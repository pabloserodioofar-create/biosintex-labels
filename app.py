import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime
import os

# Link oficial (re-validado)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ/edit#gid=0"

# Page config
st.set_page_config(
    page_title="Biosintex - Gestión de Insumos", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Defaults
if 'skus' not in st.session_state: st.session_state.skus = []
if 'providers' not in st.session_state: st.session_state.providers = []
if 'presentations' not in st.session_state: st.session_state.presentations = ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"]
if 'env' not in st.session_state: st.session_state.env = "Producción"

# CSS
st.markdown("<style>.main { background-color: #f8f9fa; } .stButton>button { background-color: #007bff; color: white; }</style>", unsafe_allow_html=True)

# Manager
if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

def refresh_data():
    data = st.session_state.manager.get_excel_data()
    if "error" in data: st.warning(f"⚠️ {data['error']}")
    if 'skus' in data: st.session_state.skus = data['skus']
    if 'providers' in data: st.session_state.providers = data['providers']
    if 'presentations' in data: st.session_state.presentations = data['presentations']

if not st.session_state.skus: refresh_data()

# Search
def search_sku(q):
    if not q: return []
    return [(f"{s['Articulo']} - {s['Nombre']}", s['Articulo']) for s in st.session_state.skus if q.lower() in str(s['Articulo']).lower() or q.lower() in str(s['Nombre']).lower()]

def search_prov(q):
    if not q: return []
    return [p['Proveedor'] for p in st.session_state.providers if q.lower() in str(p['Proveedor']).lower()]

# History
def load_all_history():
    try:
        df = st.session_state.manager.conn.read(spreadsheet=SHEET_URL, worksheet="Datos a completar", ttl=0)
        if not df.empty:
            if 'Nº de Análisis' in df.columns: df = df.rename(columns={'Nº de Análisis': 'Número de Análisis'})
            return df.iloc[::-1]
    except: pass
    return pd.DataFrame()

# Reception number check
try:
    state = st.session_state.manager.get_state()
    next_rec = str(state.get("last_reception", 0) + 1)
except:
    next_rec = "1"

# UI Header
h1, h2 = st.columns([5, 1])
with h1: st.title("📦 Biosintex - Gestión de Insumos")
with h2:
    with st.popover("⚙️ Ajustes"):
        if st.button("🔄 Sincronizar"): refresh_data(); st.rerun()
        st.divider()
        with st.expander("🔐 Admin"):
            if st.text_input("Pass", type="password") == "biosintex2026":
                if st.button("⚠️ Reset"): st.session_state.manager.reset_system(); st.rerun()

t1, t2 = st.tabs(["📝 Registro", "📊 Historial"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        sku = st_searchbox(search_sku, label="SKU *", key="sku_q")
        lote = st.text_input("Lote *", key="lote")
        vto = st.date_input("Vencimiento *", key="vto")
        pres = st.selectbox("Presentación *", st.session_state.presentations, key="pres")
    with c2:
        st.subheader("Recepción")
        udm = st.selectbox("UDM *", ["KG", "UN", "L", "M"], key="udm")
        cant = st.number_input("Cantidad Total *", min_value=0.0, key="cant")
        bultos = st.number_input("Bultos *", min_value=1, key="bult")
        prov = st_searchbox(search_prov, label="Proveedor *", key="prov_q")
        remito = st.text_input("Remito *", key="rem")
        st.text_input("Recepción (Auto)", value=next_rec, disabled=True)
        staff = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]
        cm1, cm2 = st.columns(2)
        with cm1: real = st.selectbox("Realizado por *", ["Seleccione..."] + staff, key="real")
        with cm2: cont = st.selectbox("Controlado por *", ["Seleccione..."] + staff, key="cont")

    if st.button("🚀 Generar Análisis", type="primary"):
        if not sku or not lote or not prov or real=="Seleccione..." or cont=="Seleccione...": st.error("Faltan datos")
        else:
            an = st.session_state.manager.generate_next_number()
            rec = st.session_state.manager.generate_next_reception()
            sku_name = next((s['Nombre'] for s in st.session_state.skus if str(s['Articulo']) == str(sku)), "")
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_name, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'UDM': udm, 'Cantidad Bultos': bultos, 'Vto': vto.strftime("%d/%m/%Y"), 'Proveedor': prov, 'Número de Remito': remito, 'Presentacion': pres, 'recepcion_num': rec, 'realizado_por': real, 'controlado_por': cont}
            ok, m = st.session_state.manager.save_entry(entry)
            if ok: st.success(f"Éxito: {an}"); st.session_state.current_label_data = entry; st.session_state.show_print = True; st.rerun()
            else: st.error(m)

with t2:
    hist = load_all_history()
    if not hist.empty:
        for i, r in hist.head(20).iterrows():
            with st.expander(f"📌 {r['Número de Análisis']} - {r['Descripción de Producto']}"):
                if st.button("🖨️ Reimprimir", key=f"p_{i}"): st.session_state.current_label_data = r.to_dict(); st.session_state.show_print = True; st.rerun()

if st.session_state.get('show_print'):
    d = st.session_state.current_label_data
    if st.button("❌ Cerrar"): st.session_state.show_print = False; st.rerun()
    html = f"""<div style="border:2px solid black; padding:10px; font-family:Arial; width:300px; margin:auto; background:white;">
        <h2 style="text-align:center;">{d['Número de Análisis']}</h2>
        <p><b>Insumo:</b> {d['Descripción de Producto']}</p>
        <p><b>Lote:</b> {d['Lote']} | <b>Vto:</b> {d['Vto']}</p>
        <p><b>Bultos:</b> {d['Cantidad Bultos']}</p>
        <div style="text-align:center; font-size:24px; font-weight:bold; color:red; border:2px solid red;">CUARENTENA</div>
        <button onclick="window.print()" style="width:100%; margin-top:10px; padding:10px; background:red; color:white; border:none; cursor:pointer;">IMPRIMIR RÓTULOS</button>
    </div>"""
    st.components.v1.html(html, height=400)
