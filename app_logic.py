import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}"
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _get_ws(self, base_name, env):
        # Si es modo Pruebas, buscamos la pestaña con sufijo _Test
        return base_name if env == "Producción" else f"{base_name}_Test"

    def get_state(self, env="Producción"):
        try:
            ws = self._get_ws("State", env)
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            if not df.empty:
                data = df.iloc[0].to_dict()
                return {
                    "last_number": int(data.get("last_number", 0)),
                    "last_reception": int(data.get("last_reception", 0)),
                    "year": int(data.get("year", 26))
                }
        except: pass
        return {"last_number": 0, "last_reception": 0, "year": 26}

    def save_state(self, state, env="Producción"):
        try:
            ws = self._get_ws("State", env)
            df = pd.DataFrame([state])
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=df)
        except: pass

    def generate_next_number(self, env="Producción"):
        s = self.get_state(env)
        y = datetime.now().year % 100
        if int(s["year"]) != y: s["year"] = y; s["last_number"] = 1
        else: s["last_number"] += 1
        self.save_state(s, env)
        return f"{s['last_number']:04d}/{s['year']}"

    def generate_next_reception(self, env="Producción"):
        s = self.get_state(env)
        s["last_reception"] += 1
        self.save_state(s, env)
        return str(s["last_reception"])

    def get_excel_data(self, env="Producción"):
        res = {}
        # Cargamos siempre SKU y Proveedores de la base real (suelen ser compartidos)
        # Pero si prefieres tener SKUs de prueba, puedes usar self._get_ws("SKU", env)
        try:
            df_s = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=60)
            res['skus'] = df_s.to_dict('records')
            df_p = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=60)
            res['providers'] = df_p.to_dict('records')
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
            upd = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=upd)
            return True, "OK"
        except Exception as e: return False, str(e)
