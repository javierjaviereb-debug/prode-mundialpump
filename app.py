import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# Conexión con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. LEER DATOS
try:
    partidos_df = conn.read(worksheet="Partidos")
    predicciones_df = conn.read(worksheet="Predicciones")
except Exception:
    st.error("Error al conectar con la base de datos. Verificá los permisos de la Google Sheet.")
    st.stop()

# Sistema de pestañas
tab1, tab2 = st.tabs(["📝 Cargar Pronósticos", "📊 Tabla de Posiciones"])

# --- PESTAÑA 1: CARGAR PRONÓSTICOS ---
with tab1:
    st.header("Dejá tus predicciones")
    
    usuario = st.text_input("Ingresá tu nombre/usuario de la empresa:").strip().lower()
    
    if usuario:
        st.subheader("Próximos Partidos")
        nuevas_predicciones = []
        
        # Filtrar solo partidos que no tienen resultado cargado (aún no se jugaron)
        partidos_activos = partidos_df[partidos_df['Resultado1'].isna()]
        
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
                    
                    nuevas_predicciones.append({
                        "Usuario": usuario,
                        "Partido_ID": row['ID'],
                        "Pred_1": goles1,
                        "Pred_2": goles2,
                        "Puntos": 0
                    })
                    st.markdown("---")
                
                enviado = st.form_submit_button("Guardar Pronósticos")
                
                if enviado:
                    # Convertir a DataFrame y concatenar con lo existente
                    nuevos_datos_df = pd.DataFrame(nuevas_predicciones)
                    
                    # Eliminar predicciones previas del mismo usuario para estos partidos (evita duplicados)
                    if not predicciones_df.empty:
                        predicciones_df = predicciones_df[
                            ~((predicciones_df['Usuario'] == usuario) & 
                              (predicciones_df['Partido_ID'].isin(partidos_activos['ID'])))
                        ]
                    
                    df_final = pd.concat([predicciones_df, nuevos_datos_df], ignore_index=True)
                    
                    # Guardar en Google Sheets
                    conn.update(worksheet="Predicciones", data=df_final)
                    st.success("¡Pronósticos guardados con éxito! ¡Buena suerte!")

# --- PESTAÑA 2: POSICIONES ---
with tab2:
    st.header("🏆 Ranking de la Oficina")
    
    if predicciones_df.empty:
        st.info("Aún no hay predicciones cargadas.")
    else:
        # Calcular puntos (Agrupando por usuario)
        # Nota: El cálculo real de puntos se suele correr con un script secundario 
        # comparando 'Predicciones' con 'Partidos' (Ej: 3 pts resultado exacto, 1 pt ganador).
        
        tabla_posiciones = predicciones_df.groupby("Usuario")["Puntos"].sum().reset_index()
        tabla_posiciones = tabla_posiciones.sort_values(by="Puntos", ascending=False)
        
        # Formato visual
        tabla_posiciones.index = range(1, len(tabla_posiciones) + 1)
        st.table(tabla_posiciones)
