import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# --- CONFIGURACION MUY IMPORTANTE ---
# 1. PEGA AQUÍ TU URL DE APPS SCRIPT (la que termina en /exec)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbylFGmrFKbVTYcYWF998q0yzlQrWPkuWoWvGcx0Pwl87KTVpEfhy9Xm_ZqivpnE2aaXDw/exec"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Gestión Biosintex", layout="wide")

# --- CONSTANTES ---
PRES_LIST = [
    "CAJAS", "BOLSA BLANCA", "BOBINA", "TAMBOR VERDE", "BOLSA", 
    "BOBINAS", "CAJAS BLANCAS", "TAMBORES VERDES", "BIDON AZUL", 
    "BIDON", "CUETE CARTON", "BOLSA NEGRA", "BIDON AMARILLO", 
    "TAMBOR", "BALDE", "TAMBOR AZUL", "CUETE", "CAJA DE CARTON", 
    "CAJAS PLASTICAS", "BOLSAS DE CARTON", "OTROS"
]

STAFF_BY_PLANT = {
    "Barracas": ["Ruben Guzman", "Gaston Fonteina", "Adrian Fernandez", "Walter Alarcon", "Maximiliano Duarte"],
    "Pibera": ["Hernan Miño", "Sebastian Colmano", "Gustavo Alegre", "Federico Scolazzo"]
}

# Mensaje recordatorio
if "AKfycb" not in SCRIPT_URL:
    st.error("🛑 FALTA CONFIGURAR LA URL DE ESCRITURA. Ve al archivo app.py y pega tu URL de Apps Script en la línea 8.")

# --- LOGIN ---
if "password_correct" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Biosintex</h2>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.5,1])
    with col:
        with st.form("Login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if u == "biosintex" and p == "2026":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Credenciales incorrectas")
    st.stop()

# --- INIT ---
if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL, SCRIPT_URL)
if 'env' not in st.session_state:
    st.session_state.env = "Producción"
if 'form_id' not in st.session_state:
    st.session_state.form_id = 0

def refresh_data():
    with st.spinner("Sincronizando..."):
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])
        # También refrescar historial
        st.session_state.history = st.session_state.manager.get_history(env=st.session_state.env)
        if data.get('error'): st.warning(data['error'])

if 'skus' not in st.session_state or not st.session_state.skus:
    refresh_data()

# --- BUSQUEDA ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    q = q.lower()
    res = []
    for s in st.session_state.skus:
        art = str(s.get('Articulo', s.get('ID', '')))
        nom = str(s.get('Nombre', ''))
        if q in art.lower() or q in nom.lower():
            res.append((f"{art} - {nom}", art))
    return res[:30]

def search_prov(q):
    if not q or not st.session_state.get('providers'): return []
    q_low = q.lower()
    res = []
    for p in st.session_state.providers:
        fila_texto = " ".join([str(v) for v in p.values()]).lower()
        if q_low in fila_texto:
            nombre = p.get('Proveedor', p.get('PROVEEDOR', p.get('Nombre', next(iter(p.values()), 'Sin nombre'))))
            if nombre and str(nombre) != 'nan':
                res.append(str(nombre))
    return sorted(list(set(res)))[:30]

# --- UI ---
st.title(f"📦 Recepción Biosintex ({st.session_state.env})")

with st.sidebar:
    st.header("⚙️ Ajustes")
    env_sidebar = st.radio("Entorno:", ["Producción", "Pruebas"], index=0 if st.session_state.env=="Producción" else 1)
    if env_sidebar != st.session_state.env:
        st.session_state.env = env_sidebar
        st.rerun()
    st.button("🔄 Sincronizar", on_click=refresh_data)
    
    if 'skus' in st.session_state:
        st.caption(f"✅ {len(st.session_state.skus)} SKUs cargados")
    if 'providers' in st.session_state:
        st.caption(f"✅ {len(st.session_state.providers)} Proveedores cargados")
    if hasattr(st.session_state.manager, 'last_sync') and st.session_state.manager.last_sync:
        st.caption(f"🕒 Sinc: {st.session_state.manager.last_sync.strftime('%H:%M:%S')}")

tab1, tab2 = st.tabs(["📝 Nuevo Registro", "📊 Historial"])

