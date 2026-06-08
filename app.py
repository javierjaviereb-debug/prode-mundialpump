import streamlit as st
import pandas as pd

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. CONEXIÓN DIRECTA CON GOOGLE SHEETS
try:
    url_sheet = st.secrets["connections"]["gsheets"]["spreadsheet"]
    base_url = url_sheet.split("/edit")[0]
    
    url_partidos = f"{base_url}/gviz/tq?tqx=out:csv&sheet=Partidos"
    url_predicciones = f"{base_url}/gviz/tq?tqx=out:csv&sheet=Predicciones"
    
    # Leer planillas
    partidos_df = pd.read_csv(url_partidos)
    
    try:
        predicciones_df = pd.read_csv(url_predicciones)
    except Exception:
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2"])

    # Limpiar espacios en nombres de columnas
    partidos_df.columns = partidos_df.columns.str.strip()
    predicciones_df.columns = predicciones_df.columns.str.strip()

except Exception as e:
    st.error("🚨 Error técnico de conexión con Google Sheets:")
    st.code(str(e))
    st.stop()

# --- MOTOR AUTOMÁTICO DE PUNTOS ---
# Vinculamos las predicciones con los resultados reales para calcular los puntos en vivo
if not predicciones_df.empty and not partidos_df.empty:
    # Asegurar que los IDs sean tratados como texto para evitar errores de cruce
    partidos_df['ID'] = partidos_df['ID'].astype(str).str.strip()
    predicciones_df['Partido_ID'] = predicciones_df['Partido_ID'].astype(str).str.strip()
    
    # Juntamos la tabla de predicciones con la de partidos reales
    prode_merge = pd.merge(predicciones_df, partidos_df, left_on="Partido_ID", right_on="ID", how="left")
    
    def calcular_puntos(row):
        # Si el partido no tiene resultado real cargado, da 0 puntos provisionales
        if pd.isna(row['Resultado1']) or pd.isna(row['Resultado2']) or str(row['Resultado1']).strip() == "" or str(row['Resultado2']).strip() == "":
            return 0
        
        try:
            p1, p2 = int(row['Pred_1']), int(row['Pred_2'])
            r1, r2 = int(row['Resultado1']), int(row['Resultado2'])
            
            # 1. Resultado Exacto (3 Puntos)
            if p1 == r1 and p2 == r2:
                return 3
            
            # 2. Acertar Ganador o Empate pero no los goles exactos (1 Punto)
            # Caso de empate pronosticado y empate real
            if (p1 == p2) and (r1 == r2):
                return 1
            # Caso gana equipo 1 pronosticado y gana equipo 1 real
            if (p1 > p2) and (r1 > r2):
                return 1
            # Caso gana equipo 2 pronosticado y gana equipo 2 real
            if (p1 < p2) and (r1 < r2):
                return 1
                
            # 3. No acertó nada (0 Puntos)
            return 0
        except Exception:
            return 0

    # Aplicamos la fórmula matemática fila por fila
    prode_merge['Puntos_Calculados'] = prode_merge.apply(calcular_puntos, axis=1)
    
    # Armamos la tabla de posiciones sumando los puntos calculados
    tabla_posiciones = prode_merge.groupby("Usuario")["Puntos_Calculados"].sum().reset_index()
    tabla_posiciones.columns = ["Usuario", "Puntos Totales"]
    tabla_posiciones = tabla_posiciones.sort_values(by="Puntos Totales", ascending=False)
    tabla_posiciones.index = range(1, len(tabla_posiciones) + 1)
else:
    tabla_posiciones = pd.DataFrame(columns=["Usuario", "Puntos Totales"])


# --- INTERFAZ GRÁFICA DE USUARIO ---
tab1, tab2 = st.tabs(["📝 Cargar Pronósticos", "🏆 Tabla de Posiciones"])

# PESTAÑA 1: CARGAR PRONÓSTICOS
with tab1:
    st.header("Dejá tus predicciones")
    usuario = st.text_input("Ingresá tu nombre/usuario de la empresa (Ej: jburgos):").strip().lower()
    
    if usuario:
        st.subheader("Próximos Partidos Disponibles")
        
        # Filtrar partidos que NO tienen resultado real cargado todavía
        partidos_activos = partidos_df[partidos_df['Resultado1'].isna() | (partidos_df['Resultado1'].astype(str).str.strip() == "")]
        
        if partidos_activos.empty:
            st.info("No hay partidos activos para pronosticar en este momento. ¡Volvé para la próxima etapa!")
        else:
            with st.form("form_prode"):
                nuevas_predicciones = []
                for idx, row in partidos_activos.iterrows():
                    st.write(f"⚽ **{row['Equipo1']} vs. {row['Equipo2']}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        goles1 = st.number_input(f"Goles {row['Equipo1']}", min_value=0, max_value=15, step=1, key=f"e1_{row['ID']}")
                    with col2:
                        goles2 = st.number_input(f"Goles {row['Equipo2']}", min_value=0, max_value=15, step=1, key=f"e2_{row['ID']}")
                    
                    nuevas_predicciones.append({
                        "Usuario": usuario,
                        "Partido_ID": row['ID'],
                        "Pred_1": int(goles1),
                        "Pred_2": int(goles2)
                    })
                    st.markdown("---")
                
                enviado = st.form_submit_button("Confirmar Pronósticos")
                
                if enviado:
                    st.success("👍 ¡Pronósticos armados con éxito!")
                    st.markdown("### 📋 Copiá el texto de abajo y pegalo en la pestaña 'Predicciones' de la Google Sheet o envíaselo al organizador:")
                    
                    # Generamos el formato de texto listo para copiar y pegar fácilmente en las celdas del Excel si fuera necesario centralizarlo
                    df_txt = pd.DataFrame(nuevas_predicciones)
                    st.dataframe(df_txt)
                    st.info("Nota para el grupo: El administrador registrará las líneas en la base central para actualizar el ranking.")

# PESTAÑA 2: POSICIONES AUTOMÁTICAS
with tab2:
    st.header("🏆 Ranking de la Oficina en Vivo")
    
    if tabla_posiciones.empty:
        st.info("Aún no hay predicciones computadas o no se han cargado resultados reales.")
    else:
        st.write("Los puntos se calculan así: **3 pts** resultado exacto, **1 pt** acertar ganador/empate, **0 pts** si errás.")
        st.table(tabla_posiciones)
