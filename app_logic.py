import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io
import requests

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        # ID unico de tu documento
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}"
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _read_public_csv(self, sheet_name):
        """Metodo alternativo: Lee el CSV publico directamente de Google si la conexion oficial falla"""
        url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return pd.read_csv(io.StringIO(response.text))
        except: pass
        return pd.DataFrame()

    def get_state(self):
        try:
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="State", ttl=0)
            if df.empty: df = self._read_public_csv("State")
            if not df.empty:
                data = df.iloc[0].to_dict()
                return {"last_number": int(data.get("last_number", 0)), "last_reception": int(data.get("last_reception", 0)), "year": int(data.get("year", 26))}
        except: pass
        return {"last_number": 0, "last_reception": 0, "year": 26}

    def save_state(self, state):
        try:
            df = pd.DataFrame([state])
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet="State", data=df)
        except: pass

    def generate_next_number(self):
        s = self.get_state()
        y = datetime.now().year % 100
        if int(s["year"]) != y: s["year"] = y; s["last_number"] = 1
        else: s["last_number"] += 1
        self.save_state(s)
        return f"{s['last_number']:04d}/{s['year']}"

    def generate_next_reception(self):
        s = self.get_state()
        s["last_reception"] += 1
        self.save_state(s)
        return str(s["last_reception"])

    def get_excel_data(self):
        res = {}
        # Leer SKU
        df_s = self._read_public_csv("SKU")
        if df_s.empty: 
            try: df_s = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=0)
            except: pass
        if not df_s.empty: res['skus'] = df_s.to_dict('records')

        # Leer Proveedores
        df_p = self._read_public_csv("Proveedores")
        if df_p.empty:
            try: df_p = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=0)
            except: pass
        if not df_p.empty: res['providers'] = df_p.to_dict('records')
        
        return res

    def save_entry(self, data):
        try:
            ws = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            upd = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=upd)
            return True, "OK"
        except Exception as e: return False, f"Error: {str(e)[:50]}"