with tab1:
    f_id = st.session_state.form_id
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        sku = st_searchbox(search_sku, label="Buscar SKU *", key=f"sku_in_{f_id}")
        sku_desc = ""
        if sku:
            for s in st.session_state.skus:
                if str(s.get('Articulo', s.get('ID',''))) == str(sku):
                    sku_desc = s.get('Nombre','')
                    st.info(f"✅ PRODUCTO: {sku_desc}"); break
        
        lote = st.text_input("Número de Lote *", key=f"lote_in_{f_id}")
        vto = st.date_input("Vencimiento *", key=f"vto_in_{f_id}")
        
        c_or, c_pr = st.columns(2)
        with c_or:
            origen = st.selectbox("Origen *", ["Nacional", "Importado"], key=f"ori_in_{f_id}")
        with c_pr:
            pres = st.selectbox("Presentación *", PRES_LIST, key=f"pres_in_{f_id}")

    with c2:
        st.subheader("Recepción")
        udm = st.selectbox("Unidad (UDM) *", ["KG", "UN", "L", "M"], key=f"udm_in_{f_id}")
        cant = st.number_input("Cantidad Total *", min_value=0.0, key=f"cant_in_{f_id}")
        bul = st.number_input("Bultos *", min_value=1, step=1, key=f"bul_in_{f_id}")
        prov = st_searchbox(search_prov, label="Proveedor *", key=f"prov_in_{f_id}")
        rem = st.text_input("Nº Remito *", key=f"rem_in_{f_id}")
        
        c_oc, c_rc = st.columns(2)
        with c_oc:
            oc = st.text_input("Nº Orden de Compra (OC)", key=f"oc_in_{f_id}")
        with c_rc:
            current_state = st.session_state.manager.get_state(env=st.session_state.env)
            next_rec = str(current_state.get("last_reception", 0) + 1)
            st.text_input("Nº Recepción (Sugerido)", value=next_rec, disabled=True, key=f"rec_sug_{f_id}")
        
        c_pl, c_st1, c_st2 = st.columns([1, 1.5, 1.5])
        with c_pl:
            planta = st.selectbox("Planta *", ["Barracas", "Pibera"], key=f"planta_in_{f_id}")
        
        current_staff = STAFF_BY_PLANT.get(planta, [])
        with c_st1: 
            real = st.selectbox("Realizado por *", ["Seleccione..."] + current_staff, key=f"real_in_{f_id}")
        
        # Filtrar el seleccionado en 'Realizado' para que no se repita en 'Controlado'
        cont_options = ["Seleccione..."] + [s for s in current_staff if s != real]
        with c_st2: 
            cont = st.selectbox("Controlado por *", cont_options, key=f"cont_in_{f_id}")

    if st.button("🚀 GENERAR ANÁLISIS", type="primary", use_container_width=True):
        if not sku or not lote or not prov or real=="Seleccione...":
            st.error("⚠️ Faltan datos obligatorios.")
        else:
            with st.spinner("Generando Análisis en el servidor..."):
                entry = {
                    'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_desc, 
                    'Número de Análisis': "PENDIENTE", 'Lote': lote, 'Origen': origen, 'Cantidad': cant, 'UDM': udm, 
                    'Cantidad Bultos': bul, 'Vto': vto.strftime("%d/%m/%Y"), 'Proveedor': prov, 
                    'Número de Remito': rem, 'Presentacion': pres, 'recepcion_num': 0, 
                    'realizado_por': real, 'controlado_por': cont, 'Entorno': st.session_state.env,
                    'Planta': planta, 'OC': oc
                }
                ok, result = st.session_state.manager.save_entry_remote(entry, env=st.session_state.env)
                if ok:
                    entry['Número de Análisis'] = result.get('analysis')
                    entry['recepcion_num'] = result.get('reception')
                    st.session_state.current_label = entry
                    st.session_state.show_label = True
                    
                    # --- REINICIO TOTAL DEL FORMULARIO ---
                    # Incrementamos el form_id para que todos los widgets tengan llaves nuevas
                    st.session_state.form_id += 1
                    
                    st.session_state.just_saved = True
                    st.rerun()
                else: st.error(f"Error al guardar: {result}")

