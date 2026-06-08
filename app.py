import streamlit as st
import gspread
import pandas as pd
import json

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. AUTENTICACIÓN SEGURA CON SERVICE ACCOUNT (MÉTODO COMPACTO)
try:
    # Leemos todo el contenido del JSON directo desde un único Secret como texto
    credentials_json = st.secrets["gspread_credentials_json"]
    url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Transformamos el texto en un diccionario real de Python
    credentials_dict = json.loads(credentials_json)
    
    # El robot se conecta usando el bloque completo
    gc = gspread.service_account_from_dict(credentials_dict)
    sh = gc.open_by_url(url_sheet)
    
    worksheet_partidos = sh.worksheet("Partidos")
    worksheet_predicciones = sh.worksheet("Predicciones")
    
    # Leer datos
    partidos_df = pd.DataFrame(worksheet_partidos.get_all_records())
    
    pred_data = worksheet_predicciones.get_all_records()
    if pred_data:
        predicciones_df = pd.DataFrame(pred_data)
    else:
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2", "Puntos"])

    partidos_df.columns = partidos_df.columns.str.strip()
    predicciones_df.columns = predicciones_df.columns.str.strip()

except Exception as e:
    st.error("🚨 Error de configuración en las credenciales seguras:")
    st.code(str(e))
    st.stop()
