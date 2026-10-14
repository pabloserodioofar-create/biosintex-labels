import altair as alt
import pandas as pd
import streamlit as st

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
PLANTA_COLORS = {"Barracas": "#2b6cb0", "Pibera": "#dd8a1f", "Sin dato": "#9aa0a6"}
ORIGEN_COLORS = {"Nacional": "#2f855a", "Importado": "#805ad5", "Sin dato": "#9aa0a6"}
VACIOS = {"", "nan", "None", "NaT", "<NA>"}


def _texto(serie, vacio):
    s = serie.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    return s.where(~s.isin(VACIOS), vacio)


def _col(df, nombre):
    return df[nombre] if nombre in df.columns else pd.Series([""] * len(df), index=df.index)


def prepare_data(df_raw):
    """Limpia el historial: fechas reales, textos sin vacíos y números como números."""
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    fecha = pd.to_datetime(_col(df, "Fecha"), dayfirst=True, errors="coerce", format="mixed")
    analisis = _col(df, "Número de Análisis").astype(str).str.strip()
    valido = fecha.notna() & ~analisis.isin(VACIOS)

    out = pd.DataFrame(index=df.index)
    out["fecha"] = fecha.dt.normalize()
    out["analisis_nro"] = analisis
    out["planta"] = _texto(_col(df, "Planta"), "Sin dato")
    out["origen"] = _texto(_col(df, "Origen"), "Sin dato")
    out["proveedor"] = _texto(_col(df, "Proveedor"), "Sin proveedor")
    out["insumo"] = _texto(_col(df, "Descripción de Producto"), "Sin descripción")
    out["operador"] = _texto(_col(df, "realizado_por"), "Sin dato")
    out["remito"] = _texto(_col(df, "Número de Remito"), "")
    out["udm"] = _texto(_col(df, "UDM"), "Sin dato")
    out["bultos"] = pd.to_numeric(_col(df, "Cantidad Bultos"), errors="coerce").fillna(0)
    out["cantidad"] = pd.to_numeric(_col(df, "Cantidad"), errors="coerce").fillna(0)
    out["ingresos"] = 1

    out = out[valido].copy()
    periodo = out["fecha"].dt.to_period("M")
    out["anio"] = out["fecha"].dt.year
    out["mes_key"] = periodo.astype(str)
    out["mes_label"] = periodo.apply(lambda p: f"{MESES[p.month - 1]} {p.year}")
    out["dia"] = out["fecha"].dt.day
    out["dia_semana"] = out["fecha"].dt.dayofweek
    return out


def _meses_orden(df):
    """Etiquetas de todos los meses del rango (incluye meses sin ingresos)."""
    rango = pd.period_range(df["fecha"].min(), df["fecha"].max(), freq="M")
    return [f"{MESES[p.month - 1]} {p.year}" for p in rango]


def _scale(mapa, serie):
    dominio = [k for k in mapa if k in set(serie)] + [k for k in sorted(set(serie)) if k not in mapa]
    rango = [mapa.get(k, "#6b7280") for k in dominio]
    return alt.Scale(domain=dominio, range=rango)


def _barras_por_mes(df, valor, titulo_y, color_col, color_map, orden):
    agg = df.groupby(["mes_label", color_col], as_index=False)[valor].sum()
    return (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("mes_label:N", sort=orden, title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y(f"{valor}:Q", title=titulo_y),
            color=alt.Color(f"{color_col}:N", scale=_scale(color_map, agg[color_col]), legend=alt.Legend(title=None, orient="bottom")),
            tooltip=[alt.Tooltip("mes_label:N", title="Mes"), alt.Tooltip(f"{color_col}:N", title=color_col.capitalize()), alt.Tooltip(f"{valor}:Q", title=titulo_y, format=",.0f")],
        )
        .properties(height=300)
    )