with tab2:
    # Mostrar mensaje de éxito si acaba de guardar
    if st.session_state.get('just_saved'):
        st.success("✅ ¡Registro guardado y formulario reiniciado con éxito!")
        st.session_state.just_saved = False
    st.subheader(f"📊 Historial de Cargas ({st.session_state.env})")
    
    if st.button("🔄 Refrescar Historial"):
        st.session_state.history = st.session_state.manager.get_history(env=st.session_state.env)
        st.rerun()

    if 'history' in st.session_state and not st.session_state.history.empty:
        df_hist = st.session_state.history.copy()
        
        # Exportar a Excel
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_hist.to_excel(writer, index=False)
        st.download_button(label="📥 Descargar Excel", data=output.getvalue(), file_name=f"historial_{st.session_state.env}.xlsx", mime="application/vnd.ms-excel")
        
        st.info("💡 Haz doble clic en una celda para editar (excepto campos clave).")
        
        # Preparar listas para los selectores del editor (vienen de la base)
        sku_list = sorted(list(set([str(s.get('Articulo', '')) for s in st.session_state.get('skus', []) if s.get('Articulo')])))
        desc_list = sorted(list(set([str(s.get('Nombre', '')) for s in st.session_state.get('skus', []) if s.get('Nombre')])))
        
        prov_list = []
        if 'providers' in st.session_state:
            for p in st.session_state.providers:
                name = p.get('Proveedor', p.get('PROVEEDOR', p.get('Nombre', '')))
                if name and str(name) != 'nan': prov_list.append(str(name).strip())
        prov_list = sorted(list(set(prov_list)))

        # Editor de datos con columnas configuradas como Selectbox
        edited_df = st.data_editor(
            df_hist, 
            key="hist_editor",
            use_container_width=True, 
            hide_index=True, 
            disabled=["Número de Análisis", "Fecha", "recepcion_num"],
            column_config={
                "SKU": st.column_config.SelectboxColumn("SKU", options=sku_list, required=True),
                "Descripción de Producto": st.column_config.SelectboxColumn("Descripción de Producto", options=desc_list),
                "Proveedor": st.column_config.SelectboxColumn("Proveedor", options=prov_list),
                "Presentacion": st.column_config.SelectboxColumn("Presentación", options=PRES_LIST),
                "Planta": st.column_config.SelectboxColumn("Planta", options=["Barracas", "Pibera"], required=True),
                "Origen": st.column_config.SelectboxColumn("Origen", options=["Nacional", "Importado"]),
                "UDM": st.column_config.SelectboxColumn("UDM", options=["KG", "UN", "L", "M"]),
                "Número de Remito": st.column_config.TextColumn("Nº Remito"),
                "realizado_por": st.column_config.SelectboxColumn("Realizado por", options=STAFF_BY_PLANT["Barracas"] + STAFF_BY_PLANT["Pibera"]),
                "controlado_por": st.column_config.SelectboxColumn("Controlado por", options=STAFF_BY_PLANT["Barracas"] + STAFF_BY_PLANT["Pibera"]),
            }
        )

        # --- LÓGICA DE ASOCIACIÓN SKU <-> DESCRIPCIÓN ---
        # Detectar cambios a través del estado del editor de Streamlit
        edits = st.session_state.get("hist_editor", {}).get("edited_rows", {})
        if edits:
            sku_to_desc = {str(s.get('Articulo', '')): str(s.get('Nombre', '')) for s in st.session_state.get('skus', []) if s.get('Articulo')}
            desc_to_sku = {str(s.get('Nombre', '')): str(s.get('Articulo', '')) for s in st.session_state.get('skus', []) if s.get('Nombre')}
            
            changes_made = False
            for row_idx_str, row_changes in edits.items():
                idx = int(row_idx_str)
                # Si cambió el SKU
                if "SKU" in row_changes:
                    new_sku = str(row_changes["SKU"])
                    new_desc = sku_to_desc.get(new_sku)
                    if new_desc:
                        df_hist.at[idx, "SKU"] = new_sku
                        df_hist.at[idx, "Descripción de Producto"] = new_desc
                        changes_made = True
                
                # Si cambió la Descripción
                elif "Descripción de Producto" in row_changes:
                    new_desc = str(row_changes["Descripción de Producto"])
                    new_sku = desc_to_sku.get(new_desc)
                    if new_sku:
                        df_hist.at[idx, "Descripción de Producto"] = new_desc
                        df_hist.at[idx, "SKU"] = new_sku
                        changes_made = True
                
                # Otros cambios (Remito, Planta, etc)
                else:
                    for col, val in row_changes.items():
                        df_hist.at[idx, col] = val
                        changes_made = True
            
            if changes_made:
                st.session_state.history = df_hist
                # Limpiamos el estado del editor para evitar bucles
                st.session_state["hist_editor"]["edited_rows"] = {}
                st.rerun()
        
        # Botón para guardar cambios (requiere soporte en Apps Script)
        if st.button("💾 GUARDAR CAMBIOS EN LA NUBE", type="secondary"):
            with st.spinner("Guardando cambios..."):
                # Aquí enviamos solo las filas modificadas o todo el lote
                # Por simplicidad, implementaremos la lógica en el manager
                ok, msg = st.session_state.manager.update_history_remote(edited_df, env=st.session_state.env)
                if ok: st.success("✅ Historial actualizado correctamente en Google Sheets")
                else: st.error(f"❌ Error al guardar: {msg}")
        
        st.divider()
        st.subheader("🖨️ Reimprimir Rótulo")
        sel_an = st.selectbox("Seleccione Análisis para reimprimir:", edited_df["Número de Análisis"].tolist())
        if st.button("🔍 Cargar para Impresión"):
            selected_row = edited_df[edited_df["Número de Análisis"] == sel_an].iloc[0].to_dict()
            # Mapear nombres de columnas si vienen con caracteres especiales del Excel
            re_entry = {
                'Fecha': selected_row.get('Fecha', ''), 'SKU': selected_row.get('SKU', ''), 
                'Descripción de Producto': selected_row.get('Descripción de Producto', selected_row.get('Descripcion de Producto', '')),
                'Número de Análisis': selected_row.get('Número de Análisis', selected_row.get('Numero de Analisis', '')),
                'Lote': selected_row.get('Lote', ''), 'Origen': selected_row.get('Origen', ''),
                'Cantidad': selected_row.get('Cantidad', 0), 'UDM': selected_row.get('UDM', ''),
                'Cantidad Bultos': int(selected_row.get('Cantidad Bultos', 1)), 'Vto': selected_row.get('Vto', ''),
                'Proveedor': selected_row.get('Proveedor', ''), 'Número de Remito': selected_row.get('Número de Remito', selected_row.get('Numero de Remito', '')),
                'Presentacion': selected_row.get('Presentacion', selected_row.get('Presentación', '')),
                'recepcion_num': selected_row.get('recepcion_num', ''), 'realizado_por': selected_row.get('realizado_por', ''), 'controlado_por': selected_row.get('controlado_por', '')
            }
            st.session_state.current_label = re_entry
            st.session_state.show_label = True
            st.rerun()
    else:
        st.write("No hay datos cargados. Presiona 'Refrescar Historial'.")

