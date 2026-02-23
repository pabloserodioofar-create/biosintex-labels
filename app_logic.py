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
                return df.iloc[0].to_dict()
        except Exception as e:
            pass
        return {"last_number": 0, "last_reception": 0, "year": datetime.now().year % 100}

    def save_state(self, state):
        try:
            df = pd.DataFrame([state])
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet="State", data=df)
        except Exception as e:
            st.error(f"Error al guardar estado. ¿Existe la pestaña 'State'?")

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
        missing_tabs = []
        
        # Cargar SKU
        try:
            sku_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=60)
            results['skus'] = sku_df.to_dict('records')
        except Exception as e: 
            missing_tabs.append(f"SKU (Error: {str(e)[:50]}...)")
            
        # Cargar Proveedores
        try:
            prov_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=60)
            results['providers'] = prov_df.to_dict('records')
        except Exception as e: 
            missing_tabs.append(f"Proveedores (Error: {str(e)[:50]}...)")
            
        # Cargar Historial para presentaciones
        try:
            df_hist = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Datos a completar", ttl=60)
            if 'Presentacion' in df_hist.columns:
                vals = df_hist['Presentacion'].dropna().unique().tolist()
                results['presentations'] = sorted(list(set([str(v).upper().strip() for v in vals if v])))
        except: pass # No es crítico
            
        if missing_tabs:
            results['error'] = f"Faltan estas pestañas en Google Sheets: {', '.join(missing_tabs)}"
        
        return results

    def save_entry(self, data):
        try:
            ws = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return (True, "OK")
        except:
            return (False, "Error al guardar. Revisa la pestaña 'Datos a completar'.")

    def reset_system(self):
        try:
            self.save_state({"last_number":0, "last_reception":0, "year": datetime.now().year % 100})
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Datos a completar", ttl=0)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet="Datos a completar", data=pd.DataFrame(columns=df.columns))
            return True, "Sistema reseteado"
        except: return False, "Error al resetear"
