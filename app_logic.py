import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _get_ws(self, base, env):
        return base if env == "Producción" else f"{base}_Test"

    def get_state(self, env="Producción"):
        try:
            ws = self._get_ws("State", env)
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            if not df.empty:
                return df.iloc[0].to_dict()
        except: pass
        return {"last_number": 0, "last_reception": 0, "year": 26}

    def save_state(self, state, env="Producción"):
        try:
            ws = self._get_ws("State", env)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=pd.DataFrame([state]))
        except: pass

    def generate_next_number(self, env="Producción"):
        s = self.get_state(env)
        y = datetime.now().year % 100
        if int(s.get("year", 26)) != y: s["year"] = y; s["last_number"] = 1
        else: s["last_number"] = int(s.get("last_number", 0)) + 1
        self.save_state(s, env)
        return f"{int(s['last_number']):04d}/{s['year']}"

    def generate_next_reception(self, env="Producción"):
        s = self.get_state(env)
        s["last_reception"] = int(s.get("last_reception", 0)) + 1
        self.save_state(s, env)
        return str(s["last_reception"])

    def get_excel_data(self, env=None):
        # Ignoramos env aqui para asegurar compatibilidad de argumentos
        res = {}
        try:
            res['skus'] = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=60).to_dict('records')
            res['providers'] = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=60).to_dict('records')
        except: pass
        return res

    def get_history(self, env="Producción"):
        try:
            ws = self._get_ws("Datos a completar", env)
            return self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
        except: return pd.DataFrame()

    def save_entry(self, data, env="Producción"):
        try:
            ws = self._get_ws("Datos a completar", env)
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return True, "OK"
        except Exception as e: return False, str(e)
