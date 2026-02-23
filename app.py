import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime
import os

# Google Sheet URL (Clean version)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

# Page config
st.set_page_config(
    page_title="Biosintex - Gestión de Insumos", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize Session State Defaults (To prevent AttributeErrors if load fails)
if 'skus' not in st.session_state:
    st.session_state.skus = []
if 'providers' not in st.session_state:
    st.session_state.providers = []
if 'presentations' not in st.session_state:
    st.session_state.presentations = ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"]
if 'env' not in st.session_state:
    st.session_state.env = "Producción"

# CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarNav"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# Initialize Manager
if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

# Load data helper with robust error handling
def refresh_data():
    with st.spinner("Sincronizando con Google Sheets..."):
        data = st.session_state.manager.get_excel_data()
        if "error" in data:
            st.warning(f"⚠️ Nota sobre los datos: {data['error']}")
            # We don't return, we keep defaults to let the app run
        
        # Only update if we got valid results
        if 'skus' in data: st.session_state.skus = data['skus']
        if 'providers' in data: st.session_state.providers = data['providers']
        if 'presentations' in data: st.session_state.presentations = data['presentations']

# Initial Load
if not st.session_state.skus:
    refresh_data()

# Search functions
def search_sku(query):
    if not query: return []
    q = query.lower()
    return [(f"{s['Articulo']} - {s['Nombre']}", s['Articulo']) for s in st.session_state.skus if q in str(s['Articulo']).lower() or q in str(s['Nombre']).lower()]

def search_provider(query):
    if not query: return []
    q = query.lower()
    return [p['Proveedor'] for p in st.session_state.providers if q in str(p['Proveedor']).lower()]

def load_all_history():
    try:
        df = st.session_state.manager.conn.read(spreadsheet=SHEET_URL, worksheet="Datos a completar", ttl=0)
        if not df.empty:
            mask_instr = df.astype(str).apply(lambda x: x.str.contains('carga manual|toma el asignado|toma automatico', case=False).any(), axis=1)
            df = df[~mask_instr]
            if 'Nº de Análisis' in df.columns: df = df.rename(columns={'Nº de Análisis': 'Número de Análisis'})
            return df.iloc[::-1]
    except Exception as e:
        st.info("💡 Crea una pestaña llamada 'Datos a completar' en tu Google Sheet para ver el historial.")
    return pd.DataFrame()

def safe_float(val):
    try: return float(val)
    except: return 0.0

def safe_int(val):
    try: return int(float(val))
    except: return 1

def reset_form():
    st.session_state.sku_search_new = None
    st.session_state.lote_new = ""
    st.session_state.cant_new = 0.0
    st.session_state.udm_new = "KG"
    st.session_state.bultos_new = 1
    st.session_state.prov_search_new = None
    st.session_state.remito_new = ""
    st.session_state.realiz_new = "Seleccione..."
    st.session_state.control_new = "Seleccione..."
    st.session_state.vto_new = datetime.today()

# Reception number
if 'next_recep' not in st.session_state:
    state = st.session_state.manager.get_state()
    st.session_state.next_recep = str(state.get("last_reception", 0) + 1)

# UI
header_col1, header_col2 = st.columns([5, 1])
with header_col1: st.title("📦 Biosintex - Gestión de Insumos")
with header_col2:
    with st.popover("⚙️ Ajustes"):
        if st.button("🔄 Sincronizar Google Sheets"):
            refresh_data()
            st.rerun()
        st.divider()
        with st.expander("🔐 Administración"):
            admin_pass = st.text_input("Contraseña", type="password")
            if admin_pass == "biosintex2026":
                if st.button("⚠️ Reset Sistema"):
                    success, msg = st.session_state.manager.reset_system()
                    if success: st.success(msg); refresh_data(); st.rerun()
                    else: st.error(msg)

tab1, tab2 = st.tabs(["📝 Registro", "📊 Historial"])

staff_options = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Insumo")
        selected_sku = st_searchbox(search_sku, label="SKU *", key="sku_search_new")
        sku_desc = ""
        if selected_sku:
            info = next((s for s in st.session_state.skus if str(s['Articulo']) == str(selected_sku)), None)
            if info: sku_desc = info['Nombre']; st.info(f"Producto: {sku_desc}")
        lote = st.text_input("Lote *", key="lote_new")
        origen = st.selectbox("Origen *", ["Nacional", "Importado"], key="origen_new")
        vto = st.date_input("Vencimiento *", value=datetime.today(), key="vto_new")
        pres = st.selectbox("Presentación *", st.session_state.presentations, key="pres_new")
    with col2:
        st.subheader("Recepción")
        udm = st.selectbox("UDM *", ["KG", "UN", "L", "M"], key="udm_new")
        cant = st.number_input("Cantidad Total *", min_value=0.0, step=1.0 if udm=="UN" else 0.1, key="cant_new")
        bultos = st.number_input("Bultos *", min_value=1, key="bultos_new")
        prov = st_searchbox(search_provider, label="Proveedor *", key="prov_search_new")
        remito = st.text_input("Remito *", key="remito_new")
        st.text_input("Recepción (Auto)", value=st.session_state.next_recep, disabled=True)
        c1, c2 = st.columns(2)
        with c1: realizado = st.selectbox("Realizado por *", ["Seleccione..."] + staff_options, key="realiz_new")
        with c2: controlado = st.selectbox("Controlado por *", ["Seleccione..."] + staff_options, key="control_new")

    if st.button("🚀 Generar Análisis", type="primary"):
        if not selected_sku or not lote or not prov or realizado=="Seleccione..." or controlado=="Seleccione...":
            st.error("Campos obligatorios incompletos")
        else:
            an_num = st.session_state.manager.generate_next_number()
            rec_num = st.session_state.manager.generate_next_reception()
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': selected_sku, 'Descripción de Producto': sku_desc, 'Número de Análisis': an_num, 'Lote': lote, 'Origen': origen, 'Cantidad': cant, 'UDM': udm, 'Cantidad Bultos': bultos, 'Vto': vto.strftime("%d/%m/%Y"), 'Proveedor': prov, 'Número de Remito': remito, 'Presentacion': pres, 'recepcion_num': rec_num, 'realizado_por': realizado, 'controlado_por': controlado}
            succ, msg = st.session_state.manager.save_entry(entry)
            if succ:
                st.success(f"Generado: {an_num}"); st.session_state.next_recep = str(int(rec_num)+1); st.session_state.current_label_data = entry; st.session_state.show_print = True; reset_form(); st.rerun()
            else: st.error(msg)

with tab2:
    hist_df = load_all_history()
    if not hist_df.empty:
        search = st.text_input("🔍 Buscar", "")
        df = hist_df[hist_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else hist_df
        for i, r in df.iterrows():
            with st.expander(f"📌 {r['Número de Análisis']} - {r['Descripción de Producto']}"):
                if st.button("🖨️ Reimprimir", key=f"reprint_{i}"):
                    st.session_state.current_label_data = r.to_dict(); st.session_state.show_print = True; st.rerun()

if st.session_state.get('show_print'):
    st.divider()
    d = st.session_state.current_label_data
    if st.button("❌ Cerrar Vista Previa"): st.session_state.show_print = False; st.rerun()
    # (Label HTML generation remains same as previous version)
    labels_html = f"""<style>@media print {{@page {{size:10cm 10cm; margin:0;}} body {{margin:0;}} .label-container {{page-break-after:always; display:flex; align-items:center; justify-content:center; height:100vh;}}}} .label-grid {{width:100%; max-width:500px; border:2px solid black; border-collapse:collapse; font-family:Arial; background:white;}} .label-grid td {{border:1px solid black; padding:4px; font-weight:bold;}} .large {{font-size:28px; text-align:center;}} .logo {{color:#0056b3; font-size:18px;}} .qua {{font-size:32px; text-align:center;}}</style>"""
    for i in range(1, int(d['Cantidad Bultos']) + 1):
        q_val = d['Cantidad']/int(d['Cantidad Bultos'])
        labels_html += f"""<div class="label-container"><table class="label-grid"><tr><td style="width:30%;">Analisis</td><td class="large">{d['Número de Análisis']}</td><td class="logo" style="text-align:right;">Biosintex</td></tr><tr><td>Producto</td><td colspan="2" style="text-align:center;">{d['Descripción de Producto']}</td></tr><tr><td>Lote</td><td>{d['Lote']}</td><td>Vto: {d['Vto']}</td></tr><tr style="background:#eee;"><td>Bulto</td><td style="text-align:center;">{i} de {d['Cantidad Bultos']}</td><td>{q_val:.2f} {d['UDM']}</td></tr><tr><td colspan="3" class="qua">CUARENTENA</td></tr></table></div>"""
    st.components.v1.html(f"{labels_html}<div style='text-align:center; margin-top:20px;'><button onclick='window.print()' style='padding:10px 20px; background:#ff4b4b; color:white; border:none; border-radius:5px; cursor:pointer;'>🖨️ Imprimir</button></div>", height=600, scrolling=True)
