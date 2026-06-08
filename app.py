import streamlit as st
import gspread
import pandas as pd

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. CONEXIÓN DIRECTA CON GOOGLE SHEETS
try:
    # Leer la URL desde los Secrets de Streamlit
    url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Nos conectamos usando gspread con acceso público
    gc = gspread.public_api()
    sh = gc.open_by_url(url_sheet)
    
    # Abrir las pestañas
    worksheet_partidos = sh.worksheet("Partidos")
    worksheet_predicciones = sh.worksheet("Predicciones")
    
    # LEER PARTIDOS (Forma ultra segura)
    data_partidos = worksheet_partidos.get_all_values()
    if len(data_partidos) > 1:
        # Usar la primera fila como títulos
        partidos_df = pd.DataFrame(data_partidos[1:], columns=data_partidos[0])
    else:
        partidos_df = pd.DataFrame(columns=["ID", "Equipo1", "Equipo2", "Resultado1", "Resultado2"])
    
    # LEER PREDICCIONES (Forma ultra segura)
    data_pred = worksheet_predicciones.get_all_values()
    if len(data_pred) > 1:
        predicciones_df = pd.DataFrame(data_pred[1:], columns=data_pred[0])
    else:
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2", "Puntos"])

except Exception as e:
    st.error("🚨 Error técnico de conexión con Google Sheets:")
    st.code(str(e))  # <-- ESTO NOS VA A DECIR EL ERROR REAL EN PANTALLA
    st.info("Recordá que la Google Sheet debe estar compartida como 'Cualquier persona con el enlace' en rol de 'Editor'.")
    st.stop()

# Sistema de pestañas de la interfaz
tab1, tab2 = st.tabs(["📝 Cargar Pronósticos", "📊 Tabla de Posiciones"])

# --- PESTAÑA 1: CARGAR PRONÓSTICOS ---
with tab1:
    st.header("Dejá tus predicciones")
    
    usuario = st.text_input("Ingresá tu nombre/usuario de la empresa:").strip().lower()
    
    if usuario:
        st.subheader("Próximos Partidos")
        nuevas_predicciones = []
        
        # Limpiar espacios en los nombres de las columnas por seguridad
        partidos_df.columns = partidos_df.columns.str.strip()
        
        # Filtrar partidos activos (donde Resultado1 esté vacío)
        if 'Resultado1' in partidos_df.columns:
            partidos_activos = partidos_df[partidos_df['Resultado1'].astype(str).str.strip() == ""]
        else:
            partidos_activos = partidos_df
        
        if partidos_activos.empty:
            st.info("No hay partidos activos para pronosticar en este momento.")
        else:
            with st.form("form_prode"):
                for idx, row in partidos_activos.iterrows():
                    st.write(f"**{row['Equipo1']} vs. {row['Equipo2']}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        goles1 = st.number_input(f"Goles {row['Equipo1']}", min_value=0, max_value=15, step=1, key=f"e1_{row['ID']}")
                    with col2:
                        goles2 = st.number_input(f"Goles {row['Equipo2']}", min_value=0, max_value=15, step=1, key=f"e2_{row['ID']}")
                    
                    nuevas_predicciones.append([
                        usuario,
                        str(row['ID']),
                        str(int(goles1)),
                        str(int(goles2)),
                        "0"
                    ])
                    st.markdown("---")
                
                enviado = st.form_submit_button("Guardar Pronósticos")
                
                if enviado:
                    # Guardar las filas directo al final de la planilla de Google Sheets
                    for fila in nuevas_predicciones:
                        worksheet_predicciones.append_row(fila)
                    st.success("¡Pronósticos guardados con éxito! ¡Buena suerte!")
                    st.rerun()

# --- PESTAÑA 2: POSICIONES ---
with tab2:
    st.header("🏆 Ranking de la Oficina")
    
    if predicciones_df.empty:
        st.info("Aún no hay predicciones cargadas.")
    else:
        predicciones_df.columns = predicciones_df.columns.str.strip()
        predicciones_df["Puntos"] = pd.to_numeric(predicciones_df["Puntos"], errors='coerce').fillna(0)
        
        tabla_posiciones = predicciones_df.groupby("Usuario")["Puntos"].sum().reset_index()
        tabla_posiciones = tabla_posiciones.sort_values(by="Puntos", ascending=False)
        tabla_posiciones.index = range(1, len(tabla_posiciones) + 1)
        st.table(tabla_posiciones)
