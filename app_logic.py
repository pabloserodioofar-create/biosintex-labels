import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import requests
import io

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        # Extract ID from URL for fallback methods
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}"
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _get_ws(self, base, env):
        return base if env == "Producción" else f"{base}_Test"

    def _read_fallback(self, worksheet):
        """Metodo de emergencia usando exportacion CSV directa de Google"""
        url = f"{self.spreadsheet_url}/gviz/tq?tqx=out:csv&sheet={worksheet.replace(' ', '%20')}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return pd.read_csv(io.StringIO(response.text))
        except:
            pass
        return pd.DataFrame()

    def get_excel_data(self):
        res = {"skus": [], "providers": [], "error": None}
        try:
            # Intentar SKU
            df_s = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=0)
            if df_s.empty: df_s = self._read_fallback("SKU")
            if not df_s.empty: res['skus'] = df_s.to_dict('records')

            # Intentar Proveedores
            df_p = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=0)
            if df_p.empty: df_p = self._read_fallback("Proveedores")
            if not df_p.empty: res['providers'] = df_p.to_dict('records')
            
        except Exception as e:
            res['error'] = str(e)
        return res

    def get_state(self, env="Producción"):
        ws = self._get_ws("State", env)
        try:
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            if df.empty: df = self._read_fallback(ws)
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
        ws = self._get_ws("Datos a completar", env)
        try:
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            if df.empty: df = self._read_fallback(ws)
            return df
        except: return pd.DataFrame()

    def save_entry(self, data, env="Producción"):
        try:
            ws = self._get_ws("Datos a completar", env)
            df = self.get_history(env)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return True, "OK"
        except Exception as e: return False, str(e)
