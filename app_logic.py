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
                # Filtrar posibles filas vacias
                df = df.dropna(subset=['last_number'])
                if not df.empty:
                    return df.iloc[0].to_dict()
        except: pass
        return {"last_number": 0, "last_reception": 0, "year": datetime.now().year % 100}

    def save_state(self, state):
        try:
            df = pd.DataFrame([state])
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet="State", data=df)
        except Exception as e:
            st.error(f"Error en 'State': {str(e)[:100]}")

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
        try:
            sku_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=10)
            results['skus'] = sku_df.to_dict('records')
        except Exception as e: missing.append(f"SKU ({str(e)[:30]})")
        
        try:
            prov_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=10)
            results['providers'] = prov_df.to_dict('records')
        except Exception as e: missing.append(f"Proveedores ({str(e)[:30]})")
        
        try:
            df_hist = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Datos a completar", ttl=10)
            if 'Presentacion' in df_hist.columns:
                vals = df_hist['Presentacion'].dropna().unique().tolist()
                results['presentations'] = sorted(list(set([str(v).upper().strip() for v in vals if v])))
        except: pass
            
        if missing: results['error'] = f"Error en pestañas: {', '.join(missing)}"
        return results

    def save_entry(self, data):
        try:
            ws = "Datos a completar"
            # Importante: leer sin cache para no pisar datos
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return (True, "OK")
        except Exception as e:
            return (False, f"Error al guardar: {str(e)[:100]}")

    def reset_system(self):
        try:
            self.save_state({"last_number":0, "last_reception":0, "year": datetime.now().year % 100})
            ws = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws, ttl=0)
            empty = pd.DataFrame(columns=df.columns)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=empty)
            return True, "Reset ok"
        except: return False, "Error reset"
