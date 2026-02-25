import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

class AnalysisManager:
    def __init__(self, spreadsheet_url, script_url=None):
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.script_url = script_url # URL de Apps Script para ESCRIBIR
        
    def _read_via_csv(self, sheet_name):
        """Lectura ultra-robusta via CSV (Sigue funcionando para leer)"""
        url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}/export?format=csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                return df.dropna(axis=1, how='all').dropna(axis=0, how='all')
        except: pass
        return pd.DataFrame()

    def get_excel_data(self):
        res = {"skus": [], "providers": [], "error": None}
        df_s = self._read_via_csv("SKU")
        if not df_s.empty: res['skus'] = df_s.to_dict('records')
        
        df_p = self._read_via_csv("Proveedores")
        if not df_p.empty: res['providers'] = df_p.to_dict('records')
        else: res['error'] = "No se cargó lista de proveedores."
        return res

    def get_state(self, env="Producción"):
        ws = "State" if env == "Producción" else "State_Test"
        df = self._read_via_csv(ws)
        if not df.empty:
            d = df.iloc[0].to_dict()
            return {"last_number": int(d.get("last_number", 0)), "last_reception": int(d.get("last_reception", 0)), "year": int(d.get("year", 26))}
        return {"last_number": 0, "last_reception": 0, "year": 26}

    def save_state(self, state, env="Producción"):
        if not self.script_url: return
        ws = "State" if env == "Producción" else "State_Test"
        try:
            # Usamos el puente Apps Script para guardar
            payload = {
                "action": "update_state",
                "sheet": ws,
                "last_number": int(state['last_number']),
                "last_reception": int(state['last_reception']),
                "year": int(state.get('year', 26))
            }
            requests.post(self.script_url, json=payload)
        except: pass

    def save_entry(self, data, env="Producción"):
        if not self.script_url:
            return False, "Error: No se ha configurado la URL de escritura (Apps Script)."
        
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        try:
            # Convertimos el diccionario en una lista ordenada segun columnas del Excel
            # (Asumimos el orden estandar que veniamos usando)
            row_data = [
                data.get('Fecha'), data.get('SKU'), data.get('Descripción de Producto'),
                data.get('Número de Análisis'), data.get('Lote'), data.get('Vto'),
                data.get('Cantidad'), data.get('UDM'), data.get('Cantidad Bultos'),
                data.get('Proveedor'), data.get('Número de Remito'), data.get('recepcion_num'),
                data.get('realizado_por'), data.get('controlado_por')
            ]
            
            payload = {
                "action": "append",
                "sheet": ws,
                "row": row_data
            }
            resp = requests.post(self.script_url, json=payload)
            if resp.status_code == 200:
                return True, "OK"
            return False, f"Error del servidor: {resp.status_code}"
        except Exception as e:
            return False, str(e)

    def generate_next_number(self, env="Producción"):
        s = self.get_state(env)
        y = datetime.now().year % 100
        val = int(s.get("last_number", 0)) + 1
        s["last_number"] = val; s["year"] = y
        self.save_state(s, env)
        return f"{val:04d}/{y}"

    def generate_next_reception(self, env="Producción"):
        s = self.get_state(env)
        val = int(s.get("last_reception", 0)) + 1
        s["last_reception"] = val
        self.save_state(s, env)
        return str(val)

    def get_history(self, env="Producción"):
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        return self._read_via_csv(ws)
