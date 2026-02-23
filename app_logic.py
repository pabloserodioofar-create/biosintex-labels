import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def get_state(self):
        try:
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="State", ttl=0)
            if not df.empty:
                return df.dropna(subset=['last_number']).iloc[0].to_dict()
        except: pass
        return {"last_number": 0, "last_reception": 0, "year": datetime.now().year % 100}

    def save_state(self, state):
        try:
            df = pd.DataFrame([state])
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet="State", data=df)
        except: pass

    def generate_next_number(self):
        state = self.get_state()
        curr_year = datetime.now().year % 100
        if int(state.get("year", 0)) != curr_year:
            state["year"] = curr_year
            state["last_number"] = 1
        else:
            state["last_number"] = int(state.get("last_number", 0)) + 1
        self.save_state(state)
        return f"{int(state['last_number']):04d}/{state['year']}"

    def generate_next_reception(self):
        state = self.get_state()
        state["last_reception"] = int(state.get("last_reception", 0)) + 1
        self.save_state(state)
        return str(state["last_reception"])

    def get_excel_data(self):
        results = {}
        missing = []
        
        # Intentamos leer SKU de varias formas
        try:
            sku_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=0)
            if not sku_df.empty: results['skus'] = sku_df.to_dict('records')
            else: missing.append("SKU (está vacía)")
        except Exception as e: 
            missing.append(f"SKU (No se encontró o error: {str(e)[:20]})")
        
        try:
            prov_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=0)
            if not prov_df.empty: results['providers'] = prov_df.to_dict('records')
            else: missing.append("Proveedores (está vacía)")
        except Exception as e: 
            missing.append(f"Proveedores (No se encontró o error: {str(e)[:20]})")
            
        try:
            df_hist = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Datos a completar", ttl=0)
            if not df_hist.empty and 'Presentacion' in df_hist.columns:
                vals = df_hist['Presentacion'].dropna().unique().tolist()
                results['presentations'] = sorted(list(set([str(v).upper().strip() for v in vals if v])))
        except: pass
            
        if missing: results['error'] = f"Problema: {', '.join(missing)}"
        return results

    def save_entry(self, data):
        try:
            ws = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return (True, "OK")
        except:
            return (False, "Error al guardar. Verifica la pestaña 'Datos a completar'.")

    def reset_system(self):
        try:
            self.save_state({"last_number":0, "last_reception":0, "year": datetime.now().year % 100})
            ws = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            empty = pd.DataFrame(columns=df.columns)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=empty)
            return True, "OK"
        except: return False, "Error"
