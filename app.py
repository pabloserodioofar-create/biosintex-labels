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
    with st.spinner("Conectando con Google Sheets..."):
        data = st.session_state.manager.get_excel_data()
        if 'skus' in data: st.session_state.skus = data['skus']
        if 'providers' in data: st.session_state.providers = data['providers']
        
        if not st.session_state.skus:
            st.error("❌ No se pudieron cargar los datos de SKU. Asegúrate de que la hoja sea PÚBLICA (Cualquier persona con el enlace).")

if not st.session_state.skus:
    refresh_data()

# --- BUSCADORES ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    # Soporte para 'ID' o 'Articulo' segun tus fotos
    results = []
    for s in st.session_state.skus:
        id_val = str(s.get('ID', s.get('Articulo', '')))
        nom_val = str(s.get('Nombre', ''))
        if q.lower() in id_val.lower() or q.lower() in nom_val.lower():
            results.append((f"{id_val} - {nom_val}", id_val))
    return results[:20]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    return [str(p['Proveedor']) for p in st.session_state.providers if 'Proveedor' in p and q.lower() in str(p['Proveedor']).lower()]

# --- UI ---
st.title("📦 Recepción de Insumos")

if st.button("🔄 Forzar Sincronización"):
    refresh_data()
    st.rerun()

col1, col2 = st.columns(2)
with col1:
    sku = st_searchbox(search_sku, label="SKU (ID o Nombre) *", key="sku_s")
    lote = st.text_input("Lote *")
    vto = st.date_input("Vencimiento *")
with col2:
    cant = st.number_input("Cantidad Total *", min_value=0.0)
    bul = st.number_input("Bultos *", min_value=1)
    prov = st_searchbox(search_prov, label="Proveedor *", key="prov_s")
    rem = st.text_input("Remito *")

if st.button("🚀 GENERAR ANÁLISIS", type="primary"):
    if not sku or not lote or not prov:
        st.error("Faltan campos obligatorios")
    else:
        an = st.session_state.manager.generate_next_number()
        rc = st.session_state.manager.generate_next_reception()
        sku_name = ""
        for s in st.session_state.skus:
            if str(s.get('ID', s.get('Articulo', ''))) == str(sku):
                sku_name = s.get('Nombre', '')
                break
        
        entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_name, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'Proveedor': prov, 'Número de Remito': rem, 'recepcion_num': rc}
        ok, m = st.session_state.manager.save_entry(entry)
        if ok:
            st.success(f"¡Generado! Nº Análisis: {an}")
            st.session_state.current_data = entry
            st.session_state.show_p = True
            st.rerun()
        else: st.error(m)

if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    st.subheader(f"Vista Etiqueta: {d['Número de Análisis']}")
    html = f"""<div style="border:3px solid black; padding:20px; background:white; color:black; font-family:Arial; text-align:center;">
        <h1>{d['Número de Análisis']}</h1>
        <p>{d['Descripción de Producto']}</p>
        <p>Lote: {d['Lote']} | Vto: {d['Vto']}</p>
        <div style="background:red; color:white; font-size:30px; padding:10px;">CUARENTENA</div>
        <button onclick="window.print()" style="margin-top:10px; padding:10px; background:green; color:white;">IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=450)
