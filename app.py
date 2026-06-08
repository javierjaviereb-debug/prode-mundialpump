import streamlit as st
import gspread
import pandas as pd
import json

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. AUTENTICACIÓN SEGURA CON SERVICE ACCOUNT (MÉTODO COMPACTO)
try:
    # Leemos el contenido del JSON y la URL desde los Secrets de Streamlit
    credentials_json = st.secrets["gspread_credentials_json"]
    url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Transformamos el texto en un diccionario real de Python
    credentials_dict = json.loads(credentials_json)
    
    # El robot se conecta a Google Sheets
    gc = gspread.service_account_from_dict(credentials_dict)
    sh = gc.open_by_url(url_sheet)
    
    worksheet_partidos = sh.worksheet("Partidos")
    worksheet_predicciones = sh.worksheet("Predicciones")
    
    # Traemos los datos de las pestañas
    partidos_df = pd.DataFrame(worksheet_partidos.get_all_records())
    
    pred_data = worksheet_predicciones.get_all_records()
    if pred_data:
        predicciones_df = pd.DataFrame(pred_data)
    else:
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2", "Puntos"])

    # Limpiamos espacios ocultos en los nombres de las columnas por seguridad
    partidos_df.columns = partidos_df.columns.str.strip()
    predicciones_df.columns = predicciones_df.columns.str.strip()

except Exception as e:
    st.error("🚨 Error de configuración en las credenciales seguras:")
    st.code(str(e))
    st.stop()

# --- 2. MOTOR AUTOMÁTICO DE PUNTOS ---
if not predicciones_df.empty and not partidos_df.empty:
    # Aseguramos que los IDs sean tratados como texto para el cruce de datos
    partidos_df['ID'] = partidos_df['ID'].astype(str).str.strip()
    predicciones_df['Partido_ID'] = predicciones_df['Partido_ID'].astype(str).str.strip()
    
    # Cruzamos las predicciones de los usuarios con el fixture real
    prode_merge = pd.merge(predicciones_df, partidos_df, left_on="Partido_ID", right_on="ID", how="left")
    
    def calcular_puntos(row):
        # Si el partido no se jugó o no tiene resultado real cargado, da 0 puntos provisionales
        if pd.isna(row['Resultado1']) or pd.isna(row['Resultado2']) or str(row['Resultado1']).strip() == "" or str(row['Resultado2']).strip() == "":
            return 0
        try:
            p1, p2 = int(row['Pred_1']), int(row['Pred_2'])
            r1, r2 = int(row['Resultado1']), int(row['Resultado2'])
            
            # Caso 1: Resultado Exacto (3 Puntos)
            if p1 == r1 and p2 == r2: 
                return 3
            # Caso 2: Acertar Empate pero no los goles exactos (1 Punto)
            if (p1 == p2) and (r1 == r2): 
                return 1
            # Caso 3: Acertar Ganador Equipo 1 (1 Punto)
            if (p1 > p2) and (r1 > r2): 
                return 1
            # Caso 4: Acertar Ganador Equipo 2 (1 Punto)
            if (p1 < p2) and (r1 < r2): 
                return 1
                
            return 0
        except: 
            return 0

    # Aplicamos la fórmula matemática renglón por renglón
    prode_merge['Puntos_Calculados'] = prode_merge.apply(calcular_puntos, axis=1)
    
    # Agrupamos por empleado para armar el Ranking
    tabla_posiciones = prode_merge.groupby("Usuario")["Puntos_Calculados"].sum().reset_index()
    tabla_posiciones.columns = ["Usuario", "Puntos Totales"]
    tabla_posiciones = tabla_posiciones.sort_values(by="Puntos Totales", ascending=False)
    tabla_posiciones.index = range(1, len(tabla_posiciones) + 1)
else:
    tabla_posiciones