if st.session_state.get('show_label'):
    d = st.session_state.current_label
    st.divider()
    if st.button("❌ Cerrar"): st.session_state.show_label = False; st.rerun()
    
    # --- CONTROLES DE IMPRESIÓN (Solo visibles en pantalla) ---
    # --- CONTROLES DE IMPRESIÓN (Solo visibles en pantalla) ---
    c_p1, c_p2 = st.columns([1,1])
    with c_p1:
        print_mode = st.radio("Modo de impresión:", ["Bulto individual", "Todos los bultos"], horizontal=True, key="print_mode_radio")
    
    cant_sugerida = d['Cantidad'] / d['Cantidad Bultos'] if d['Cantidad Bultos'] else 0
    
    if print_mode == "Bulto individual":
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            bulto_n_list = [st.number_input("Imprimir Bulto Nº", min_value=1, max_value=d['Cantidad Bultos'], value=1)]
        with c_i2:
            cant_bulto = st.number_input("Cantidad para este bulto", value=float(cant_sugerida), step=0.01)
            cant_list = [cant_bulto]
    else:
        bulto_n_list = list(range(1, d['Cantidad Bultos'] + 1))
        cant_list = [cant_sugerida] * d['Cantidad Bultos']
        st.info(f"Se generarán {d['Cantidad Bultos']} rótulos, cada uno con {cant_sugerida:.2f} {d['UDM']}")

    # Diseño de Rótulo 10x10 cm aproximado para impresión
    labels_html = ""
    for idx, b_n in enumerate(bulto_n_list):
        c_bulto = cant_list[idx]
        labels_html += f"""
        <div class="label-container" id="printable-label-{b_n}">
            <table>
                <tr>
                    <td class="field-name">Nº de Análisis</td>
                    <td class="header-val" colspan="2">{d['Número de Análisis']}</td>
                    <td class="logo-box"><b style="color:#0056b3; font-size:16px;">Biosintex</b></td>
                </tr>
                <tr>
                    <td class="field-name">Insumo / Producto</td>
                    <td colspan="3" class="label-text">{d.get('Descripción de Producto', '')}</td>
                </tr>
                <tr>
                    <td class="field-name">Presentación</td>
                    <td colspan="3" class="label-text">{d.get('Presentacion', '')}</td>
                </tr>
                <tr>
                    <td class="field-name">Fecha</td>
                    <td colspan="3">{d['Fecha']}</td>
                </tr>
                <tr>
                    <td class="field-name">Nº de lote</td>
                    <td>{d['Lote']}</td>
                    <td class="field-name">Vto.:</td>
                    <td>{d['Vto']}</td>
                </tr>
                <tr>
                    <td class="field-name">Código interno</td>
                    <td colspan="3" class="label-text">{d['SKU']}</td>
                </tr>
                <tr>
                    <td class="field-name">Origen</td>
                    <td colspan="3" class="label-text">{d.get('Origen', '')}</td>
                </tr>
                <tr>
                    <td class="field-name">Proveedor</td>
                    <td colspan="3" class="label-text">{d['Proveedor']}</td>
                </tr>
                <tr>
                    <td class="field-name">Bulto Nº</td>
                    <td style="background:#ddd; font-weight:bold;">{b_n}</td>
                    <td class="field-name">de</td>
                    <td style="background:#ddd; font-weight:bold;">{d['Cantidad Bultos']}</td>
                </tr>
                <tr>
                    <td class="field-name">Cantidad por bulto</td>
                    <td style="font-weight:bold;">{c_bulto:.2f} {d['UDM']}</td>
                    <td class="field-name">Total</td>
                    <td>{d['Cantidad']} {d['UDM']}</td>
                </tr>
                <tr>
                    <td class="field-name">Nº de Remito</td>
                    <td class="small-text">{d['Número de Remito']}</td>
                    <td class="field-name">Nº de recepción</td>
                    <td>{d['recepcion_num']}</td>
                </tr>
                <tr>
                    <td class="field-name">Realizado por</td>
                    <td class="label-text" style="font-size:9px;">{d['realizado_por'] if d['realizado_por'] != "Seleccione..." else ""}</td>
                    <td class="field-name">Controlado por</td>
                    <td class="label-text" style="font-size:9px;">{d['controlado_por'] if d['controlado_por'] != "Seleccione..." else ""}</td>
                </tr>
                <tr>
                    <td class="small-text">DP-003-SOP Vigente</td>
                    <td colspan="3" class="cuarentena">CUARENTENA</td>
                </tr>
            </table>
        </div>
        """

    full_html = f"""
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            @page {{ size: 100mm 100mm; margin: 0; }}
            body {{ margin: 0; }}
            .label-container {{ page-break-after: always; }}
        }}
        .label-container {{
            width: 370px;
            height: 370px;
            border: 2px solid black;
            font-family: Arial, sans-serif;
            font-size: 11px;
            margin: 10px auto;
            background: white;
            color: black;
            display: flex;
            flex-direction: column;
            page-break-after: always;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            height: 100%;
        }}
        td {{
            border: 1px solid black;
            padding: 3px;
            text-align: center;
            vertical-align: middle;
        }}
        .label-text {{ font-weight: bold; text-transform: uppercase; }}
        .header-val {{ font-size: 24px; font-weight: bold; }}
        .cuarentena {{
            background: white;
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 2px;
        }}
        .field-name {{ width: 30%; text-align: left; background: #f0f0f0; font-weight: bold; font-size: 10px; }}
        .logo-box {{ width: 30%; }}
        .small-text {{ font-size: 9px; }}
    </style>
    <div id="printable-area">
        {labels_html}
    </div>
    <div class="no-print" style="text-align:center; margin-top:20px;">
        <button onclick="window.print()" style="padding:15px 30px; background:green; color:white; font-weight:bold; border:none; border-radius:5px; cursor:pointer; font-size:16px;">🖨️ IMPRIMIR ETIQUETAS</button>
        <p style="color:gray; font-size:12px; margin-top:5px;">Se imprimirán {len(bulto_n_list)} rótulo(s).</p>
    </div>
    """
    st.components.v1.html(full_html, height=600 if print_mode == "Bulto individual" else 800, scrolling=True)

