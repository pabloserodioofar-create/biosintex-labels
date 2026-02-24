import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# URL Directa limpia
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Sistema Biosintex", layout="wide")

if 'skus' not in st.session_state: st.session_state.skus = []
if 'providers' not in st.session_state: st.session_state.providers = []

if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

def refresh_data():
    with st.spinner("Sincronizando con Google Sheets..."):
        data = st.session_state.manager.get_excel_data()
        if 'skus' in data: st.session_state.skus = data['skus']
        if 'providers' in data: st.session_state.providers = data['providers']

def load_history():
    try:
        # Intentamos leer la pestaña de datos
        df = st.session_state.manager.conn.read(spreadsheet=SHEET_URL, worksheet="Datos a completar", ttl=0)
        if not df.empty:
            return df.iloc[::-1] # Mostrar los más nuevos arriba
    except:
        pass
    return pd.DataFrame()

if not st.session_state.skus:
    refresh_data()

# --- BUSCADORES ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    res = []
    for s in st.session_state.skus:
        id_v = str(s.get('ID', s.get('Articulo', '')))
        nom_v = str(s.get('Nombre', ''))
        if q.lower() in id_v.lower() or q.lower() in nom_v.lower():
            res.append((f"{id_v} - {nom_v}", id_v))
    return res[:20]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    return [str(p['Proveedor']) for p in st.session_state.providers if 'Proveedor' in p and q.lower() in str(p['Proveedor']).lower()]

# --- UI PRINCIPAL ---
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title("📦 Recepción de Insumos Biosintex")
with col_t2:
    if st.button("🔄 Sincronizar"):
        refresh_data()
        st.rerun()

# --- TABS (ESTO ES LO QUE FALTABA) ---
tab1, tab2 = st.tabs(["📝 Nuevo Registro", "📊 Ver Historial"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        sku = st_searchbox(search_sku, label="Buscar SKU (ID o Nombre) *", key="sku_s")
        sku_name = ""
        if sku:
            for s in st.session_state.skus:
                if str(s.get('ID', s.get('Articulo', ''))) == str(sku):
                    sku_name = s.get('Nombre', '')
                    st.info(f"Producto: {sku_name}")
                    break
        lote = st.text_input("Lote *", key="lote_f")
        vto = st.date_input("Vencimiento *", key="vto_f")
    with c2:
        st.subheader("Recepción")
        cant = st.number_input("Cantidad Total *", min_value=0.0, key="cant_f")
        bul = st.number_input("Bultos *", min_value=1, key="bul_f")
        prov = st_searchbox(search_prov, label="Proveedor *", key="prov_s")
        rem = st.text_input("Remito *", key="rem_f")
        
    st.markdown("---")
    if st.button("🚀 GENERAR ANÁLISIS Y ETIQUETA", type="primary", use_container_width=True):
        if not sku or not lote or not prov:
            st.error("Faltan datos obligatorios")
        else:
            an = st.session_state.manager.generate_next_number()
            rc = st.session_state.manager.generate_next_reception()
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_name, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'Proveedor': prov, 'Número de Remito': rem, 'recepcion_num': rc}
            ok, m = st.session_state.manager.save_entry(entry)
            if ok:
                st.success(f"¡Éxito! Análisis generado: {an}")
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else: st.error(m)

with tab2:
    st.subheader("Últimos Ingresos Registrados")
    hist_df = load_history()
    if not hist_df.empty:
        # Mostramos una tabla con los datos
        columns_to_show = ['Fecha', 'Número de Análisis', 'SKU', 'Descripción de Producto', 'Lote', 'Proveedor']
        st.dataframe(hist_df[columns_to_show], use_container_width=True)
        
        # Botón para reimprimir
        st.write("---")
        st.write("### Reimprimir Etiqueta")
        an_to_print = st.selectbox("Seleccione Número de Análisis", hist_df['Número de Análisis'].tolist())
        if st.button("🖨️ Ver etiqueta para reimprimir"):
            fila = hist_df[hist_df['Número de Análisis'] == an_to_print].iloc[0]
            st.session_state.current_data = fila.to_dict()
            st.session_state.show_p = True
            st.rerun()
    else:
        st.info("Aún no hay registros en la planilla de Google.")

# --- VISTA DE IMPRESION ---
if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    st.subheader(f"Vista Previa: {d['Número de Análisis']}")
    if st.button("❌ Cerrar Vista Previa"):
        st.session_state.show_p = False
        st.rerun()
    
    html = f"""<div style="border:3px solid black; padding:20px; background:white; color:black; font-family:Arial; text-align:center;">
        <h1 style="margin:0; font-size:40px;">{d['Número de Análisis']}</h1>
        <hr>
        <p style="font-size:18px;"><b>{d.get('Descripción de Producto', 'INSUMO')}</b></p>
        <p>SKU: {d['SKU']} | Lote: {d['Lote']}</p>
        <p>Vencimiento: {d.get('Vto', 'S/V')}</p>
        <div style="background:red; color:white; font-size:35px; font-weight:bold; padding:15px; margin-top:10px; border:2px solid black;">CUARENTENA</div>
        <button onclick="window.print()" style="width:100%; margin-top:20px; padding:15px; background:green; color:white; font-weight:bold; cursor:pointer; font-size:18px; border-radius:10px;">🖨️ IMPRIMIR AHORA</button>
    </div>"""
    st.components.v1.html(html, height=500)
