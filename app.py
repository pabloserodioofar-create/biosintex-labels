import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# --- CONFIGURACION MUY IMPORTANTE ---
# 1. PEGA AQUÍ TU URL DE APPS SCRIPT (la que termina en /exec)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwlWb92Vha5hLW8WXubnRAc7NR953147fotL8uwqSTL7uiru-RRwq-QtJEHM0GnY6nWBg/exec"

SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Gestión Biosintex", layout="wide")

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
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        # Usamos llaves para el estado para poder resetear
        sku = st_searchbox(search_sku, label="Buscar SKU *", key="sku_in")
        sku_desc = ""
        if sku:
            for s in st.session_state.skus:
                if str(s.get('Articulo', s.get('ID',''))) == str(sku):
                    sku_desc = s.get('Nombre','')
                    st.info(f"✅ PRODUCTO: {sku_desc}"); break
        
        lote = st.text_input("Número de Lote *", key="lote_in")
        vto = st.date_input("Vencimiento *", key="vto_in")
        
        c_or, c_pr = st.columns(2)
        with c_or:
            origen = st.selectbox("Origen *", ["Nacional", "Importado"], key="ori_in")
        with c_pr:
            pres_list = [
                "CAJAS", "BOLSA BLANCA", "BOBINA", "TAMBOR VERDE", "BOLSA", 
                "BOBINAS", "CAJAS BLANCAS", "TAMBORES VERDES", "BIDON AZUL", 
                "BIDON", "CUETE CARTON", "BOLSA NEGRA", "BIDON AMARILLO", 
                "TAMBOR", "BALDE", "TAMBOR AZUL", "CUETE", "CAJA DE CARTON", 
                "CAJAS PLASTICAS", "BOLSAS DE CARTON", "OTROS"
            ]
            pres = st.selectbox("Presentación *", pres_list, key="pres_in")

    with c2:
        st.subheader("Recepción")
        udm = st.selectbox("Unidad (UDM) *", ["KG", "UN", "L", "M"], key="udm_in")
        cant = st.number_input("Cantidad Total *", min_value=0.0, key="cant_in")
        bul = st.number_input("Bultos *", min_value=1, step=1, key="bul_in")
        prov = st_searchbox(search_prov, label="Proveedor *", key="prov_in")
        rem = st.text_input("Nº Remito *", key="rem_in")
        
        current_state = st.session_state.manager.get_state(env=st.session_state.env)
        next_rec = str(current_state.get("last_reception", 0) + 1)
        st.text_input("Nº Recepción (Auto)", value=next_rec, disabled=True)
        
        staff = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]
        sm1, sm2 = st.columns(2)
        with sm1: real = st.selectbox("Realizado por *", ["Seleccione..."] + staff, key="real_in")
        with sm2: cont = st.selectbox("Controlado por *", ["Seleccione..."] + staff, key="cont_in")

    if st.button("🚀 GENERAR ANÁLISIS", type="primary", use_container_width=True):
        if not sku or not lote or not prov or real=="Seleccione...":
            st.error("⚠️ Faltan datos obligatorios.")
        else:
            with st.spinner("Guardando en la nube..."):
                an = st.session_state.manager.generate_next_number(env=st.session_state.env)
                rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
                
                entry = {
                    'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_desc, 
                    'Número de Análisis': an, 'Lote': lote, 'Origen': origen, 'Cantidad': cant, 'UDM': udm, 
                    'Cantidad Bultos': bul, 'Vto': vto.strftime("%d/%m/%Y"), 'Proveedor': prov, 
                    'Número de Remito': rem, 'Presentacion': pres, 'recepcion_num': int(rc), 
                    'realizado_por': real, 'controlado_por': cont, 'Entorno': st.session_state.env
                }
                ok, msg = st.session_state.manager.save_entry(entry, env=st.session_state.env)
                if ok:
                    st.session_state.current_label = entry
                    st.session_state.show_label = True
                    # Limpiar formulario borrando llaves de session_state
                    for rkey in ["sku_in", "lote_in", "rem_in", "cant_in", "bul_in", "prov_in", "real_in", "cont_in"]:
                        if rkey in st.session_state: del st.session_state[rkey]
                    st.rerun()
                else: st.error(f"Error al guardar: {msg}")

with tab2:
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
        
        # Editor de datos
        edited_df = st.data_editor(df_hist, use_container_width=True, hide_index=True, disabled=["Número de Análisis", "Fecha", "recepcion_num"])
        
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
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        bulto_n = st.number_input("Imprimir Bulto Nº", min_value=1, max_value=d['Cantidad Bultos'], value=1)
    with c_p2:
        # Sugerir cantidad normal, pero permitir editar por bulto parcial
        cant_sugerida = d['Cantidad'] / d['Cantidad Bultos'] if d['Cantidad Bultos'] else 0
        cant_bulto = st.number_input("Cantidad para este bulto", value=float(cant_sugerida), step=0.01)

    # Diseño de Rótulo 10x10 cm aproximado para impresión
    html = f"""
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            @page {{ size: 100mm 100mm; margin: 0; }}
            body {{ margin: 0; }}
        }}
        .label-container {{
            width: 380px;
            height: 380px;
            border: 2px solid black;
            font-family: Arial, sans-serif;
            font-size: 11px;
            margin: auto;
            background: white;
            color: black;
            display: flex;
            flex-direction: column;
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
    <div class="label-container" id="printable-label">
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
                <td style="background:#ddd; font-weight:bold;">{bulto_n}</td>
                <td class="field-name">de</td>
                <td style="background:#ddd; font-weight:bold;">{d['Cantidad Bultos']}</td>
            </tr>
            <tr>
                <td class="field-name">Cantidad por bulto</td>
                <td style="font-weight:bold;">{cant_bulto:.2f} {d['UDM']}</td>
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
    <div class="no-print" style="text-align:center; margin-top:20px;">
        <button onclick="window.print()" style="padding:15px 30px; background:green; color:white; font-weight:bold; border:none; border-radius:5px; cursor:pointer; font-size:16px;">🖨️ IMPRIMIR ESTE RÓTULO</button>
        <p style="color:gray; font-size:12px; margin-top:5px;">Configura el bulto y cantidad arriba antes de imprimir.</p>
    </div>
    """
    st.components.v1.html(html, height=650)
