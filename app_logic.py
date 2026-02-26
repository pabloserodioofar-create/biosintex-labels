import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

class AnalysisManager:
    def __init__(self, spreadsheet_url, script_url=None):
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.script_url = script_url
        self.cached_xl = None
        self.last_sync = None
        
    def _fetch_all(self):
        """Descarga el archivo completo en formato XLSX (más confiable para varias pestañas)"""
        url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}/export?format=xlsx"
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                self.cached_xl = pd.ExcelFile(io.BytesIO(response.content))
                self.last_sync = datetime.now()
                return True
        except Exception as e:
            st.error(f"Error de conexión: {str(e)}")
        return False

    def get_excel_data(self):
        res = {"skus": [], "providers": [], "error": None}
        
        if not self._fetch_all():
            res['error'] = "⚠️ No se pudo sincronizar con Google Sheets. Revisa tu conexión."
            return res
        
        # 1. SKU
        if "SKU" in self.cached_xl.sheet_names:
            df_s = self.cached_xl.parse("SKU")
            res['skus'] = df_s.dropna(how='all').to_dict('records')
        
        # 2. PROVEEDORES
        found_p = False
        for tab in ["Proveedores", "PROVEEDORES", "Proveedor"]:
            if tab in self.cached_xl.sheet_names:
                df_p = self.cached_xl.parse(tab)
                # Validación de seguridad: que no sea la hoja de SKUs por error
                if "Articulo" not in df_p.columns:
                    res['providers'] = df_p.dropna(how='all').to_dict('records')
                    found_p = True
                    break
        
        if not found_p:
            res['error'] = "⚠️ No se encontró la pestaña 'Proveedores' en el Excel."
            
        return res

    def get_state(self, env="Producción"):
        # Usar caché si existe, sino intentar descargar
        if not self.cached_xl:
            self._fetch_all()
            
        if not self.cached_xl:
            return {"last_number": 0, "last_reception": 0, "year": 26}

        ws = "State" if env == "Producción" else "State_Test"
        if ws in self.cached_xl.sheet_names:
            df = self.cached_xl.parse(ws)
            if not df.empty:
                d = df.iloc[0].to_dict()
                return {
                    "last_number": int(d.get("last_number", 0)), 
                    "last_reception": int(d.get("last_reception", 0)), 
                    "year": int(d.get("year", 26))
                }
        return {"last_number": 0, "last_reception": 0, "year": 26}

    def save_state(self, state, env="Producción"):
        if not self.script_url or "/exec" not in self.script_url: return
        ws = "State" if env == "Producción" else "State_Test"
        try:
            payload = {
                "action": "update_state", 
                "sheet": ws, 
                "last_number": int(state['last_number']), 
                "last_reception": int(state['last_reception']), 
                "year": int(state.get('year', 26))
            }
            requests.post(self.script_url, json=payload, timeout=10)
        except: pass

    def save_entry(self, data, env="Producción"):
        if not self.script_url or "/exec" not in self.script_url:
            return False, "⚠️ Configuración incompleta: Pega la URL de Apps Script en app.py"
        
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        try:
            # Orden EXACTO según el encabezado del Excel (13 columnas):
            # Fecha, SKU, Descripción de Producto, Número de Análisis, Lote, Origen, Cantidad, UDM, Cantidad Bultos, Vto, Proveedor, Número de Remito, Presentacion
            row_data = [
                str(data.get('Fecha', '')), 
                str(data.get('SKU', '')), 
                str(data.get('Descripción de Producto', '')),
                str(data.get('Número de Análisis', '')), 
                str(data.get('Lote', '')), 
                str(data.get('Origen', '')),
                str(data.get('Cantidad', '')), 
                str(data.get('UDM', '')), 
                str(data.get('Cantidad Bultos', '')),
                str(data.get('Vto', '')),
                str(data.get('Proveedor', '')), 
                str(data.get('Número de Remito', '')), 
                str(data.get('Presentacion', ''))
            ]
            payload = {"action": "append", "sheet": ws, "row": row_data}
            resp = requests.post(self.script_url, json=payload, timeout=15)
            if resp.status_code == 200: 
                # Forzamos resincronización en la siguiente carga para ver cambios
                self.cached_xl = None 
                return True, "OK"
            return False, f"Server Error {resp.status_code} (Revisa la URL de Apps Script)"
        except Exception as e: return False, f"Error: {str(e)}"

    def generate_next_number(self, env="Producción"):
        s = self.get_state(env)
        y = datetime.now().year % 100
        val = int(s.get("last_number", 0)) + 1
        s["last_number"] = val
        s["year"] = y
        self.save_state(s, env)
        return f"{val:04d}/{y}"

    def generate_next_reception(self, env="Producción"):
        s = self.get_state(env)
        val = int(s.get("last_reception", 0)) + 1
        s["last_reception"] = val
        self.save_state(s, env)
        return str(val)

    def get_history(self, env="Producción"):
        if not self.cached_xl:
            self._fetch_all()
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        if self.cached_xl and ws in self.cached_xl.sheet_names:
            return self.cached_xl.parse(ws)
        return pd.DataFrame()
