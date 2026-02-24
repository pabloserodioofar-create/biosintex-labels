import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# Link oficial
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Biosintex - Gestión de Insumos", layout="wide")

# --- SISTEMA DE LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["username"] == "biosintex" and st.session_state["password"] == "2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No guardar la contraseña
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center;'>🔒 Acceso Privado</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            with st.form("Login"):
                st.text_input("Usuario", key="username")
                st.text_input("Contraseña", type="password", key="password")
                st.form_submit_button("Entrar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.error("😕 Usuario o contraseña incorrectos")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- INICIALIZACION DESPUES DEL LOGIN ---
if 'env' not in st.session_state:
    st.session_state.env = "Producción"

if 'manager' not in st.session_state:
    st.session_state.manager = AnalysisManager(SHEET_URL)

def refresh_data():
    with st.spinner(f"Sincronizando {st.session_state.env}..."):
        # Pasamos el entorno al manager para que sepa que pestañas leer
        data = st.session_state.manager.get_excel_data(env=st.session_state.env)
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

# --- UI PRINCIPAL ---
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title(f"📦 Biosintex - {st.session_state.env}")
with header_col2:
    with st.popover("⚙️ Ajustes"):
        st.write("### Configuración")
        status = "🟢 Producción" if st.session_state.env == "Producción" else "🟡 Pruebas"
        st.info(f"Entorno actual: {status}")
        
        nuevo_env = st.radio("Cambiar Entorno:", ["Producción", "Pruebas"], 
                             index=0 if st.session_state.env == "Producción" else 1)
        
        if nuevo_env != st.session_state.env:
            st.session_state.env = nuevo_env
            refresh_data()
            st.rerun()

        if st.button("🔄 Forzar Sincronización"):
            refresh_data()
            st.rerun()
            
        st.divider()
        if st.button("🚪 Cerrar Sesión"):
            del st.session_state["password_correct"]
            st.rerun()

tab1, tab2 = st.tabs(["📝 Registro de Ingreso", "📊 Historial / Reimpresión"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Insumo")
        sku_code = st_searchbox(search_sku, label="Buscar SKU *", key="sku_input")
        sku_name = ""
        if sku_code:
            for s in st.session_state.skus:
                if str(s.get('ID', s.get('Articulo', ''))) == str(sku_code):
                    sku_name = s.get('Nombre', '')
                    st.info(f"Producto: {sku_name}")
                    break
        lote = st.text_input("Lote *", key="lote_input")
        vto = st.date_input("Vencimiento *", key="vto_input")
        udm = st.selectbox("UDM", ["KG", "UN", "L", "M"], key="udm_input")

    with col_b:
        st.subheader("Recepción")
        cant = st.number_input("Cantidad Total *", min_value=0.0, key="cant_input")
        bul = st.number_input("Bultos *", min_value=1, key="bul_input")
        prov = st_searchbox(search_prov, label="Proveedor *", key="prov_input")
        rem = st.text_input("Remito *", key="rem_input")
        
        state_v = st.session_state.manager.get_state(env=st.session_state.env)
        next_r = str(state_v.get("last_reception", 0) + 1)
        st.text_input("Recepción (Auto)", value=next_r, disabled=True)

    if st.button("🚀 GENERAR ETIQUETA", type="primary", use_container_width=True):
        if not sku_code or not lote or not prov:
            st.error("Campos obligatorios incompletos")
        else:
            an = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            entry = {
                'Fecha': datetime.now().strftime("%d/%m/%Y"),
                'SKU': sku_code,
                'Descripción de Producto': sku_name,
                'Número de Análisis': an,
                'Lote': lote,
                'Cantidad': cant,
                'UDM': udm,
                'Cantidad Bultos': bul,
                'Proveedor': prov,
                'Número de Remito': rem,
                'recepcion_num': rc,
                'Entorno': st.session_state.env
            }
            ok, msg = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.success(f"¡Generado! {an}")
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else: st.error(msg)

with tab2:
    st.subheader(f"Historial {st.session_state.env}")
    h_df = st.session_state.manager.get_history(env=st.session_state.env)
    if not h_df.empty:
        st.dataframe(h_df.iloc[::-1], use_container_width=True)
        sel_an = st.selectbox("Seleccione análisis para reimprimir:", h_df['Número de Análisis'].tolist())
        if st.button("🖨️ Ver para Reimpresión"):
            row = h_df[h_df['Número de Análisis'] == sel_an].iloc[0]
            st.session_state.current_data = row.to_dict()
            st.session_state.show_p = True
            st.rerun()
    else:
        st.info("No hay registros en este entorno.")

if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    if st.button("❌ Cerrar Vista Previa"):
        st.session_state.show_p = False
        st.rerun()
    
    html = f"""<div style="border:5px solid black; padding:20px; text-align:center; background:white; font-family:Arial; color:black;">
        <h1 style="font-size:50px; margin:0;">{d['Número de Análisis']}</h1>
        <hr>
        <p style="font-size:20px;"><b>{d['Descripción de Producto']}</b></p>
        <p>SKU: {d['SKU']} | Lote: {d['Lote']}</p>
        <div style="background:red; color:white; font-size:40px; font-weight:bold; padding:20px;">CUARENTENA</div>
        <p style='margin-top:10px;'>Entorno: {d.get('Entorno', 'PRUEBAS')}</p>
        <button onclick="window.print()" style="padding:15px 30px; background:green; color:white; font-weight:bold; cursor:pointer;">IMPRIMIR</button>
    </div>"""
    st.components.v1.html(html, height=550)
