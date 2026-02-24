import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# URL Directa oficial limpia
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Gestión Biosintex", layout="wide")

if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

if 'env' not in st.session_state:
    st.session_state.env = "Producción"

# --- LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>� Acceso Reservado</h2>", unsafe_allow_html=True)
        _, col, _ = st.columns([1,2,1])
        with col:
            with st.form("Login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Entrar"):
                    if u == "biosintex" and p == "2026":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else: st.error("Error")
        return False
    return True

if not check_password(): st.stop()

# --- CARGA ---
def refresh_data():
    with st.spinner("Sincronizando con la nube..."):
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])
        if data.get('error'):
            # Si hay error 404, mostramos una sugerencia de permisos
            st.error(f"Error de conexión: {data['error']}")
            st.info("💡 Sugerencia: Revisa que la hoja de Google esté compartida como 'Cualquier persona con el enlace' y rol 'Editor'.")

if 'skus' not in st.session_state: refresh_data()

# --- BUSCADORES ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    q_low = q.lower()
    return [(f"{s.get('Articulo', '')} - {s.get('Nombre', '')}", s.get('Articulo', '')) 
            for s in st.session_state.skus if q_low in str(s).lower()]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    q_low = q.lower()
    res = []
    for p in st.session_state.providers:
        # Buscamos por ID o por Proveedor (Celda A1 o B1)
        id_p = str(p.get('ID', ''))
        nom_p = str(p.get('Proveedor', ''))
        if q_low in id_p.lower() or q_low in nom_p.lower():
            res.append(nom_p)
    return list(set(res)) # Sin repetir

# --- UI ---
st.title("📦 Recepción de Insumos")

with st.sidebar:
    st.header("⚙️ Ajustes")
    nuevo_env = st.radio("Entorno:", ["Producción", "Pruebas"])
    if nuevo_env != st.session_state.env:
        st.session_state.env = nuevo_env
        st.rerun()
    if st.button("🔄 Sincronizar"): refresh_data(); st.rerun()

tab1, tab2 = st.tabs(["📝 Registro", "📊 Historial"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Producto")
        sku = st_searchbox(search_sku, label="Buscar SKU *", key="sku_main")
        lote = st.text_input("Lote *")
        vto = st.date_input("Vencimiento *")
    with c2:
        st.subheader("Proveedor")
        prov = st_searchbox(search_prov, label="Buscar Proveedor (ID o Nombre) *", key="prov_main")
        cant = st.number_input("Cantidad *", min_value=0.0)
        rem = st.text_input("Remito *")

    if st.button("🚀 GENERAR ANÁLISIS", type="primary"):
        if not sku or not lote or not prov: st.error("Faltan datos")
        else:
            an = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'Proveedor': prov, 'Número de Remito': rem, 'recepcion_num': rc, 'Entorno': st.session_state.env}
            ok, m = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else: st.error(m)

if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    if st.button("❌ Cerrar"): st.session_state.show_p = False; st.rerun()
    html = f"""<div style="border:4px solid black; padding:15px; background:white; color:black; font-family:Arial; text-align:center;">
        <h1 style="font-size:45px; margin:0;">{d['Número de Análisis']}</h1>
        <p>SKU: {d['SKU']} | Lote: {d['Lote']}</p>
        <div style="background:red; color:white; font-size:40px; font-weight:bold; padding:20px;">CUARENTENA</div>
        <button onclick="window.print()" style="margin-top:15px; padding:10px 20px; background:green; color:white;">IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=450)
