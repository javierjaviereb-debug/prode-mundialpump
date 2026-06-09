import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽", layout="wide")
st.title("⚽ Prode Mundialista - Pump Control")

# --- 1. BASE DE DATOS LOCAL (SQLITE) ---
DB_NAME = "prode_internal.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def inicializar_base_datos():
    conn = get_connection()
    cursor = conn.cursor()
    # Tabla de Partidos (estado: 0=Abierto, 1=Bloqueado/Cerrado)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidos (
        id TEXT PRIMARY KEY,
        equipo1 TEXT,
        equipo2 TEXT,
        resultado1 INTEGER,
        resultado2 INTEGER,
        estado INTEGER DEFAULT 0
    )
    """)
    # Tabla de Predicciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predicciones (
        usuario TEXT,
        partido_id TEXT,
        pred_1 INTEGER,
        pred_2 INTEGER,
        PRIMARY KEY (usuario, partido_id)
    )
    """)
    conn.commit()
    conn.close()

inicializar_base_datos()

# --- CARGAR DATOS EN TIEMPO REAL ---
conn = get_connection()
partidos_df = pd.read_sql_query("SELECT * FROM partidos", conn)
predicciones_df = pd.read_sql_query("SELECT * FROM predicciones", conn)
conn.close()

# --- PANEL DE ADMINISTRADOR EN LA BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Control (Admin)")
    modo_admin = st.checkbox("Activar modo Administrador")
    if modo_admin:
        password = st.text_input("Contraseña de Admin", type="password")
        if password == "pump2026":
            st.success("¡Acceso Admin concedido!")
            
            # SECCIÓN A: VER USUARIOS DE ALTA
            st.markdown("---")
            st.subheader("👥 Usuarios Registrados")
            if not predicciones_df.empty:
                usuarios_alta = sorted(predicciones_df["usuario"].unique())
                st.write(f"Total: **{len(usuarios_alta)}** usuarios activos")
                st.caption(", ".join(usuarios_alta))
            else:
                st.info("Aún no hay usuarios dados de alta.")
            
            # SECCIÓN B: AGREGAR PARTIDOS AL FIXTURE
            st.markdown("---")
            st.subheader("➕ Agregar Partido al Fixture")
            with st.form("form_add_partido"):
                new_id = st.text_input("ID único (Ej: 1, 2, 3...):")
                col_eq1, col_eq2 = st.columns(2)
                with col_eq1: new_eq1 = st.text_input("Equipo A:")
                with col_eq2: new_eq2 = st.text_input("Equipo B:")
                if st.form_submit_button("Añadir Partido"):
                    if new_id and new_eq1 and new_eq2:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO partidos (id, equipo1, equipo2, estado) VALUES (?, ?, ?, 0)", (new_id.strip(), new_eq1.strip(), new_eq2.strip()))
                            conn.commit()
                            conn.close()
                            st.success(f"Partido {new_id} añadido.")
                            st.rerun()
                        except: 
                            st.error("El ID ya existe.")
                    else: 
                        st.warning("Completá todos los campos.")
        elif password != "":
            st.error("Contraseña incorrecta")

# --- 2. MOTOR AUTOMÁTICO DE PUNTOS ---
if not predicciones_df.empty and not partidos_df.empty:
    prode_merge = pd.merge(predicciones_df, partidos_df, left_on="partido_id", right_on="id", how="left")
    
    def calcular_puntos(row):
        if pd.isna(row['resultado1']) or row['resultado1'] is None: 
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

# --- 3. INTERFAZ GRÁFICA PRINCIPAL ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Mi Juego / Cargar Pronósticos", 
    "🏆 Tabla de Posiciones", 
    "🔍 Ver Pronósticos de Otros", 
    "👑 Panel de Gestión Masiva (Admin)"
])

# TAB 1: EL USUARIO CARGA, VERIFICA Y MODIFICA
with tab1:
    st.header("📝 Tus Pronósticos de la Fecha")
    usuario = st.text_input("Ingresá tu nombre/usuario de la empresa para empezar:").strip().lower()
    
    if usuario:
        partidos_votables = partidos_df[partidos_df['estado'] == 0]
        
        if partidos_votables.empty:
            st.info("No hay partidos abiertos para pronosticar en este momento. ¡Esperá a que se habilite la próxima fecha!")
        else:
            st.subheader("⚽ Partidos disponibles para jugar o corregir")
            st.write("💡 *Abajo podés ver lo que cargaste previamente. Si querés corregir algo antes de que empiece el partido, cambialo y dale a 'Guardar Cambios'.*")
            
            with st.form("form_prode_usuario"):
                inputs = []
                for idx, row in partidos_votables.iterrows():
                    voto_previo = predicciones_df[(predicciones_df['usuario'] == usuario) & (predicciones_df['partido_id'] == row['id'])]
                    
                    val_def1 = int(voto_previo.iloc[0]['pred_1']) if not voto_previo.empty else 0
                    val_def2 = int(voto_previo.iloc[0]['pred_2']) if not voto_previo.empty else 0
                    
                    col_info, col_inputs = st.columns([2, 2])
                    with col_info:
                        if not voto_previo.empty:
                            st.markdown(f"**{row['equipo1']} vs. {row['equipo2']}** <br> <span style='color:green;'>✔️ Ya cargado previamente: {val_def1} - {val_def2}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"**{row['equipo1']} vs. {row['equipo2']}** <br> <span style='color:orange;'>⏳ Pendiente de carga</span>", unsafe_allow_html=True)
                    
                    with col_inputs:
                        sub_c1, sub_c2 = st.columns(2)
                        with sub_c1: g1 = st.number_input(f"Goles {row['equipo1']}", min_value=0, max_value=15, step=1, value=val_def1, key=f"u1_{row['id']}")
                        with sub_c2: g2 = st.number_input(f"Goles {row['equipo2']}", min_value=0, max_value=15, step=1, value=val_def2, key=f"u2_{row['id']}")
                    
                    inputs.append((row['id'], g1, g2))
                    st.markdown("---")
                    
                if st.form_submit_button("💾 Guardar / Modificar mis Pronósticos"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    for p_id, g1, g2 in inputs:
                        cursor.execute("INSERT OR REPLACE INTO predicciones (usuario, partido_id, pred_1, pred_2) VALUES (?, ?, ?, ?)", (usuario, str(p_id), int(g1), int(g2)))
                    conn.commit()
                    conn.close()
                    st.success("¡Tus jugadas se procesaron con éxito!")
                    st.rerun()

# TAB 2: RANKING EN VIVO
with tab2:
    st.header("🏆 Ranking de la Oficina en Vivo")
    if tabla_posiciones.empty: 
        st.info("Aún no hay predicciones cargadas.")
    else:
