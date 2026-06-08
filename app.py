import streamlit as st
import gspread
import pandas as pd

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. CONEXIÓN NATIVA DE GSPREAD MEDIANTE VARIABLES TOML
try:
    # Mapeamos los campos nativos desde los Secrets individuales de Streamlit
    credentials_dict = {
        "type": st.secrets["gspread_credentials"]["type"],
        "project_id": st.secrets["gspread_credentials"]["project_id"],
        "private_key_id": st.secrets["gspread_credentials"]["private_key_id"],
        "private_key": st.secrets["gspread_credentials"]["private_key"],
        "client_email": st.secrets["gspread_credentials"]["client_email"],
        "client_id": st.secrets["gspread_credentials"]["client_id"],
        "auth_uri": st.secrets["gspread_credentials"]["auth_uri"],
        "token_uri": st.secrets["gspread_credentials"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gspread_credentials"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gspread_credentials"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gspread_credentials"]["universe_domain"]
    }
    
    url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # El robot se conecta usando el diccionario limpio armado en memoria
    gc = gspread.service_account_from_dict(credentials_dict)
    sh = gc.open_by_url(url_sheet)
    
    worksheet_partidos = sh.worksheet("Partidos")
    worksheet_predicciones = sh.worksheet("Predicciones")
    
    # Cargar datos de las pestañas
    partidos_df = pd.DataFrame(worksheet_partidos.get_all_records())
    pred_data = worksheet_predicciones.get_all_records()
    
    if pred_data:
        predicciones_df = pd.DataFrame(pred_data)
    else:
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2", "Puntos"])

    partidos_df.columns = partidos_df.columns.str.strip()
    predicciones_df.columns = predicciones_df.columns.str.strip()

except Exception as e:
    st.error("🚨 Error de conexión con Google Sheets:")
    st.code(str(e))
    st.stop()

# --- 2. MOTOR AUTOMÁTICO DE PUNTOS ---
if not predicciones_df.empty and not partidos_df.empty:
    partidos_df['ID'] = partidos_df['ID'].astype(str).str.strip()
    predicciones_df['Partido_ID'] = predicciones_df['Partido_ID'].astype(str).str.strip()
    
    prode_merge = pd.merge(predicciones_df, partidos_df, left_on="Partido_ID", right_on="ID", how="left")
    
    def calcular_puntos(row):
        if pd.isna(row['Resultado1']) or pd.isna(row['Resultado2']) or str(row['Resultado1']).strip() == "" or str(row['Resultado2']).strip() == "": 
            return 0
        try:
            p1, p2 = int(row['Pred_1']), int(row['Pred_2'])
            r1, r2 = int(row['Resultado1']), int(row['Resultado2'])
            if p1 == r1 and p2 == r2: return 3
            if (p1 == p2) and (r1 == r2): return 1
            if (p1 > p2) and (r1 > r2): return 1
            if (p1 < p2) and (r1 < r2): return 1
            return 0
        except: 
            return 0

    prode_merge['Puntos_Calculados'] = prode_merge.apply(calcular_puntos, axis=1)
    tabla_posiciones = prode_merge.groupby("Usuario")["Puntos_Calculados"].sum().reset_index()
    tabla_posiciones.columns = ["Usuario", "Puntos Totales"]
    tabla_posiciones = tabla_posiciones.sort_values(by="Puntos Totales", ascending=False)
    tabla_posiciones.index = range(1, len(tabla_posiciones) + 1)
else:
    tabla_posiciones = pd.DataFrame(columns=["Usuario", "Puntos Totales"])

# --- 3. INTERFAZ GRÁFICA ---
tab1, tab2 = st.tabs(["📝 Cargar Pronósticos", "🏆 Tabla de Posiciones"])

with tab1:
    st.header("Dejá tus predicciones")
    usuario = st.text_input("Ingresá tu nombre/usuario de la empresa:").strip().lower()
    
    if usuario:
        st.subheader("Próximos Partidos")
        partidos_activos = partidos_df[partidos_df['Resultado1'].isna() | (partidos_df['Resultado1'].astype(str).str.strip() == "")]
        
        if partidos_activos.empty:
            st.info("No hay partidos activos para pronosticar en este momento. ¡Volvé para la próxima fecha!")
        else:
            ya_voto = False
            if not predicciones_df.empty:
                partidos_activos_ids = partidos_activos['ID'].astype(str).tolist()
                votos_usuario = predicciones_df[(predicciones_df['Usuario'] == usuario) & (predicciones_df['Partido_ID'].astype(str).isin(partidos_activos_ids))]
                if not votos_usuario.empty: 
                    ya_voto = True
            
            if ya_voto:
                st.warning("⚠️ Ya registraste tus pronósticos para los partidos disponibles. ¡Esperá a que el admin habilite la siguiente fecha!")
            else:
                with st.form("form_prode"):
                    inputs = []
                    for idx, row in partidos_activos.iterrows():
                        st.write(f"⚽ **{row['Equipo1']} vs. {row['Equipo2']}**")
                        col1, col2 = st.columns(2)
                        with col1: 
                            goles1 = st.number_input(f"Goles {row['Equipo1']}", min_value=0, max_value=15, step=1, key=f"e1_{row['ID']}")
                        with col2: 
                            goles2 = st.number_input(f"Goles {row['Equipo2']}", min_value=0, max_value=15, step=1, key=f"e2_{row['ID']}")
                        inputs.append((row['ID'], goles1, goles2))
                        st.markdown("---")
                        
                    enviado = st.form_submit_button("Guardar Pronósticos en la Base de Datos")
                    if enviado:
                        try:
                            for p_id, g1, g2 in inputs:
                                worksheet_predicciones.append_row([usuario, str(p_id), int(g1), int(g2), 0])
                            st.success("¡Perfecto! Tus jugadas se guardaron solas en la base de datos. ¡Buena suerte!")
                            st.rerun()
                        except Exception as error_guardado: 
                            st.error(f"Error al guardar los datos: {error_guardado}")

with tab2:
    st.header("🏆 Ranking de la Oficina en Vivo")
    if tabla_posiciones.empty: 
        st.info("Aún no hay predicciones cargadas en el sistema.")
    else:
        st.write("Sistema de puntos: **3 pts** resultado exacto | **1 pt** acertar ganador o empate | **0 pts** si errás.")
        st.table(tabla_posiciones)
