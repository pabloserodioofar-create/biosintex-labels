import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# URL Directa limpia
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Biosintex - Gestión de Insumos", layout="wide")

# --- SISTEMA DE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center;'>🔒 Acceso Privado Biosintex</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("Login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Entrar"):
                    if u == "biosintex" and p == "2026":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
        return False
    return True

if not check_password():
    st.stop()

# --- INICIALIZACION (Limpieza de memoria vieja) ---
if 'manager' not in st.session_state or not hasattr(st.session_state.manager, 'get_history'):
    st.session_state.manager = AnalysisManager(SHEET_URL)

if 'env' not in st.session_state:
    st.session_state.env = "Producción"

def refresh_data():
    with st.spinner(f"Cargando datos de {st.session_state.env}..."):
        # Llamada simplificada para evitar TypeErrors
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])

if 'skus' not in st.session_state:
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

# --- UI ---
h1, h2 = st.columns([4, 1])
with h1: st.title(f"📦 Biosintex - {st.session_state.env}")
with h2:
    with st.popover("⚙️ Entorno"):
        nuevo = st.radio("Entorno:", ["Producción", "Pruebas"], 
                        index=0 if st.session_state.env == "Producción" else 1)
        if nuevo != st.session_state.env:
            st.session_state.env = nuevo
            st.rerun()
        if st.button("🔄 Sincronizar"): refresh_data(); st.rerun()

tab1, tab2 = st.tabs(["📝 Nuevo Registro", "📊 Historial / Reimpresión"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        sku = st_searchbox(search_sku, label="SKU (ID o Nombre) *", key="sku_input")
        sku_name = ""
        if sku:
            for s in st.session_state.skus:
                if str(s.get('ID', s.get('Articulo', ''))) == str(sku):
                    sku_name = s.get('Nombre', '')
                    st.info(f"Producto: {sku_name}"); break
        lote = st.text_input("Lote *", key="lot_in")
        vto = st.date_input("Vencimiento *", key="vto_in")

    with c2:
        st.subheader("Recepción")
        cant = st.number_input("Cantidad Total *", min_value=0.0, key="can_in")
        bul = st.number_input("Bultos *", min_value=1, key="bul_in")
        prov = st_searchbox(search_prov, label="Proveedor *", key="pro_in")
        rem = st.text_input("Remito *", key="rem_in")
        
        state_v = st.session_state.manager.get_state(env=st.session_state.env)
        st.text_input("Recepción (Auto)", value=str(state_v.get("last_reception", 0)+1), disabled=True)

    if st.button("🚀 GENERAR ETIQUETA", type="primary", use_container_width=True):
        if not sku or not lote or not prov:
            st.error("Campos incompletos")
        else:
            an = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_name, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'Proveedor': prov, 'Número de Remito': rem, 'recepcion_num': rc}
            ok, m = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else: st.error(m)

with tab2:
    h_df = st.session_state.manager.get_history(env=st.session_state.env)
    if not h_df.empty:
        st.dataframe(h_df.iloc[::-1], use_container_width=True)
        sel = st.selectbox("Reimprimir análisis:", h_df['Número de Análisis'].tolist())
        if st.button("🖨️ Ver Etiqueta"):
            st.session_state.current_data = h_df[h_df['Número de Análisis'] == sel].iloc[0].to_dict()
            st.session_state.show_p = True
            st.rerun()
    else: st.info("Sin registros.")

if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    if st.button("❌ Cerrar"): st.session_state.show_p = False; st.rerun()
    html = f"""<div style="border:4px solid black; padding:15px; background:white; color:black; font-family:Arial; text-align:center;">
        <h1 style="font-size:45px; margin:0;">{d['Número de Análisis']}</h1><hr>
        <p><b>{d.get('Descripción de Producto','')}</b></p>
        <p>SKU: {d['SKU']} | Lote: {d['Lote']}</p>
        <div style="background:red; color:white; font-size:35px; font-weight:bold; padding:15px; border:2px solid black;">CUARENTENA</div>
        <button onclick="window.print()" style="margin-top:15px; padding:10px 20px; background:green; color:white; cursor:pointer;">IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=500)
