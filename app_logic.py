import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.conn = st.connection("gsheets", type=GSheetsConnection)
        # We don't need a local state file anymore
        self.init_state()

    def init_state(self):
        # We try to read state, logic is better handled in generate methods
        pass

    def get_state(self):
        try:
            # Read from a sheet named 'State'
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="State", ttl=0)
            if not df.empty:
                return df.iloc[0].to_dict()
        except:
            pass
        # Default state if sheet not found or empty
        return {"last_number": 0, "last_reception": 0, "year": datetime.now().year % 100}

    def save_state(self, state):
        try:
            df = pd.DataFrame([state])
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet="State", data=df)
        except Exception as e:
            st.error(f"Error guardando estado en GSheets: {e}")

    def generate_next_number(self):
        state = self.get_state()
        current_year = datetime.now().year % 100
        
        last_year = int(state.get("year", 0))
        last_num = int(state.get("last_number", 0))

        if last_year != current_year:
            state["year"] = current_year
            state["last_number"] = 1
        else:
            state["last_number"] = last_num + 1
            
        self.save_state(state)
        formatted_num = f"{int(state['last_number']):04d}/{state['year']}"
        return formatted_num

    def generate_next_reception(self):
        state = self.get_state()
        state["last_reception"] = int(state.get("last_reception", 0)) + 1
        self.save_state(state)
        return str(state["last_reception"])

    def get_excel_data(self):
        try:
            # Read from Google Sheets tabs
            sku_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="SKU", ttl=300)
            prov_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Proveedores", ttl=300)
            
            skus = sku_df.to_dict('records')
            providers = prov_df.to_dict('records')
            
            presentations = ["CAJAS", "BOLSA BLANCA", "BOLSA KRAFT", "TAMBOR", "BIDON", "OTROS"]
            try:
                df_history = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet="Datos a completar", ttl=60)
                if 'Presentacion' in df_history.columns:
                    first_val = str(df_history['Presentacion'].iloc[0])
                    if "que se desplegue esto" in first_val.lower():
                        extra_options = first_val.replace("que se desplegue esto", "").split('\n')
                        for opt in extra_options:
                            opt = opt.strip()
                            if opt and opt not in presentations:
                                presentations.append(opt)
                    
                    history_values = df_history['Presentacion'].dropna().unique().tolist()
                    for val in history_values:
                        val = str(val).strip()
                        if val and "que se desplegue esto" not in val.lower() and val not in presentations:
                            presentations.append(val)
            except:
                pass
            
            presentations = sorted(list(set([p.strip().upper() for p in presentations if p and p.strip()])))
            
            return {"skus": skus, "providers": providers, "presentations": presentations}
        except Exception as e:
            return {"error": str(e)}

    def save_entry(self, data):
        try:
            ws_name = "Datos a completar"
            existing_df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws_name, ttl=0)
            new_row_df = pd.DataFrame([data])
            updated_df = pd.concat([existing_df, new_row_df], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws_name, data=updated_df)
            return (True, "Success")
        except Exception as e:
            return (False, f"Error al guardar en GSheets: {str(e)}")

    def update_entry(self, analysis_num, data):
        try:
            ws_name = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws_name, ttl=0)
            
            col_name = 'Número de Análisis' if 'Número de Análisis' in df.columns else 'Nº de Análisis'
            idx = df[df[col_name].astype(str) == str(analysis_num)].index
            
            if len(idx) == 0:
                return (False, f"No se encontró el análisis {analysis_num}")
            
            for key, val in data.items():
                if key in df.columns and key != col_name:
                    df.at[idx[0], key] = val
            
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws_name, data=df)
            return (True, "Datos actualizados correctamente")
        except Exception as e:
            return (False, f"Error al actualizar GSheets: {str(e)}")

    def reset_system(self):
        try:
            new_state = {"last_number": 0, "last_reception": 0, "year": datetime.now().year % 100}
            self.save_state(new_state)
            
            ws_name = "Datos a completar"
            df = self.conn.read(spreadsheet=self.spreadsheet_url, worksheet=ws_name, ttl=0)
            empty_df = pd.DataFrame(columns=df.columns)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws_name, data=empty_df)
            return True, "Sistema reseteado a 0."
        except Exception as e:
            return False, str(e)
