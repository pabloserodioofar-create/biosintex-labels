import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
import time

class AnalysisManager:
    def __init__(self, spreadsheet_url, script_url=None):
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.script_url = script_url
        self.cached_xl = None
        self.last_sync = None
        
    def _fetch_all(self):
        """Descarga el archivo completo en formato XLSX con cache-buster"""
        url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}/export?format=xlsx&t={int(time.time())}"
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
        
        # 1. SKU (Búsqueda flexible por nombre)
        sku_tab = next((s for s in self.cached_xl.sheet_names if "SKU" in s.upper()), None)
        if sku_tab:
            df_s = self.cached_xl.parse(sku_tab)
            res['skus'] = df_s.dropna(how='all', subset=df_s.columns[:2]).to_dict('records')
        
        # 2. PROVEEDORES (Búsqueda flexible: cualquier pestaña que contenga 'PROV')
        prov_tab = next((s for s in self.cached_xl.sheet_names if "PROV" in s.upper()), None)
        
        if prov_tab:
            df_p = self.cached_xl.parse(prov_tab)
            # Limpiar nombres de columnas (quitar espacios fantasmas)
            df_p.columns = [str(c).strip() for c in df_p.columns]
            
            # Validación: que no sea la de SKU por accidente
            if "Articulo" not in df_p.columns:
                # Quitamos filas vacías y convertimos a dict
                res['providers'] = df_p.dropna(how='all', subset=[df_p.columns[0]]).to_dict('records')
            else:
                # Si entramos aquí, es que 'PROV' detectó la de SKU o algo raro
                res['error'] = f"⚠️ Error: La pestaña '{prov_tab}' parece contener productos, no proveedores."
        
        if not res['providers'] and not res['error']:
            tabs = ", ".join(self.cached_xl.sheet_names)
            res['error'] = f"⚠️ No se encontró la pestaña 'Proveedores'. Pestañas encontradas: {tabs}"
            
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

    def save_entry_remote(self, data, env="Producción"):
        if not self.script_url or "/exec" not in self.script_url:
            return False, "⚠️ Configuración incompleta: Pega la URL de Apps Script en app.py"
        
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        try:
            # Mandamos la fila al servidor. El servidor generará el número de análisis.
            # Dejamos espacio para el número de análisis en el índice 3
            row_data = [
                str(data.get('Fecha', '')), 
                str(data.get('SKU', '')), 
                str(data.get('Descripción de Producto', '')),
                "GENERANDO...", 
                str(data.get('Lote', '')), 
                str(data.get('Origen', '')),
                str(data.get('Cantidad', '')), 
                str(data.get('UDM', '')), 
                str(data.get('Cantidad Bultos', '')),
                str(data.get('Vto', '')),
                str(data.get('Proveedor', '')), 
                str(data.get('Número de Remito', '')), 
                str(data.get('Presentacion', '')),
                str(data.get('Planta', '')), # 14va Columna: Planta
                str(data.get('OC', '')), # 15va Columna: OC
                str(data.get('realizado_por', '')), # 16va Columna: Realizado
                str(data.get('controlado_por', '')), # 17va Columna: Controlado
                str(data.get('recepcion_num', '')) # 18va Columna: Recepción
            ]
            
            payload = {
                "action": "save_entry", 
                "sheet": ws, 
                "row": row_data,
                "env": env
            }
            
            resp = requests.post(self.script_url, json=payload, timeout=20)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == "OK":
                    self.cached_xl = None # Limpiar caché para forzar descarga de nuevos datos
                    return True, result
                return False, f"Server Error: {result.get('status')}"
            return False, f"Error de conexión {resp.status_code}"
        except Exception as e:
            return False, str(e)

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
            df = self.cached_xl.parse(ws)
            if not df.empty:
                # Filtrar solo la fila de ejemplo/instrucciones si existe (usualmente contiene estas palabras clave)
                # Eliminamos 'carga' y 'manual' del patrón ya que son palabras comunes en datos reales
                patron_instrucciones = "toma|asignado|ejemplo|ingresa|automatico|pestaña"
                mask = df.astype(str).apply(lambda x: x.str.contains(patron_instrucciones, case=False, na=False)).any(axis=1)
                # Solo aplicar la máscara si la fila está entre las primeras 3 (típico de filas de cabecera/ejemplo)
                df = df[~(mask & (df.index < 3))]
                df = df.dropna(how='all')
            return df
        return pd.DataFrame()

    def update_history_remote(self, df, env="Producción"):
        """Envía el historial completo editado al servidor para actualizar la hoja"""
        if not self.script_url or "/exec" not in self.script_url:
            return False, "⚠️ Configuración incompleta: Pega la URL de Apps Script en app.py"
        
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        try:
            # Convertimos el DataFrame a una lista de listas (matriz) para el Apps Script
            # Incluimos los encabezados para que el script pueda mapear o sobrescribir
            data_to_send = [df.columns.tolist()] + df.values.tolist()
            
            # Limpieza de datos: convertir todo a string o tipos básicos para JSON
            clean_data = []
            for row in data_to_send:
                clean_row = []
                for val in row:
                    if pd.isna(val): clean_row.append("")
                    elif isinstance(val, (datetime, pd.Timestamp)): clean_row.append(val.strftime("%d/%m/%Y"))
                    else: clean_row.append(str(val))
                clean_data.append(clean_row)

            payload = {
                "action": "update_history", 
                "sheet": ws, 
                "rows": clean_data
            }
            
            resp = requests.post(self.script_url, json=payload, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("status") == "OK":
                    self.cached_xl = None # Forzar recarga
                    return True, "OK"
                return False, f"Servidor: {result.get('status')}"
            return False, f"Error {resp.status_code}"
        except Exception as e:
            return False, str(e)
