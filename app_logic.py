import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import requests
import io

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}"
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _direct_read(self, sheet_name):
        """Lectura directa via CSV export (muy robusta)"""
        # Limpiamos el nombre de la hoja para la URL
        clean_name = sheet_name.replace(' ', '%20')
        url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}/export?format=csv&sheet={clean_name}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                return df.dropna(axis=1, how='all').dropna(axis=0, how='all')
        except: pass
        return pd.DataFrame()

    def get_excel_data(self):
        res = {"skus": [], "providers": [], "error": None}
        
        # 1. Intentamos SKU
        df_s = self._direct_read("SKU")
        if df_s.empty: df_s = self._direct_read("skus")
        if not df_s.empty:
            res['skus'] = df_s.to_dict('records')
        
        # 2. Intentamos Proveedores (con variaciones por si acaso)
        tab_names = ["Proveedores", "PROVEEDORES", "Proveedor", "PROVEEDOR"]
        df_p = pd.DataFrame()
        for tab in tab_names:
            df_p = self._direct_read(tab)
            if not df_p.empty: break
            
        if not df_p.empty:
            res['providers'] = df_p.to_dict('records')
        else:
            res['error'] = "No se encontro la pestaña de Proveedores. Revisa el nombre en el Excel."
            
        return res

    def get_state(self, env="Producción"):
        ws = "State" if env == "Producción" else "State_Test"
        df = self._direct_read(ws)
        if df.empty:
            try: df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            except: pass
        
        if not df.empty:
            d = df.iloc[0].to_dict()
            return {"last_number": int(d.get("last_number", 0)), "last_reception": int(d.get("last_reception", 0)), "year": int(d.get("year", 26))}
        return {"last_number": 0, "last_reception": 0, "year": 26}

    def save_state(self, state, env="Producción"):
        ws = "State" if env == "Producción" else "State_Test"
        try:
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=pd.DataFrame([state]))
        except: pass

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
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        df = self._direct_read(ws)
        if df.empty:
            try: df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            except: pass
        return df

    def save_entry(self, data, env="Producción"):
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        try:
            df = self.get_history(env)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return True, "OK"
        except Exception as e: return False, str(e)
