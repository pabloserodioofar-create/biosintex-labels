import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# ID de documento verificado
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Recepción Biosintex", layout="wide")

# --- LOGIN ---
if "password_correct" not in st.session_state:
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Reservado Biosintex</h2>", unsafe_allow_html=True)
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
    st.session_state.manager = AnalysisManager(SHEET_URL)
if 'env' not in st.session_state:
    st.session_state.env = "Producción"

def refresh_data():
    with st.spinner("Sincronizando proveedores..."):
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])
        if data.get('error') and not st.session_state.providers:
            st.error(f"Error en proveedores: {data['error']}")

if 'skus' not in st.session_state or not st.session_state.skus:
    refresh_data()

# --- BUSQUEDA ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    q = q.lower()
    return [(f"{str(s.get('Articulo',''))} - {str(s.get('Nombre',''))}", str(s.get('Articulo',''))) 
            for s in st.session_state.skus if q in str(s).lower()]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    q = q.lower()
    res = []
    for p in st.session_state.providers:
        # Buscamos en todas las posibles columnas: ID, Proveedor, Nombre
        entero = " ".join([str(v) for v in p.values()]).lower()
        if q in entero:
            # Mostramos el valor de la columna 'Proveedor' o la que tenga texto
            nombre = p.get('Proveedor', p.get('nombre', p.get('PROVEEDOR', '')))
            if not nombre: # Si no tiene nombre de columna, sacamos el segundo valor
                nombre = list(p.values())[1] if len(p.values()) > 1 else list(p.values())[0]
            res.append(str(nombre))
    return list(set(res))

# --- UI ---
st.title(f"📦 Recepción de Insumos ({st.session_state.env})")

with st.sidebar:
    st.header("⚙️ Ajustes")
    env = st.radio("Entorno:", ["Producción", "Pruebas"], index=0 if st.session_state.env=="Producción" else 1)
    if env != st.session_state.env:
        st.session_state.env = env
        st.rerun()
    st.button("🔄 Sincronizar Todo", on_click=refresh_data)

tab1, tab2 = st.tabs(["📝 Registro", "📊 Historial"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Insumo")
        sku = st_searchbox(search_sku, label="Buscar Insumo *", key="sku_in")
        sku_desc = ""
        if sku:
            for s in st.session_state.skus:
                if str(s.get('Articulo','')) == str(sku):
                    sku_desc = s.get('Nombre','')
                    st.info(f"✅ PRODUCTO: {sku_desc}"); break
        lote = st.text_input("Número de Lote *")
        vto = st.date_input("Vencimiento *")
        pres = st.selectbox("Presentación *", ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"])

    with c2:
        st.subheader("Recepción")
        udm = st.selectbox("Unidad (UDM) *", ["KG", "UN", "L", "M"])
        cant = st.number_input("Cantidad Total *", min_value=0.0)
        bul = st.number_input("Bultos *", min_value=1, step=1)
        prov = st_searchbox(search_prov, label="Proveedor (Nombre o ID) *", key="prov_in")
        rem = st.text_input("Nº Remito *")
        
        st.text_input("Recepción (Auto)", value=str(st.session_state.manager.get_state(env=st.session_state.env).get("last_reception", 0)+1), disabled=True)
        
        staff = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]
        sm1, sm2 = st.columns(2)
        with sm1: real = st.selectbox("Realizado por *", ["Seleccione..."] + staff)
        with sm2: cont = st.selectbox("Controlado por *", ["Seleccione..."] + staff)

    if st.button("🚀 GENERAR ANÁLISIS", type="primary", use_container_width=True):
        if not sku or not lote or not prov or real=="Seleccione...":
            st.error("⚠️ Faltan datos obligatorios.")
        else:
            an = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            entry = {'Fecha': datetime.now().strftime("%d/%m/%Y"), 'SKU': sku, 'Descripción de Producto': sku_desc, 'Número de Análisis': an, 'Lote': lote, 'Vto': vto.strftime("%d/%m/%Y"), 'Cantidad': cant, 'UDM': udm, 'Cantidad Bultos': bul, 'Proveedor': prov, 'Número de Remito': rem, 'recepcion_num': int(rc), 'realizado_por': real, 'controlado_por': cont, 'Entorno': st.session_state.env}
            ok, msg = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.session_state.current_label = entry
                st.session_state.show_label = True
                st.rerun()
            else: st.error(msg)

if st.session_state.get('show_label'):
    d = st.session_state.current_label
    st.divider()
    if st.button("❌ Cerrar"): st.session_state.show_label = False; st.rerun()
    html = f"""<div style="border:5px solid black; padding:20px; background:white; color:black; font-family:Arial; text-align:center; width:350px; margin:auto;">
        <h1 style="font-size:50px; margin:0;">{d['Número de Análisis']}</h1><hr>
        <p><b>{d.get('Descripción de Producto', 'INSUMO')}</b></p>
        <p>SKU: {d['SKU']} | Lote: {d['Lote']}</p>
        <div style="background:red; color:white; font-size:40px; font-weight:bold; padding:20px; border:2px solid black;">CUARENTENA</div>
        <button onclick="window.print()" style="margin-top:20px; padding:15px; width:100%; background:green; color:white; font-weight:bold; cursor:pointer;">🖨️ IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=500)
