import os
import json
import ee
import streamlit as st
from config import settings

def init_gee_session():
    """Inicializa la sesin de GEE buscando credenciales en Secrets (Nube) o Archivo (Local)"""
    # 1. Intentar con Streamlit Secrets (Nube)
    if "gee_credentials" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gee_credentials"])
            credentials = ee.ServiceAccountCredentials(creds_dict['client_email'], key_data=json.dumps(creds_dict))
            ee.Initialize(credentials)
            return True, "Earth Engine inicializado desde Secrets (Cloud)."
        except Exception as e:
            return False, f"Error con Secrets: {str(e)}"
            
    # 2. Intentar con archivo local
    creds_path = os.path.join(settings.CREDENTIALS_DIR, "gee_service_account.json")
    if os.path.exists(creds_path):
        try:
            with open(creds_path) as f:
                info = json.load(f)
            credentials = ee.ServiceAccountCredentials(info['client_email'], creds_path)
            ee.Initialize(credentials)
            return True, "Earth Engine inicializado desde archivo local."
        except Exception as e:
            return False, f"Error al inicializar GEE: {str(e)}"
            
    return False, "No se encontraron credenciales (Secrets o JSON)."

def save_gee_credentials(json_file):
    """Guarda el archivo JSON de credenciales en la carpeta credentials"""
    if not os.path.exists(settings.CREDENTIALS_DIR):
        os.makedirs(settings.CREDENTIALS_DIR)
        
    path = os.path.join(settings.CREDENTIALS_DIR, "gee_service_account.json")
    with open(path, "wb") as f:
        f.write(json_file.getbuffer())
    return path

def clean_scientific_name(name):
    """Normaliza nombres cientficos"""
    if not isinstance(name, str):
        return ""
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} {parts[1].lower()}"
    return name.capitalize()
