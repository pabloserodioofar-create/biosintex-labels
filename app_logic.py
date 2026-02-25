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

    def _get_ws_data(self, sheet_name):
        """Lectura ultra-robusta via CSV con verificacion de contenido"""
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
        
        # 1. Cargar SKU
        df_sku = self._get_ws_data("SKU")
        if not df_sku.empty and ("Articulo" in df_sku.columns or "ID" in df_sku.columns):
            res['skus'] = df_sku.to_dict('records')
        
        # 2. Cargar Proveedores (Probando variaciones y validando contenido)
        # Esto evita que Google nos devuelva el SKU por error
        for tab in ["Proveedores", "PROVEEDORES", "Proveedor", "PROVEEDOR", "Proveedores "]:
            df_p = self._get_ws_data(tab)
            if not df_p.empty:
                # VALIDACION: Si tiene 'Articulo', NO es la pestaña de proveedores
                if "Articulo" in df_p.columns:
                    continue 
                # VALIDACION: Debe tener algo que parezca un proveedor o un ID
                res['providers'] = df_p.to_dict('records')
                break
            
        return res

    def get_state(self, env="Producción"):
        ws = "State" if env == "Producción" else "State_Test"
        df = self._get_ws_data(ws)
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
        df = self._get_ws_data(ws)
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
