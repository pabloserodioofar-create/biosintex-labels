import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# URL Directa oficial
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Sistema Biosintex", layout="wide")

# --- LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Sistema Rótulos</h2>", unsafe_allow_html=True)
        _, col, _ = st.columns([1,1.5,1])
        with col:
            with st.form("Login"):
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Ingresar"):
                    if u == "biosintex" and p == "2026":
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else: st.error("❌ Credenciales incorrectas")
        return False
    return True

if not check_password(): st.stop()

# --- INITIALIZATION ---
if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)
if 'env' not in st.session_state:
    st.session_state.env = "Producción"
if 'skus' not in st.session_state:
    st.session_state.skus = []
if 'providers' not in st.session_state:
    st.session_state.providers = []

def refresh_data():
    with st.spinner("Sincronizando con Google Sheets..."):
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])
        if data.get('error'):
            st.error(f"Aviso técnico: {data['error']}")
        elif not st.session_state.skus:
            st.warning("⚠️ No se cargaron SKUs. Revisa que la pestaña 'SKU' tenga datos.")

if not st.session_state.skus:
    refresh_data()

# --- SEARCH LOGIC ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    q_low = q.lower()
    res = []
    # Buscamos en ID, Articulo o Nombre
    for s in st.session_state.skus:
        art = str(s.get('Articulo', s.get('ID', '')))
        nom = str(s.get('Nombre', ''))
        if q_low in art.lower() or q_low in nom.lower():
            if art and nom: res.append((f"{art} - {nom}", art))
    return res[:30]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    q_low = q.lower()
    res = []
    for p in st.session_state.providers:
        pid = str(p.get('ID', ''))
        pnom = str(p.get('Proveedor', ''))
        if q_low in pid.lower() or q_low in pnom.lower():
            res.append(pnom)
    return list(set(res))

# --- MAIN UI ---
st.title(f"📦 Biosintex ({st.session_state.env})")

with st.sidebar:
    st.header("⚙️ Ajustes")
    nuevo_env = st.radio("Entorno:", ["Producción", "Pruebas"], index=0 if st.session_state.env=="Producción" else 1)
    if nuevo_env != st.session_state.env:
        st.session_state.env = nuevo_env
        refresh_data()
        st.rerun()
    st.button("🔄 Sincronizar Todo", on_click=refresh_data)
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

tab1, tab2 = st.tabs(["📝 Generar Rótulo", "📊 Historial"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Información Insumo")
        sku_val = st_searchbox(search_sku, label="Buscar SKU *", key="sku_main")
        sku_name = ""
        if sku_val:
            for s in st.session_state.skus:
                if str(s.get('Articulo', s.get('ID',''))) == str(sku_val):
                    sku_name = s.get('Nombre', '')
                    st.info(f"✅ PRODUCTO: {sku_name}")
                    break
        lote = st.text_input("Número de Lote *")
        vto = st.date_input("Vencimiento *")
        orig = st.selectbox("Origen *", ["Nacional", "Importado"])
        pres = st.selectbox("Presentación *", ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"])

    with c2:
        st.subheader("Información Recepción")
        udm = st.selectbox("Unidad (UDM) *", ["KG", "UN", "L", "M"])
        cant = st.number_input("Cantidad Total *", min_value=0.0, step=1.0 if udm=="UN" else 0.1)
        bult = st.number_input("Cantidad Bultos *", min_value=1, step=1)
        prov_val = st_searchbox(search_prov, label="Proveedor (Nombre o ID) *", key="prov_main")
        rem = st.text_input("Nº Remito *")
        
        # State
        st.text_input("Nº Recepción (Auto)", value=str(st.session_state.manager.get_state(env=st.session_state.env).get("last_reception", 0)+1), disabled=True)
        
        staff = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]
        sm1, sm2 = st.columns(2)
        with sm1: real = st.selectbox("Realizado por *", ["Seleccione..."] + staff)
        with sm2: cont = st.selectbox("Controlado por *", ["Seleccione..."] + staff)

    if st.button("🚀 GENERAR ANÁLISIS Y RÓTULOS", type="primary", use_container_width=True):
        if not sku_val or not lote or not prov_val or real=="Seleccione..." or cant <= 0:
            st.error("⚠️ Faltan datos obligatorios.")
        else:
            an = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            
            entry = {
                'Fecha': datetime.now().strftime("%d/%m/%Y"),
                'SKU': sku_val,
                'Descripción de Producto': sku_name,
                'Número de Análisis': an,
                'Lote': lote,
                'Vto': vto.strftime("%d/%m/%Y"),
                'Cantidad': cant,
                'UDM': udm,
                'Cantidad Bultos': bult,
                'Proveedor': prov_val,
                'Número de Remito': rem,
                'Presentacion': pres,
                'Origen': orig,
                'recepcion_num': rc,
                'realizado_por': real,
                'controlado_por': cont,
                'Entorno': st.session_state.env
            }
            
            ok, msg = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.success(f"✅ ¡Generado! Análisis: {an}")
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else: st.error(f"Error: {msg}")

with tab2:
    st.subheader(f"Historial {st.session_state.env}")
    h_df = st.session_state.manager.get_history(env=st.session_state.env)
    if not h_df.empty:
        st.dataframe(h_df.iloc[::-1], use_container_width=True)
        st.divider()
        sel = st.selectbox("Reimprimir rótulo:", h_df['Número de Análisis'].unique().tolist() if 'Número de Análisis' in h_df.columns else [])
        if st.button("🖨️ Ver etiqueta"):
            st.session_state.current_data = h_df[h_df['Número de Análisis'] == sel].iloc[0].to_dict()
            st.session_state.show_p = True
            st.rerun()
    else: st.info("Sin registros.")

if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    if st.button("❌ Cerrar"): st.session_state.show_p = False; st.rerun()
    
    html = f"""<div style="background: white; color: black; border: 5px solid black; padding: 20px; text-align: center; font-family: Arial; width: 350px; margin: auto;">
        <h1 style="font-size: 50px; margin: 0;">{d['Número de Análisis']}</h1>
        <hr style="border: 2px solid black;">
        <p style="font-size: 18px;"><b>{d.get('Descripción de Producto', 'INSUMO')}</b></p>
        <p>Lote: {d['Lote']} | Vto: {d['Vto']}</p>
        <p>Origen: {d.get('Origen','')} | Cant: {d['Cantidad']} {d.get('UDM','')}</p>
        <div style="background: red; color: white; font-size: 35px; font-weight: bold; padding: 15px; border: 2px solid black; margin-top: 10px;">CUARENTENA</div>
        <p style="font-size: 12px; margin-top: 10px;">Bultos: {d['Cantidad Bultos']} | Recep: {d.get('recepcion_num','')}</p>
        <button onclick="window.print()" style="margin-top: 15px; padding: 15px; width: 100%; background: green; color: white; font-weight: bold; cursor: pointer;">🖨️ IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=550)
