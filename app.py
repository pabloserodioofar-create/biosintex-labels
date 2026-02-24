import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# URL Directa oficial
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Biosintex - Gestión de Insumos", layout="wide")

# Limpieza de memoria para asegurar que use la lógica nueva
if 'manager' not in st.session_state or not hasattr(st.session_state.manager, 'get_excel_data'):
    st.session_state.manager = AnalysisManager(SHEET_URL)

if 'env' not in st.session_state:
    st.session_state.env = "Producción"

# --- LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center;'>🔒 Acceso Biosintex</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            with st.form("Login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Entrar"):
                    if u == "biosintex" and p == "2026":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else: st.error("Error de acceso")
        return False
    return True

if not check_password(): st.stop()

# --- CARGA DE DATOS ---
def refresh_data():
    with st.spinner(f"Cargando datos de Google Sheets..."):
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])
        if data.get('error'):
            st.error(f"Error técnico de conexión: {data['error']}")
        elif not st.session_state.skus:
            st.warning("⚠️ No se encontraron productos en la pestaña 'SKU'. Revisa que la hoja tenga datos debajo de los títulos.")

if 'skus' not in st.session_state:
    refresh_data()

# --- BUSCADORES ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    res = []
    q_low = q.lower()
    for s in st.session_state.skus:
        # Buscamos por ID (según tu imagen) o por Nombre
        cod = str(s.get('ID', s.get('Articulo', '')))
        nom = str(s.get('Nombre', ''))
        if q_low in cod.lower() or q_low in nom.lower():
            res.append((f"{cod} - {nom}", cod))
    return res[:20]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    q_low = q.lower()
    return [str(p['Proveedor']) for p in st.session_state.providers if 'Proveedor' in p and q_low in str(p['Proveedor']).lower()]

# --- UI PRINCIPAL ---
st.title(f"📦 Biosintex ({st.session_state.env})")

with st.sidebar:
    st.subheader("⚙️ Configuración")
    nuevo = st.radio("Entorno:", ["Producción", "Pruebas"], index=0 if st.session_state.env == "Producción" else 1)
    if nuevo != st.session_state.env:
        st.session_state.env = nuevo
        st.rerun()
    if st.button("🔄 Sincronizar Datos"):
        refresh_data()
        st.rerun()
    st.divider()
    if st.button("🚪 Salir"):
        del st.session_state["password_correct"]
        st.rerun()

tab1, tab2 = st.tabs(["📝 Nuevo Registro", "📊 Historial"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        sku = st_searchbox(search_sku, label="Buscar SKU (ID o Nombre) *", key="sku_main")
        sku_name = ""
        if sku:
            for s in st.session_state.skus:
                if str(s.get('ID', s.get('Articulo', ''))) == str(sku):
                    sku_name = s.get('Nombre', '')
                    st.info(f"Producto: {sku_name}"); break
        lote = st.text_input("Lote *")
        vto = st.date_input("Vencimiento *")
    with c2:
        st.subheader("Recepción")
        cant = st.number_input("Cantidad Total *", min_value=0.0)
        bul = st.number_input("Bultos *", min_value=1)
        prov = st_searchbox(search_prov, label="Proveedor *", key="prov_main")
        rem = st.text_input("Remito *")
        st.text_input("Nº Recepción (Auto)", value=str(st.session_state.manager.get_state(env=st.session_state.env).get("last_reception", 0)+1), disabled=True)

    if st.button("🚀 GENERAR ANÁLISIS", type="primary", use_container_width=True):
        if not sku or not lote or not prov: st.error("Faltan datos")
        else:
            an = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_name, 'Número de Análisis': an, 'Lote': lote, 'Cantidad': cant, 'Proveedor': prov, 'Número de Remito': rem, 'recepcion_num': rc, 'Entorno': st.session_state.env}
            ok, m = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else: st.error(m)

with tab2:
    hist = st.session_state.manager.get_history(env=st.session_state.env)
    if not hist.empty:
        st.dataframe(hist.iloc[::-1], use_container_width=True)
    else: st.info("Sin registros.")

if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    if st.button("❌ Cerrar"): st.session_state.show_p = False; st.rerun()
    html = f"""<div style="border:5px solid black; padding:15px; background:white; color:black; font-family:Arial; text-align:center;">
        <h1 style="font-size:45px; margin:0;">{d['Número de Análisis']}</h1><hr>
        <p><b>{d['Descripción de Producto']}</b></p>
        <p>Lote: {d['Lote']} | SKU: {d['SKU']}</p>
        <div style="background:red; color:white; font-size:35px; font-weight:bold; padding:15px; border:2px solid black;">CUARENTENA</div>
        <button onclick="window.print()" style="margin-top:15px; padding:10px 20px; background:green; color:white; cursor:pointer;">IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=500)
