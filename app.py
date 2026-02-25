import streamlit as st
import pandas as pd
from app_logic import AnalysisManager
from streamlit_searchbox import st_searchbox
from datetime import datetime

# Configuracion Base
SHEET_URL = "https://docs.google.com/spreadsheets/d/1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"

st.set_page_config(page_title="Biosintex - Gestión de Rótulos", layout="wide")

# --- LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Acceso Sistema Biosintex</h2>", unsafe_allow_html=True)
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
    with st.spinner("Sincronizando datos..."):
        data = st.session_state.manager.get_excel_data()
        st.session_state.skus = data.get('skus', [])
        st.session_state.providers = data.get('providers', [])
        if data.get('error'):
            st.error(f"Error de conexión: {data['error']}")
        elif not st.session_state.skus:
            st.warning("⚠️ No se cargaron SKUs. Verifica que la hoja sea pública y tenga datos.")

if not st.session_state.skus:
    refresh_data()

# --- SEARCH LOGIC ---
def search_sku(q):
    if not q or not st.session_state.skus: return []
    q_low = q.lower()
    res = []
    for s in st.session_state.skus:
        art = str(s.get('Articulo', s.get('ID', '')))
        nom = str(s.get('Nombre', ''))
        if q_low in art.lower() or q_low in nom.lower():
            res.append((f"{art} - {nom}", art))
    return res[:25]

def search_prov(q):
    if not q or not st.session_state.providers: return []
    q_low = q.lower()
    res = []
    for p in st.session_state.providers:
        pid = str(p.get('ID', ''))
        pnom = str(p.get('Proveedor', ''))
        if q_low in pid.lower() or q_low in pnom.lower():
            res.append(pnom)
    return list(set(res)) # Avoid duplicates

# --- MAIN UI ---
st.title(f"📦 Biosintex ({st.session_state.env})")

with st.sidebar:
    st.header("⚙️ Configuración")
    nuevo_env = st.radio("Entorno:", ["Producción", "Pruebas"], index=0 if st.session_state.env=="Producción" else 1)
    if nuevo_env != st.session_state.env:
        st.session_state.env = nuevo_env
        refresh_data()
        st.rerun()
    st.button("🔄 Sincronizar", on_click=refresh_data)
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        del st.session_state["password_correct"]
        st.rerun()

