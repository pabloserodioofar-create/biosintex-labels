import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import requests
import io

class AnalysisManager:
    def __init__(self, spreadsheet_url):
        # ID verificado de tu documento
        self.doc_id = "1IhDCR-BkAl5mk9C20eCCzZ50dgYK5tw40Wt1owIIylQ"
        self.spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{self.doc_id}"
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _fetch_sheet(self, sheet_name):
        """Intenta leer una hoja por nombre usando el motor de exportacion de Google"""
        # Variantes de URL para mayor compatibilidad
        urls = [
            f"https://docs.google.com/spreadsheets/d/{self.doc_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}",
            f"https://docs.google.com/spreadsheets/d/{self.doc_id}/export?format=csv&sheet={sheet_name.replace(' ', '%20')}"
        ]
        
        last_err = ""
        for url in urls:
            try:
                response = requests.get(url, timeout=7)
                if response.status_code == 200:
                    df = pd.read_csv(io.StringIO(response.text))
                    if not df.empty:
                        return df.dropna(axis=1, how='all').dropna(axis=0, how='all'), None
                else:
                    last_err = f"Google devolvió error {response.status_code}"
            except Exception as e:
                last_err = str(e)
        
        return pd.DataFrame(), last_err

    def get_excel_data(self):
        res = {"skus": [], "providers": [], "errors": []}
        
        # 1. Cargar SKU
        df_sku, err_sku = self._fetch_sheet("SKU")
        if not df_sku.empty:
            res['skus'] = df_sku.to_dict('records')
        else:
            # Reintento por si se llama distinto
            df_sku2, _ = self._fetch_sheet("Articulos")
            if not df_sku2.empty: res['skus'] = df_sku2.to_dict('records')
            else: res['errors'].append(f"SKU: {err_sku}")

        # 2. Cargar Proveedores
        df_p, err_p = self._fetch_sheet("Proveedores")
        if not df_p.empty and "Articulo" not in df_p.columns:
            res['providers'] = df_p.to_dict('records')
        else:
            # Reintento con variantes
            for v in ["PROVEEDORES", "Proveedor", "PROVEEDOR"]:
                df_v, _ = self._fetch_sheet(v)
                if not df_v.empty and "Articulo" not in df_v.columns:
                    res['providers'] = df_v.to_dict('records')
                    break
            if not res['providers']:
                res['errors'].append(f"Proveedores: {err_p}")
            
        return res

    def get_state(self, env="Producción"):
        ws = "State" if env == "Producción" else "State_Test"
        df, _ = self._fetch_sheet(ws)
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

    def get_history(self, env="Producción"):
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        df, _ = self._fetch_sheet(ws)
        return df

    def save_entry(self, data, env="Producción"):
        ws = "Datos a completar" if env == "Producción" else "Datos a completar_Test"
        try:
            df = self.get_history(env)
            updated = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            self.conn.update(spreadsheet=self.spreadsheet_url, worksheet=ws, data=updated)
            return True, "OK"
        except Exception as e: return False, str(e)

    def generate_next_number(self, env="Producción"):
        s = self.get_state(env)
        y = datetime.now().year % 100
        val = int(s.get("last_number", 0)) + 1
        s["last_number"] = val; s["year"] = y
        self.save_state(s, env)
        return f"{val:04d}/{y}"

    def generate_next_reception(self, env="Producción"):
        s = self.get_state(env)
        val = int(s.get("last_reception", 0)) + 1
        s["last_reception"] = val
        self.save_state(s, env)
        return str(val)
