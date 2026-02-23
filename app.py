import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# URL BASE (Sin nada extra al final para evitar errores 400)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Biosintex - Gestión de Insumos", layout="wide", initial_sidebar_state="collapsed")

if 'skus' not in st.session_state: st.session_state.skus = []
if 'providers' not in st.session_state: st.session_state.providers = []
if 'presentations' not in st.session_state: st.session_state.presentations = ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"]

if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

def refresh_data():
    data = st.session_state.manager.get_excel_data()
    if "error" in data: st.warning(f"💡 Sugerencia: {data['error']}. Asegúrate de que las pestañas tengan al menos una fila con títulos.")
    if 'skus' in data: st.session_state.skus = data['skus']
    if 'providers' in data: st.session_state.providers = data['providers']
    if 'presentations' in data:
        # Combinar con las básicas
        new_pres = list(set(st.session_state.presentations + data['presentations']))
        st.session_state.presentations = sorted(new_pres)

if not st.session_state.skus: refresh_data()

# --- BUSCADORES ---
def search_sku(q):
    if not q: return []
    return [(f"{s['Articulo']} - {s['Nombre']}", s['Articulo']) for s in st.session_state.skus if q.lower() in str(s['Articulo']).lower() or q.lower() in str(s['Nombre']).lower()]

def search_prov(q):
    if not q: return []
    return [p['Proveedor'] for p in st.session_state.providers if q.lower() in str(p['Proveedor']).lower()]

# --- UI ---
h1, h2 = st.columns([5, 1])
with h1: st.title("📦 Biosintex")
with h2:
    if st.button("🔄 Sincronizar"): refresh_data(); st.rerun()

tab1, tab2 = st.tabs(["📝 Registro", "📊 Historial"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        sku = st_searchbox(search_sku, label="SKU *", key="sku_q")
        lote = st.text_input("Lote *", key="lote")
        vto = st.date_input("Vencimiento *", key="vto")
        pres = st.selectbox("Presentación *", st.session_state.presentations, key="pres")
    with c2:
        udm = st.selectbox("UDM *", ["KG", "UN", "L", "M"], key="udm")
        cant = st.number_input("Cantidad *", min_value=0.0, key="cant")
        bultos = st.number_input("Bultos *", min_value=1, key="bult")
        prov = st_searchbox(search_prov, label="Proveedor *", key="prov_q")
        remito = st.text_input("Remito *", key="rem")
        
    if st.button("🚀 Generar Análisis", type="primary"):
        if not sku or not lote or not prov: st.error("Faltan datos obligatorios")
        else:
            an = st.session_state.manager.generate_next_number()
            rec = st.session_state.manager.generate_next_reception()
            sku_name = next((s['Nombre'] for s in st.session_state.skus if str(s['Articulo']) == str(sku)), "Insumo")
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_name, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'UDM': udm, 'Cantidad Bultos': bultos, 'Vto': vto.strftime("%d/%m/%Y"), 'Proveedor': prov, 'Número de Remito': remito, 'Presentacion': pres, 'recepcion_num': rec}
            ok, m = st.session_state.manager.save_entry(entry)
            if ok: 
                st.success(f"Éxito: {an}")
                st.session_state.current_label_data = entry
                st.session_state.show_print = True
                st.rerun()
            else: st.error(m)

if st.session_state.get('show_print'):
    d = st.session_state.current_label_data
    st.divider()
    st.subheader(f"Vista Previa: {d['Número de Análisis']}")
    if st.button("❌ Cerrar"): st.session_state.show_print = False; st.rerun()
    html = f"""<div style="border:2px solid black; padding:20px; font-family:Arial; background:white; color:black;">
        <h2>ANÁLISIS: {d['Número de Análisis']}</h2>
        <p><b>Producto:</b> {d['Descripción de Producto']}</p>
        <p><b>Lote:</b> {d['Lote']} | <b>Vencimiento:</b> {d['Vto']}</p>
        <div style="font-size:30px; color:red; border:3px solid red; text-align:center; padding:10px;">CUARENTENA</div>
        <button onclick="window.print()" style="width:100%; height:50px; background:red; color:white; font-weight:bold; margin-top:20px; cursor:pointer;">IMPRIMIR RÓTULOS</button>
    </div>"""
    st.components.v1.html(html, height=450)