tab1, tab2 = st.tabs(["📝 Generar Nuevo Rótulo", "📊 Historial de Ingresos"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Datos del Insumo")
        sku_sel = st_searchbox(search_sku, label="Código o Nombre del Insumo *", key="sku_input")
        sku_name = ""
        if sku_sel:
            for s in st.session_state.skus:
                if str(s.get('Articulo', s.get('ID',''))) == str(sku_sel):
                    sku_name = s.get('Nombre', '')
                    st.info(f"✅ Seleccionado: {sku_name}")
                    break
        lote = st.text_input("Número de Lote *")
        vto = st.date_input("Fecha de Vencimiento *")
        pres_options = ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "FRASCO", "BALDE", "OTROS"]
        presentacion = st.selectbox("Presentación *", pres_options)
        origen = st.selectbox("Origen *", ["Nacional", "Importado"])

    with col2:
        st.subheader("Datos de Recepción")
        udm = st.selectbox("Unidad de Medida (UDM) *", ["KG", "UN", "L", "M"])
        step_val = 1.0 if udm == "UN" else 0.1
        cant = st.number_input("Cantidad Total Recibida *", min_value=0.0, step=step_val)
        bultos = st.number_input("Cantidad de Bultos *", min_value=1, step=1)
        prov_sel = st_searchbox(search_prov, label="Nombre o ID del Proveedor *", key="prov_input")
        remito = st.text_input("Número de Remito *")
        
        state_vals = st.session_state.manager.get_state(env=st.session_state.env)
        next_r = str(state_vals.get("last_reception", 0) + 1)
        st.text_input("Nº de Recepción (Auto)", value=next_r, disabled=True)
        
        staff = ["Walter Alarcon", "Gaston Fonteina", "Adrian Fernadez", "Ruben Guzman", "Maximiliano Duarte", "Hernan Miño", "Gustavo Alegre", "Sebastian Colmano", "Federico Scolazzo"]
        c_staff1, c_staff2 = st.columns(2)
        with c_staff1: realizado = st.selectbox("Realizado por *", ["Seleccione..."] + staff)
        with c_staff2: controlado = st.selectbox("Controlado por *", ["Seleccione..."] + staff)

    if st.button("🚀 GENERAR NÚMERO DE ANÁLISIS Y RÓTULO", type="primary", use_container_width=True):
        if not sku_sel or not lote or not prov_sel or realizado == "Seleccione..." or controlado == "Seleccione..." or cant <= 0:
            st.error("⚠️ Por favor complete todos los campos obligatorios.")
        else:
            an_num = st.session_state.manager.generate_next_number(env=st.session_state.env)
            rc_num = st.session_state.manager.generate_next_reception(env=st.session_state.env)
            
            entry = {
                'Fecha': datetime.now().strftime("%d/%m/%Y"),
                'SKU': sku_sel,
                'Descripción de Producto': sku_name,
                'Número de Análisis': an_num,
                'Lote': lote,
                'Vto': vto.strftime("%d/%m/%Y"),
                'Cantidad': cant,
                'UDM': udm,
                'Cantidad Bultos': bultos,
                'Proveedor': prov_sel,
                'Número de Remito': remito,
                'Presentacion': presentacion,
                'Origen': origen,
                'recepcion_num': rc_num,
                'realizado_por': realizado,
                'controlado_por': controlado,
                'Entorno': st.session_state.env
            }
            
            ok, msg = st.session_state.manager.save_entry(entry, env=st.session_state.env)
            if ok:
                st.success(f"✅ ¡Rótulo generado con éxito! Número de Análisis: {an_num}")
                st.session_state.current_data = entry
                st.session_state.show_p = True
                st.rerun()
            else:
                st.error(f"❌ Error al guardar: {msg}")

with tab2:
    st.subheader(f"Historial de Ingresos ({st.session_state.env})")
    h_df = st.session_state.manager.get_history(env=st.session_state.env)
    if not h_df.empty:
        # Filter instruction rows if any
        if 'SKU' in h_df.columns:
            h_df = h_df[h_df['SKU'].astype(str).str.len() > 1]
        
        st.dataframe(h_df.iloc[::-1], use_container_width=True)
        
        st.write("### Reimprimir Rótulo")
        sel_an = st.selectbox("Seleccione el Número de Análisis:", h_df['Número de Análisis'].unique().tolist() if 'Número de Análisis' in h_df.columns else [])
        if st.button("🖨️ Ver Vista Previa para Reimprimir"):
            fila = h_df[h_df['Número de Análisis'] == sel_an].iloc[0]
            st.session_state.current_data = fila.to_dict()
            st.session_state.show_p = True
            st.rerun()
    else:
        st.info("No hay registros en el historial.")

# --- DISPLAY LABEL ---
if st.session_state.get('show_p'):
    d = st.session_state.current_data
    st.divider()
    if st.button("❌ Cerrar Vista Previa"):
        st.session_state.show_p = False
        st.rerun()
    
    # Calculate items per bundle
    total_cant = float(d.get('Cantidad', 0))
    total_bultos = int(d.get('Cantidad Bultos', 1))
    cant_per_bulto = total_cant / total_bultos
    
    html = f"""
    <div style="background: #f0f2f6; padding: 20px; border-radius: 10px;">
        <div id="labels-to-print" style="background: white; width: 400px; margin: auto; padding: 20px; border: 4px solid black; font-family: Arial; color: black;">
            <h1 style="text-align: center; font-size: 45px; margin: 0;">{d['Número de Análisis']}</h1>
            <hr style="border: 2px solid black;">
            <p style="font-size: 20px; margin: 5px 0;"><b>{d.get('Descripción de Producto', 'INSUMO')}</b></p>
            <p style="margin: 5px 0;">SKU: {d['SKU']} | Origen: {d.get('Origen', 'Nacional')}</p>
            <p style="margin: 5px 0;">Lote: {d['Lote']} | Vto: {d['Vto']}</p>
            <p style="margin: 5px 0;">Remito: {d.get('Número de Remito', '')} | Recep: {d.get('recepcion_num', '')}</p>
            <div style="background: red; color: white; text-align: center; font-size: 40px; font-weight: bold; padding: 15px; margin-top: 10px; border: 2px solid black;">
                CUARENTENA
            </div>
            <p style="font-size: 14px; margin-top: 10px; text-align: center;">Cantidad por bulto: {cant_per_bulto:.2f} {d.get('UDM', 'KG')}</p>
            <p style="font-size: 12px; text-align: right; color: #555;">Realizado por: {d.get('realizado_por', '')}</p>
            <button onclick="window.print()" style="width: 100%; height: 50px; background: #28a745; color: white; font-weight: bold; border: none; border-radius: 5px; cursor: pointer; margin-top: 15px; font-size: 16px;">
                🖨️ IMPRIMIR RÓTULOS ({total_bultos} bultos)
            </button>
        </div>
    </div>
    """
    st.components.v1.html(html, height=600, scrolling=True)
