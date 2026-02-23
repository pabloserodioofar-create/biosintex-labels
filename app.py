import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime
import os

# Google Sheet URL (Provided by User)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ/edit?usp=sharing"

# Page config
st.set_page_config(
    page_title="Biosintex - Gestión de Insumos", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS for a more premium look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #007bff !important;
        color: white !important;
    }
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    [data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Manager
if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

# Environment Management (Simplificado para Cloud)
if 'env' not in st.session_state:
    st.session_state.env = "Producción"

# Load data helper
def refresh_data():
    data = st.session_state.manager.get_excel_data()
    if "error" in data:
        st.error(f"Error cargando datos: {data['error']}")
        return
    st.session_state.skus = data.get('skus', [])
    st.session_state.providers = data.get('providers', [])
    st.session_state.presentations = data.get('presentations', ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"])

if 'skus' not in st.session_state:
    refresh_data()

# Search functions
def search_sku(query):
    if not query: return []
    query = query.lower()
    return [(f"{s['Articulo']} - {s['Nombre']}", s['Articulo']) 
            for s in st.session_state.skus 
            if query in str(s['Articulo']).lower() or query in str(s['Nombre']).lower()]

def search_provider(query):
    if not query: return []
    query = query.lower()
    return [p['Proveedor'] for p in st.session_state.providers if query in str(p['Proveedor']).lower()]

# Helper to load all history from GSheets
def load_all_history():
    try:
        conn = st.connection("gsheets", type=st.session_state.manager.conn.__class__)
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Datos a completar", ttl=0)
        
        if not df.empty:
            # Filter instruction rows
            mask_instr = df.astype(str).apply(lambda x: x.str.contains('carga manual|toma el asignado|toma automatico', case=False).any(), axis=1)
            df = df[~mask_instr]

            # Standardize analysis column
            if 'Nº de Análisis' in df.columns:
                df = df.rename(columns={'Nº de Análisis': 'Número de Análisis'})
            
            return df.iloc[::-1] # Reverse to show newest first
    except Exception as e:
        st.error(f"Error cargando historial de Google Sheets: {e}")
    return pd.DataFrame()

# Safe numeric converters
def safe_float(val):
    try: return float(val)
    except: return 0.0

def safe_int(val):
    try: return int(float(val))
    except: return 1

# Form reset function
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
    st.session_state.pres_new = st.session_state.presentations[0] if st.session_state.presentations else ""
    st.session_state.vto_new = datetime.now()

# Initialize reception number from GSheets state
if 'next_recep' not in st.session_state:
    state = st.session_state.manager.get_state()
    st.session_state.next_recep = str(state.get("last_reception", 0) + 1)

# UI Layout
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("📦 Biosintex - Gestión de Insumos y Rótulos")

with header_col2:
    with st.popover("⚙️ Ajustes", use_container_width=True):
        st.info(f"Conectado a Google Sheets")
        st.divider()
        if st.button("🔄 Actualizar Datos", key="refr_pop"):
            refresh_data()
            st.success("Sincronizado con GSheets")
            
        st.divider()
        with st.expander("🔐 Administración"):
            admin_pass = st.text_input("Contraseña", type="password", key="adm_pass_pop")
            if admin_pass == "biosintex2026":
                st.subheader("⚠️ Peligro")
                reset_confirm = st.text_input("Escriba 'RESET'", key="res_conf_pop")
                if st.button("⚠️ Borrar Todo", type="secondary", key="res_btn_pop"):
                    if reset_confirm == "RESET":
                        success, msg = st.session_state.manager.reset_system()
                        if success:
                            st.success(msg)
                            refresh_data()
                            st.rerun()
                        else:
                            st.error(msg)
            elif admin_pass:
                st.error("Incorrecta")

tab1, tab2 = st.tabs(["📝 Registrar Nuevo Ingreso", "📊 Historial / Edición y Reimpresión"])

staff_options = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]

# --- TAB 1: NEW ENTRY ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Datos del Insumo")
        selected_sku_val = st_searchbox(search_sku, label="Seleccionar SKU (Código o Nombre) *", key="sku_search_new")
        sku_desc = ""
        if selected_sku_val:
            sku_info = next((s for s in st.session_state.skus if str(s['Articulo']) == str(selected_sku_val)), None)
            if sku_info:
                sku_desc = sku_info['Nombre']
                st.info(f"Seleccionado: {sku_desc}")

        lote = st.text_input("Número de Lote *", key="lote_new")
        origen = st.selectbox("Origen *", ["Nacional", "Importado"], key="origen_new")
        vto = st.date_input("Fecha de Vencimiento *", value=datetime.today(), key="vto_new")
        presentacion = st.selectbox("Presentación *", st.session_state.presentations, key="pres_new")
        
    with col2:
        st.subheader("Datos de Recepción")
        udm = st.selectbox("UDM *", ["KG", "UN", "L", "M"], key="udm_new")
        if udm == "UN":
            cantidad = st.number_input("Cantidad Total *", min_value=0, step=1, key="cant_new")
        else:
            cantidad = st.number_input("Cantidad Total *", min_value=0.0, step=0.1, key="cant_new")
            
        bultos = st.number_input("Cantidad de Bultos *", min_value=1, step=1, key="bultos_new")
        search_prov_val = st_searchbox(search_provider, label="Proveedor *", key="prov_search_new")
        remito = st.text_input("Número de Remito *", key="remito_new")
        recepcion_num_display = st.text_input("Nº de recepción (Auto)", value=st.session_state.next_recep, disabled=True)
        
        col_small1, col_small2 = st.columns(2)
        with col_small1: realizado_por = st.selectbox("Realizado por *", ["Seleccione..."] + staff_options, key="realiz_new")
        with col_small2: controlado_por = st.selectbox("Controlado por *", ["Seleccione..."] + staff_options, key="control_new")

    st.markdown("*Campos obligatorios")

    if st.button("🚀 Generar Número de Análisis y Rótulos", type="primary"):
        missing = []
        if not selected_sku_val: missing.append("SKU")
        if not lote: missing.append("Lote")
        if not search_prov_val: missing.append("Proveedor")
        if not remito: missing.append("Remito")
        if cantidad <= 0: missing.append("Cantidad")
        if realizado_por == "Seleccione...": missing.append("Realizado por")
        if controlado_por == "Seleccione...": missing.append("Controlado por")
        
        if missing:
            st.error(f"Faltan: {', '.join(missing)}")
        else:
            analisis_num = st.session_state.manager.generate_next_number()
            recep_num_actual = st.session_state.manager.generate_next_reception()
            
            entry_data = {
                'Fecha': datetime.now().strftime("%d/%m/%Y"),
                'SKU': selected_sku_val,
                'Descripción de Producto': sku_desc,
                'Número de Análisis': analisis_num,
                'Lote': lote,
                'Origen': origen,
                'Cantidad': cantidad,
                'UDM': udm,
                'Cantidad Bultos': bultos,
                'Vto': vto.strftime("%d/%m/%Y"),
                'Proveedor': search_prov_val,
                'Número de Remito': remito,
                'Presentacion': presentacion,
                'recepcion_num': recep_num_actual,
                'realizado_por': realizado_por,
                'controlado_por': controlado_por
            }
            success, message = st.session_state.manager.save_entry(entry_data)
            if success:
                st.success(f"¡Éxito! Análisis: **{analisis_num}** | Recepción: **{recep_num_actual}**")
                st.session_state.next_recep = str(int(recep_num_actual) + 1)
                st.session_state.current_label_data = entry_data
                st.session_state.show_print = True
                reset_form()
                st.rerun()
            else:
                st.error(message)

# --- TAB 2: HISTORY & EDIT ---
with tab2:
    st.subheader("📋 Historial en la Nube")
    history_df = load_all_history()
    
    if history_df.empty:
        st.info("Cargando historial...")
    else:
        search_hist = st.text_input("🔍 Buscar por Análisis, SKU o Producto", "")
        if search_hist:
            mask = history_df.apply(lambda row: row.astype(str).str.contains(search_hist, case=False).any(), axis=1)
            display_df = history_df[mask]
        else:
            display_df = history_df

        for idx, row in display_df.iterrows():
            with st.expander(f"📌 {row['Número de Análisis']} - {row['Descripción de Producto']} ({row['Fecha']})"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_sku = st.text_input("SKU", value=row.get('SKU', ''), key=f"e_sku_{idx}", disabled=True)
                    e_desc = st.text_input("Producto", value=row.get('Descripción de Producto', ''), key=f"e_desc_{idx}")
                    e_lote = st.text_input("Lote", value=row.get('Lote', ''), key=f"e_lote_{idx}")
                    e_vto = st.text_input("Vencimiento", value=str(row.get('Vto', '')), key=f"e_vto_{idx}")
                    e_pres = st.selectbox("Presentación", st.session_state.presentations, 
                                          index=st.session_state.presentations.index(row['Presentacion']) if row['Presentacion'] in st.session_state.presentations else 0,
                                          key=f"e_pres_{idx}")
                with col_e2:
                    e_cant = st.number_input("Cantidad", value=safe_float(row.get('Cantidad', 0.0)), key=f"e_cant_{idx}")
                    e_udm = st.selectbox("UDM", ["KG", "UN", "L", "M"], 
                                         index=["KG", "UN", "L", "M"].index(row['UDM']) if row['UDM'] in ["KG", "UN", "L", "M"] else 0,
                                         key=f"e_udm_{idx}")
                    e_bultos = st.number_input("Bultos", value=safe_int(row.get('Cantidad Bultos', 1)), key=f"e_bultos_{idx}")
                    e_prov = st.text_input("Proveedor", value=row.get('Proveedor', ''), key=f"e_prov_{idx}")
                    e_remito = st.text_input("Remito", value=row.get('Número de Remito', ''), key=f"e_remito_{idx}")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("💾 Guardar Cambios", key=f"btn_save_{idx}"):
                        updated_data = row.to_dict()
                        updated_data.update({'Descripción de Producto': e_desc, 'Lote': e_lote, 'Vto': e_vto, 'Presentacion': e_pres, 'Cantidad': e_cant, 'UDM': e_udm, 'Cantidad Bultos': e_bultos, 'Proveedor': e_prov, 'Número de Remito': e_remito})
                        success, msg = st.session_state.manager.update_entry(row['Número de Análisis'], updated_data)
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)
                with col_btn2:
                    if st.button("🖨️ Reimprimir", key=f"btn_print_{idx}"):
                        st.session_state.current_label_data = row.to_dict()
                        st.session_state.show_print = True
                        st.rerun()

# --- SHARED PRINT PREVIEW ---
if st.session_state.get('show_print'):
    st.divider()
    data = st.session_state.current_label_data
    st.subheader(f"🖨️ Vista Previa: {data['Número de Análisis']}")
    
    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        total_bultos = int(data['Cantidad Bultos'])
        has_partial = st.checkbox("¿Hay un bulto parcial?", key="shared_partial_check")
        partial_qty = 0.0
        if has_partial:
            partial_qty = st.number_input("Cantidad del bulto parcial", min_value=0.0, max_value=float(data['Cantidad']), step=0.1, value=float(data['Cantidad']), key="shared_partial_val")
        if st.button("❌ Cerrar"):
            st.session_state.show_print = False
            st.rerun()

    with col_p2:
        labels_html = """<style>
            @media print { @page { size: 10cm 10cm; margin: 0; } body { margin: 0; padding: 0; } .label-container { page-break-after: always; padding: 0; margin: 0; height: 100vh; display: flex; align-items: center; justify-content: center; } .no-print { display: none !important; } }
            .label-grid { width: 100%; max-width: 500px; border-collapse: collapse; font-family: Arial, sans-serif; border: 2px solid black; table-layout: fixed; background: white; color: black; margin: auto; }
            .label-grid td { border: 1px solid black; padding: 4px 8px; font-size: 14px; font-weight: bold; }
            .large-text { font-size: 28px; text-align: center; }
            .logo-text { color: #0056b3; font-weight: bold; font-size: 18px; }
            .quarantine { font-size: 32px; text-align: center; letter-spacing: 2px; }
            .sub-code { font-size: 10px; font-weight: normal; border: none !important; }
            .grey-bg { background-color: #e0e0e0; }
            .center-text { text-align: center; }
        </style>"""

        for i in range(1, total_bultos + 1):
            if has_partial and i == total_bultos: qty_val = partial_qty
            else: qty_val = data['Cantidad'] / total_bultos if not has_partial else (data['Cantidad'] - partial_qty) / (total_bultos - 1)

            labels_html += f"""
            <div class="label-container" style="margin-bottom: 40px;">
                <table class="label-grid">
                    <tr><td style="width: 35%;">Nº de Analisis</td><td class="large-text" style="width: 40%;">{data['Número de Análisis']}</td><td style="width: 25%; text-align: right;"><span class="logo-text">Biosintex</span></td></tr>
                    <tr><td>Insumo / Producto</td><td colspan="2" class="center-text">{data['Descripción de Producto']}</td></tr>
                    <tr><td>Presentación</td><td colspan="2" class="center-text">{data['Presentacion']}</td></tr>
                    <tr><td>Fecha</td><td colspan="2" class="center-text">{data.get('Fecha', datetime.now().strftime("%d/%m/%Y"))}</td></tr>
                    <tr><td>Nº de lote</td><td>{data['Lote']}</td><td style="padding: 0;"><table style="width: 100%; border-collapse: collapse; height: 100%;"><tr><td style="border: none; border-right: 1px solid black; width: 40%;">Vto.:</td><td style="border: none;">{data['Vto']}</td></tr></table></td></tr>
                    <tr><td>Código interno</td><td colspan="2" class="center-text">{data['SKU']}</td></tr>
                    <tr><td>Origen</td><td colspan="2" class="center-text">{data.get('Origen', 'Nacional')}</td></tr>
                    <tr><td>Proveedor</td><td colspan="2" class="center-text">{data['Proveedor']}</td></tr>
                    <tr class="grey-bg"><td>Bulto Nº</td><td class="center-text">{i}</td><td style="padding: 0;"><table style="width: 100%; border-collapse: collapse; height: 100%;"><tr><td style="border: none; border-right: 1px solid black; width: 40%; text-align: center;">de</td><td style="border: none; text-align: center;">{total_bultos}</td></tr></table></td></tr>
                    <tr class="grey-bg"><td>Cantidad por bulto</td><td class="center-text">{qty_val:.2f} {data['UDM']}</td><td style="padding: 0;"><table style="width: 100%; border-collapse: collapse; height: 100%;"><tr><td style="border: none; border-right: 1px solid black; width: 40%; text-align: center;">Total</td><td style="border: none; text-align: center;">{data['Cantidad']} {data['UDM']}</td></tr></table></td></tr>
                    <tr><td>Nº de Remito</td><td style="font-size: 11px;">{data['Número de Remito']}</td><td style="padding: 0;"><table style="width: 100%; border-collapse: collapse; height: 100%;"><tr><td style="border: none; border-right: 1px solid black; width: 50%; font-size: 10px; text-align: center;">Nº de recepción</td><td style="border: none; text-align: center;">{data.get('recepcion_num', '')}</td></tr></table></td></tr>
                    <tr><td>Realizado por</td><td class="center-text" style="font-size: 12px;">{data.get('realizado_por', '')}</td><td style="padding: 0;"><table style="width: 100%; border-collapse: collapse; height: 100%;"><tr><td style="border: none; border-right: 1px solid black; width: 50%; font-size: 10px; text-align: center;">Controlado por</td><td style="border: none; text-align: center; font-size: 12px;">{data.get('controlado_por', '')}</td></tr></table></td></tr>
                    <tr><td class="sub-code">DP-003-SOP Vigente</td><td colspan="2" class="quarantine">CUARENTENA</td></tr>
                </table>
            </div>"""

        st.components.v1.html(f"""{labels_html}<div class="no-print" style="margin-top: 20px; text-align: center;"><button onclick="window.print()" style="padding: 15px 30px; background-color: #ff4b4b; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 18px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🖨️ Imprimir Rótulos</button></div>""", height=800, scrolling=True)