def _pareto(df, metrica, top_n):
    valor = "ingresos" if metrica == "Análisis" else "bultos"
    agg = df.groupby("proveedor", as_index=False)[valor].sum().sort_values(valor, ascending=False).reset_index(drop=True)
    total = agg[valor].sum()
    agg["acum"] = agg[valor].cumsum() / total if total else 0
    previo = agg["acum"].shift(fill_value=0)
    agg["clase"] = previo.apply(lambda p: "A" if p < 0.80 else ("B" if p < 0.95 else "C"))
    top = agg.head(top_n)
    orden = top["proveedor"].tolist()

    barras = (
        alt.Chart(top)
        .mark_bar()
        .encode(
            x=alt.X("proveedor:N", sort=orden, title=None, axis=alt.Axis(labelAngle=-45, labelLimit=160, labelOverlap=False)),
            y=alt.Y(f"{valor}:Q", title=metrica),
            color=alt.Color("clase:N", scale=alt.Scale(domain=["A", "B", "C"], range=["#2b6cb0", "#dd8a1f", "#9aa0a6"]), legend=alt.Legend(title="Clase", orient="bottom")),
            tooltip=[alt.Tooltip("proveedor:N", title="Proveedor"), alt.Tooltip(f"{valor}:Q", title=metrica, format=",.0f"), alt.Tooltip("acum:Q", title="% acumulado", format=".0%"), alt.Tooltip("clase:N", title="Clase")],
        )
    )
    linea = (
        alt.Chart(top)
        .mark_line(point=True, color="#c53030")
        .encode(
            x=alt.X("proveedor:N", sort=orden),
            y=alt.Y("acum:Q", title="% acumulado", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        )
    )
    grafico = alt.layer(barras, linea).resolve_scale(y="independent").properties(height=360)
    resumen = (
        agg.groupby("clase")
        .agg(proveedores=("proveedor", "count"), total=(valor, "sum"))
        .reindex(["A", "B", "C"])
        .fillna(0)
    )
    resumen["% del total"] = (resumen["total"] / total * 100).round(1) if total else 0
    return grafico, resumen, agg


def _proveedores_por_mes(df, top_n, orden):
    top = df.groupby("proveedor")["ingresos"].sum().nlargest(top_n).index
    d = df.assign(proveedor=df["proveedor"].where(df["proveedor"].isin(top), "Otros"))
    agg = d.groupby(["mes_label", "proveedor"], as_index=False)["ingresos"].sum()
    return (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("mes_label:N", sort=orden, title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("ingresos:Q", title="Análisis"),
            color=alt.Color("proveedor:N", legend=alt.Legend(title=None, orient="bottom", columns=3, labelLimit=220)),
            tooltip=[alt.Tooltip("mes_label:N", title="Mes"), alt.Tooltip("proveedor:N", title="Proveedor"), alt.Tooltip("ingresos:Q", title="Análisis")],
        )
        .properties(height=340)
    )


def _heatmap(df, orden_meses):
    agg = df.groupby(["mes_label", "dia"], as_index=False)["ingresos"].sum()
    base = alt.Chart(agg).encode(
        x=alt.X("dia:O", title="Día del mes"),
        y=alt.Y("mes_label:N", sort=orden_meses, title=None, axis=alt.Axis(labelOverlap=False)),
    )
    rect = base.mark_rect().encode(
        color=alt.Color("ingresos:Q", scale=alt.Scale(scheme="oranges"), legend=alt.Legend(title="Análisis")),
        tooltip=[alt.Tooltip("mes_label:N", title="Mes"), alt.Tooltip("dia:O", title="Día"), alt.Tooltip("ingresos:Q", title="Análisis")],
    )
    texto = base.mark_text(fontSize=10).encode(
        text="ingresos:Q",
        color=alt.condition(alt.datum.ingresos > agg["ingresos"].max() * 0.6, alt.value("white"), alt.value("#333")),
    )
    return (rect + texto).properties(height=max(140, 30 * len(orden_meses)))


def _dias_pico(df, n=10):
    filas = []
    for fecha, g in df.groupby("fecha"):
        provs = g.groupby("proveedor")["ingresos"].sum().sort_values(ascending=False)
        filas.append({
            "Fecha": fecha.strftime("%d/%m/%Y"),
            "Día": DIAS_SEMANA[fecha.dayofweek],
            "Análisis": int(g["ingresos"].sum()),
            "Bultos": int(g["bultos"].sum()),
            "Plantas": ", ".join(sorted(g["planta"].unique())),
            "Proveedores principales": ", ".join(f"{p} ({int(c)})" for p, c in provs.head(3).items()),
        })
    tabla = pd.DataFrame(filas)
    return tabla.sort_values(["Análisis", "Bultos"], ascending=False).head(n).reset_index(drop=True)


def render_dashboard(df_raw):
    if df_raw is None or len(df_raw) == 0:
        st.info("No hay datos cargados. Presioná 'Actualizar datos'.")
        return

    datos = prepare_data(df_raw)
    if datos.empty:
        st.info("No hay registros con fecha y número de análisis válidos para graficar.")
        return

    # ---------- Filtros ----------
    anios = sorted(datos["anio"].unique(), reverse=True)
    f1, f2, f3 = st.columns([1, 2, 2])
    with f1:
        anio = st.selectbox("Año", ["Todos"] + [int(a) for a in anios], index=1 if len(anios) else 0, key="dash_anio")
    with f2:
        plantas = sorted(datos["planta"].unique())
        sel_plantas = st.multiselect("Planta", plantas, default=plantas, key="dash_plantas")
    with f3:
        origenes = sorted(datos["origen"].unique())
        sel_origenes = st.multiselect("Origen", origenes, default=origenes, key="dash_origenes")

    df = datos[datos["planta"].isin(sel_plantas) & datos["origen"].isin(sel_origenes)]
    if anio != "Todos":
        df = df[df["anio"] == anio]
    if df.empty:
        st.warning("No hay ingresos para los filtros seleccionados.")
        return

    sin_planta = int((df["planta"] == "Sin dato").sum())
    if sin_planta:
        st.caption(f"ℹ️ {sin_planta} registro(s) no tienen planta cargada (registros anteriores al campo Planta) y se agrupan como 'Sin dato'.")

    orden_meses = _meses_orden(df)

    # ---------- KPIs ----------
    por_mes = df.groupby("mes_label")["ingresos"].sum()
    mes_pico = por_mes.idxmax()
    por_dia = df.groupby("fecha")["ingresos"].sum()
    dia_pico = por_dia.idxmax()
    k = st.columns(6)
    k[0].metric("Análisis generados", f"{int(df['ingresos'].sum()):,}".replace(",", "."))
    k[1].metric("Bultos recibidos", f"{int(df['bultos'].sum()):,}".replace(",", "."))
    k[2].metric("Proveedores distintos", df["proveedor"].nunique())
    k[3].metric("Remitos distintos", df.loc[df["remito"] != "", "remito"].nunique())
    k[4].metric("Promedio mensual (análisis)", f"{por_mes.sum() / len(orden_meses):.0f}")
    k[5].metric("Mes pico", mes_pico, f"{int(por_mes.max())} análisis", delta_color="off")
    st.caption(f"Día con más ingresos: {dia_pico.strftime('%d/%m/%Y')} ({DIAS_SEMANA[dia_pico.dayofweek]}) con {int(por_dia.max())} análisis.")

    # ---------- Evolución mensual ----------
    st.subheader("📅 Evolución mensual")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Ingresos por mes (análisis) y planta**")
        st.altair_chart(_barras_por_mes(df, "ingresos", "Análisis", "planta", PLANTA_COLORS, orden_meses))
    with c2:
        st.markdown("**Bultos por mes y planta**")
        st.altair_chart(_barras_por_mes(df, "bultos", "Bultos", "planta", PLANTA_COLORS, orden_meses))

    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Origen de los ingresos por mes**")
        st.altair_chart(_barras_por_mes(df, "ingresos", "Análisis", "origen", ORIGEN_COLORS, orden_meses))
    with c4:
        st.markdown("**Promedio de análisis por día de la semana**")
        dias_rango = pd.date_range(df["fecha"].min(), df["fecha"].max())
        ocurrencias = pd.Series(dias_rango.dayofweek).value_counts()
        tot = df.groupby("dia_semana")["ingresos"].sum()
        prom = pd.DataFrame({"dia_semana": range(7)})
        prom["Día"] = [DIAS_SEMANA[i] for i in prom["dia_semana"]]
        prom["Promedio"] = [tot.get(i, 0) / ocurrencias.get(i, 1) for i in prom["dia_semana"]]
        st.altair_chart(
            alt.Chart(prom).mark_bar(color="#2b6cb0").encode(
                x=alt.X("Día:N", sort=DIAS_SEMANA, title=None),
                y=alt.Y("Promedio:Q", title="Análisis por día"),
                tooltip=["Día", alt.Tooltip("Promedio:Q", format=".1f")],
            ).properties(height=300)
        )

    # ---------- Detalle diario ----------
    st.subheader("🗓️ Ingresos por día")
    d1, d2 = st.columns([1, 1])
    meses_disp = [m for m in orden_meses if m in set(df["mes_label"])]
    with d1:
        mes_sel = st.selectbox("Mes a detallar", meses_disp, index=len(meses_disp) - 1, key="dash_mes")
    with d2:
        metrica_dia = st.radio("Medir en", ["Análisis", "Bultos"], horizontal=True, key="dash_metrica_dia")
    valor_dia = "ingresos" if metrica_dia == "Análisis" else "bultos"
    dm = df[df["mes_label"] == mes_sel]
    dias_agg = dm.groupby(["dia", "planta"], as_index=False)[valor_dia].sum()
    dias_del_mes = int(dm["fecha"].dt.days_in_month.iloc[0])
    st.altair_chart(
        alt.Chart(dias_agg).mark_bar().encode(
            x=alt.X("dia:O", title="Día del mes", scale=alt.Scale(domain=list(range(1, dias_del_mes + 1)))),
            y=alt.Y(f"{valor_dia}:Q", title=metrica_dia),
            color=alt.Color("planta:N", scale=_scale(PLANTA_COLORS, dias_agg["planta"]), legend=alt.Legend(title=None, orient="bottom")),
            tooltip=[alt.Tooltip("dia:O", title="Día"), alt.Tooltip("planta:N", title="Planta"), alt.Tooltip(f"{valor_dia}:Q", title=metrica_dia, format=",.0f")],
        ).properties(height=300)
    )

    st.markdown("**Mapa de calor: ingresos por día del mes (permite ver picos recurrentes, ej. fin de mes)**")
    st.altair_chart(_heatmap(df, orden_meses))

    # ---------- Proveedores ----------
    st.subheader("🏭 Proveedores")
    p1, p2 = st.columns([1, 1])
    with p1:
        metrica_prov = st.radio("Curva ABC según", ["Análisis", "Bultos"], horizontal=True, key="dash_metrica_prov")
    with p2:
        top_n = st.slider("Proveedores a mostrar", 5, 30, 15, key="dash_topn")
    grafico, resumen, agg_prov = _pareto(df, metrica_prov, top_n)
    st.markdown(f"**Curva ABC de proveedores por {metrica_prov.lower()}** (A: hasta 80% acumulado, B: hasta 95%, C: resto)")
    st.altair_chart(grafico)
    r = resumen.reset_index().rename(columns={"clase": "Clase", "proveedores": "Proveedores", "total": metrica_prov})
    r[metrica_prov] = r[metrica_prov].astype(int)
    r["Proveedores"] = r["Proveedores"].astype(int)
    st.dataframe(r, hide_index=True)

    st.markdown("**Ingresos por mes de los 8 principales proveedores (qué proveedor explica cada pico)**")
    st.altair_chart(_proveedores_por_mes(df, 8, orden_meses))

    # ---------- Insumos y operadores ----------
    st.subheader("🧪 Insumos y operadores")
    i1, i2 = st.columns(2)
    with i1:
        st.markdown("**Top 10 insumos por cantidad de ingresos**")
        ins = df.groupby("insumo", as_index=False)["ingresos"].sum().nlargest(10, "ingresos")
        st.altair_chart(
            alt.Chart(ins).mark_bar(color="#2f855a").encode(
                y=alt.Y("insumo:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
                x=alt.X("ingresos:Q", title="Análisis"),
                tooltip=[alt.Tooltip("insumo:N", title="Insumo"), alt.Tooltip("ingresos:Q", title="Análisis")],
            ).properties(height=320)
        )
    with i2:
        st.markdown("**Análisis realizados por operador**")
        ops = df.groupby(["operador", "planta"], as_index=False)["ingresos"].sum()
        orden_ops = ops.groupby("operador")["ingresos"].sum().sort_values(ascending=False).index.tolist()
        st.altair_chart(
            alt.Chart(ops).mark_bar().encode(
                y=alt.Y("operador:N", sort=orden_ops, title=None),
                x=alt.X("ingresos:Q", title="Análisis"),
                color=alt.Color("planta:N", scale=_scale(PLANTA_COLORS, ops["planta"]), legend=alt.Legend(title=None, orient="bottom")),
                tooltip=[alt.Tooltip("operador:N", title="Operador"), alt.Tooltip("planta:N", title="Planta"), alt.Tooltip("ingresos:Q", title="Análisis")],
            ).properties(height=320)
        )

    # ---------- Picos ----------
    st.subheader("🔺 Días pico")
    st.caption("Los 10 días con más ingresos del período filtrado y los proveedores que más aportaron ese día.")
    st.dataframe(_dias_pico(df), hide_index=True)

    with st.expander("Cantidad recibida por mes y unidad de medida"):
        st.caption("No se suman unidades distintas entre sí (KG, UN, L, M); cada columna es una unidad.")
        piv = df.pivot_table(index="mes_label", columns="udm", values="cantidad", aggfunc="sum", fill_value=0)
        piv = piv.reindex([m for m in orden_meses if m in piv.index])
        piv.index.name = "Mes"
        st.dataframe(piv.round(1))
