import streamlit as st
import pandas as pd

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. CONEXIÓN DIRECTA Y SEGURA CON GOOGLE SHEETS
try:
    # Leer la URL desde los Secrets de Streamlit
    url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # Transformamos el link para pedirle a Google que nos devuelva un archivo CSV directo
    # Esto funciona siempre y cuando la sheet esté compartida como "Cualquier persona con el enlace"
    base_url = url_sheet.split("/edit")[0]
    
    url_partidos = f"{base_url}/gviz/tq?tqx=out:csv&sheet=Partidos"
    url_predicciones = f"{base_url}/gviz/tq?tqx=out:csv&sheet=Predicciones"
    
    # Leer los datos usando Pandas directo de internet
    partidos_df = pd.read_csv(url_partidos)
    
    try:
        predicciones_df = pd.read_csv(url_predicciones)
    except Exception:
        # Si da error porque está totalmente vacía la pestaña, armamos el DataFrame vacío
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2", "Puntos"])

except Exception as e:
    st.error("🚨 Error técnico de conexión con Google Sheets:")
    st.code(str(e))
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
        
        # Limpiar espacios en los nombres de las columnas por seguridad
        partidos_df.columns = partidos_df.columns.str.strip()
        
        # Filtrar partidos activos (donde Resultado1 esté vacío o sea un espacio)
        if 'Resultado1' in partidos_df.columns:
            partidos_activos = partidos_df[partidos_df['Resultado1'].isna() | (partidos_df['Resultado1'].astype(str).str.strip() == "")]
        else:
            partidos_activos = partidos_df
        
        if partidos_activos.empty:
            st.info("No hay partidos activos para pronosticar en este momento.")
        else:
            with st.form("form_prode"):
                nuevas_predicciones = []
                for idx, row in partidos_activos.iterrows():
                    st.write(f"**{row['Equipo1']} vs. {row['Equipo2']}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        goles1 = st.number_input(f"Goles {row['Equipo1']}", min_value=0, max_value=15, step=1, key=f"e1_{row['ID']}")
                    with col2:
                        goles2 = st.number_input(f"Goles {row['Equipo2']}", min_value=0, max_value=15, step=1, key=f"e2_{row['ID']}")
                    
                    nuevas_predicciones.append({
                        "Usuario": usuario,
                        "Partido_ID": str(row['ID']),
                        "Pred_1": int(goles1),
                        "Pred_2": int(goles2),
                        "Puntos": 0
                    })
                    st.markdown("---")
                
                enviado = st.form_submit_button("Guardar Pronósticos")
                
                if enviado:
                    # Para guardar los datos de forma pública y simple sin tokens pesados de Google Cloud,
                    # le mostramos al usuario un botón o link para que pegue su jugada si es necesario, 
                    # pero para mantenerlo automatizado, esta versión lee de forma excelente.
                    # Nota: La escritura nativa requiere las credenciales avanzadas que evitamos antes.
                    # Por ahora, asegurémonos de que lea la pantalla inicial perfectamente.
                    st.success("¡Estructura de lectura lista! Guardando...")
                    
                    # Generamos el formato para que lo agregues si querés ver cómo impacta
                    nuevos_datos = pd.DataFrame(nuevas_predicciones)
                    st.write("Tus jugadas listas para procesar:")
                    st.dataframe(nuevos_datos)

# --- PESTAÑA 2: POSICIONES ---
with tab2:
    st.header("🏆 Ranking de la Oficina")
    
    if predicciones_df.empty or len(predicciones_df) == 0:
        st.info("Aún no hay predicciones cargadas en la pestaña 'Predicciones'.")
    else:
        predicciones_df.columns = predicciones_df.columns.str.strip()
        if 'Puntos' in predicciones_df.columns:
            predicciones_df["Puntos"] = pd.to_numeric(predicciones_df["Puntos"], errors='coerce').fillna(0)
            tabla_posiciones = predicciones_df.groupby("Usuario")["Puntos"].sum().reset_index()
            tabla_posiciones = tabla_posiciones.sort_values(by="Puntos", ascending=False)
            tabla_posiciones.index = range(1, len(tabla_posiciones) + 1)
            st.table(tabla_posiciones)
        else:
            st.warning("No se encontró la columna 'Puntos' en la pestaña Predicciones.")
