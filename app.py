import streamlit as st
import pandas as pd
import sqlite3
import os

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽", layout="wide")
st.title("⚽ Prode Mundialista de la Empresa")

# --- 1. CONEXIÓN Y CREACIÓN DE BASE DE DATOS LOCAL (SQLITE) ---
DB_NAME = "prode_internal.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def inicializar_base_datos():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Crear tabla de Partidos si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidos (
        id TEXT PRIMARY KEY,
        equipo1 TEXT,
        equipo2 TEXT,
        resultado1 INTEGER,
        resultado2 INTEGER
    )
    """)
    
    # Crear tabla de Predicciones si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predicciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        partido_id TEXT,
        pred_1 INTEGER,
        pred_2 INTEGER
    )
    """)
    
    # Insertar Fixture Inicial de ejemplo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM partidos")
    if cursor.fetchone()[0] == 0:
        fixture_inicial = [
            ("1", "Argentina", "Arabia Saudita", None, None),
            ("2", "México", "Polonia", None, None),
            ("3", "Francia", "Australia", None, None),
            ("4", "Dinamarca", "Túnez", None, None),
            ("5", "Brasil", "Serbia", None, None),
            ("6", "Portugal", "Ghana", None, None),
        ]
        cursor.executemany("INSERT INTO partidos VALUES (?, ?, ?, ?, ?)", fixture_inicial)
        conn.commit()
    conn.close()

# Inicializamos las tablas internas
inicializar_base_datos()

# --- CARGAR DATOS A DATAFRAMES ---
conn = get_connection()
partidos_df = pd.read_sql_query("SELECT * FROM partidos", conn)
predicciones_df = pd.read_sql_query("SELECT * FROM predicciones", conn)
conn.close()

# --- PANEL DE ADMINISTRADOR OCULTO (Para que cargues resultados reales) ---
with st.sidebar:
    st.header("⚙️ Panel de Control (Admin)")
    modo_admin = st.checkbox("Activar modo Administrador")
    if modo_admin:
        password = st.text_input("Contraseña de Admin", type="password")
        if password == "pump2026":  # Podés cambiar esta contraseña cuando quieras
            st.success("¡Acceso concedido!")
            st.subheader("Cargar Resultados Reales")
            
            partido_a_editar = st.selectbox("Seleccionar partido jugado:", partidos_df["id"] + " - " + partidos_df["equipo1"] + " vs " + partidos_df["equipo2"])
            p_id = partido_a_editar.split(" - ")[0]
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                r1 = st.number_input("Goles Equipo 1", min_value=0, max_value=15, step=1, key="admin_r1")
            with col_res2:
                r2 = st.number_input("Goles Equipo 2", min_value=0, max_value=15, step=1, key="admin_r2")
                
            if st.button("Actualizar Resultado Oficial"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE partidos SET resultado1 = ?, resultado2 = ? WHERE id = ?", (int(r1), int(r2), p_id))
                conn.commit()
                conn.close()
                st.success("Resultado actualizado en la base SQL. ¡Actualizando tablas!")
                st.rerun()
        elif password != "":
            st.error("Contraseña incorrecta")

# --- 2. MOTOR AUTOMÁTICO DE PUNTOS ---
if not predicciones_df.empty and not partidos_df.empty:
    prode_merge = pd.merge(predicciones_df, partidos_df, left_on="partid_id", right_on="id", how="left", suffixes=('_pred', '_real'))
    
    def calcular_puntos(row):
        if pd.isna(row['resultado1']) or pd.isna(row['resultado2']) or row['resultado1'] is None or row['resultado2'] is None: 
            return 0
        try:
            p1, p2 = int(row['pred_1']), int(row['pred_2'])
            r1, r2 = int(row['resultado1']), int(row['resultado2'])
            if p1 == r1 and p2 == r2: return 3
            if (p1 == p2) and (r1 == r2): return 1
            if (p1 > p2) and (r1 > r2): return 1
            if (p1 < p2) and (r1 < r2): return 1
            return 0
        except: 
            return 0

    prode_merge['Puntos_Calculados'] = prode_merge.apply(calcular_puntos, axis=1)
    tabla_posiciones = prode_merge.groupby("usuario")["Puntos_Calculados"].sum().reset_index()
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
        # Partidos activos son los que no tienen resultado cargado aún
        partidos_activos = partidos_df[partidos_df['resultado1'].isna() | (partidos_df['resultado1'].isnull())]
        
        if partidos_activos.empty:
            st.info("No hay partidos activos para pronosticar en este momento.")
        else:
            ya_voto = False
            if not predicciones_df.empty:
                votos_usuario = predicciones_df[(predicciones_df['usuario'] == usuario) & (predicciones_df['partido_id'].isin(partidos_activos['id'].tolist()))]
                if not votos_usuario.empty: 
                    ya_voto = True
            
            if ya_voto:
                st.warning("⚠️ Ya registraste tus pronósticos para esta fecha.")
            else:
                with st.form("form_prode"):
                    inputs = []
                    for idx, row in partidos_activos.iterrows():
                        st.write(f"⚽ **{row['equipo1']} vs. {row['equipo2']}**")
                        col1, col2 = st.columns(2)
                        with col1: 
                            goles1 = st.number_input(f"Goles {row['equipo1']}", min_value=0, max_value=15, step=1, key=f"e1_{row['id']}")
                        with col2: 
                            goles2 = st.number_input(f"Goles {row['equipo2']}", min_value=0, max_value=15, step=1, key=f"e2_{row['id']}")
                        inputs.append((row['id'], goles1, goles2))
                        st.markdown("---")
                        
                    enviado = st.form_submit_button("Guardar Pronósticos")
                    if enviado:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            for p_id, g1, g2 in inputs:
                                cursor.execute("INSERT INTO predicciones (usuario, partido_id, pred_1, pred_2) VALUES (?, ?, ?, ?)", (usuario, str(p_id), int(g1), int(g2)))
                            conn.commit()
                            conn.close()
                            st.success("¡Perfecto! Tus jugadas se guardaron con éxito en el sistema.")
                            st.rerun()
                        except Exception as error_guardado: 
                            st.error(f"Error al guardar en SQL: {error_guardado}")

with tab2:
    st.header("🏆 Ranking de la Oficina en Vivo")
    if tabla_posiciones.empty: 
        st.info("Aún no hay predicciones cargadas en el sistema.")
    else:
        st.write("Sistema de puntos: **3 pts** resultado exacto | **1 pt** acertar ganador o empate.")
        st.table(tabla_posiciones)
