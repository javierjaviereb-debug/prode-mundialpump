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
            
            # SECCIÓN B: CARGA MASIVA DE NUEVA ETAPA / FIXTURE
            st.markdown("---")
            st.subheader("⚡ Carga Masiva de Partidos")
            st.write("Pegá los partidos abajo respetando este formato:")
            st.code("ID, Equipo A, Equipo B\n(Ejemplo:\n10, Argentina, Uruguay\n11, Francia, Holanda)")
            
            data_masiva = st.text_area("Lista de partidos a agregar:", height=150, placeholder="10, Argentina, Uruguay\n11, Francia, Holanda")
            
            if st.button("🚀 Procesar e Inyectar Fixture Masivo"):
                if data_masiva.strip():
                    lineas = data_masiva.strip().split("\n")
                    partidos_a_insertar = []
                    errores = []
                    
                    for linea in lineas:
                        if not linea.strip():
                            continue
                        # Soportamos separación por coma (,) o por guion (-)
                        partes = linea.replace("-", ",").split(",")
                        if len(partes) == 3:
                            p_id = partes[0].strip()
                            eq1 = partes[1].strip()
                            eq2 = partes[2].strip()
                            partidos_a_insertar.append((p_id, eq1, eq2))
                        else:
                            errores.append(f"Línea mal formateada: '{linea}'")
                    
                    if errores:
                        for err in errores:
                            st.error(err)
                    elif partidos_a_insertar:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            # Insertamos masivamente ignorando si el ID ya existe para no romper la base
                            cursor.executemany("INSERT OR IGNORE INTO partidos (id, equipo1, equipo2, estado) VALUES (?, ?, ?, 0)", partidos_a_insertar)
                            conn.commit()
                            conn.close()
                            st.success(f"¡Se procesaron e inyectaron {len(partidos_a_insertar)} partidos con éxito al fixture!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar en la base de datos: {e}")
                else:
                    st.warning("El cuadro de texto está vacío.")
                    
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
            st.info("No hay partidos abiertos para pronosticar en este momento. ¡Esperá a que se habilite la próxima fecha o etapa!")
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
                    st.success("¡Tus jugadas se guardaron o actualizaron con éxito!")
                    st.rerun()

# TAB 2: RANKING EN VIVO
with tab2:
    st.header("🏆 Ranking de la Oficina en Vivo")
    if tabla_posiciones.empty: 
        st.info("Aún no hay predicciones cargadas.")
    else: 
        st.table(tabla_posiciones)

# TAB 3: CONSULTAR JUGADAS DE CUALQUIERA
with tab3:
    st.header("🔍 Consultar Pronósticos Registrados")
    if predicciones_df.empty: 
        st.info("No hay pronósticos registrados en el sistema.")
    else:
        todos_usuarios = sorted(predicciones_df["usuario"].unique())
        user_sel = st.selectbox("Seleccioná un compañero para ver su juego:", todos_usuarios)
        if user_sel:
            votos_user = predicciones_df[predicciones_df["usuario"] == user_sel]
            votos_merge = pd.merge(votos_user, partidos_df, left_on="partido_id", right_on="id")
            votos_merge["Resultado Real"] = votos_merge.apply(lambda r: f"{r['resultado1']} - {r['resultado2']}" if pd.notna(r['resultado1']) else "Pendiente ⏳", axis=1)
            votos_merge["Su Pronóstico"] = votos_merge["pred_1"].astype(str) + " - " + votos_merge["pred_2"].astype(str)
            tabla_ver = votos_merge[["equipo1", "equipo2", "Su Pronóstico", "Resultado Real"]]
            tabla_ver.columns = ["Equipo 1", "Equipo 2", "Su Pronóstico", "Resultado Oficial"]
            st.dataframe(tabla_ver, use_container_width=True)

# TAB 4: PANTALLA MASIVA DEL ADMINISTRADOR (CARGA DE RESULTADOS Y BLOQUEOS)
with tab4:
    st.header("👑 Panel de Gestión Masiva (Exclusivo Administrador)")
    if modo_admin and password == "pump2026":
        if partidos_df.empty:
            st.info("No hay partidos creados en el fixture todavía. Podés usar la sección de Carga Masiva en la barra lateral izquierda.")
        else:
            st.write("Cargá los resultados oficiales y gestioná los bloqueos de toda la fecha en una sola pantalla:")
            
            with st.form("form_gestion_masiva_admin"):
                admin_inputs = []
                
                header_c1, header_c2, header_c3, header_c4 = st.columns([1, 3, 2, 2])
                with header_c1: st.markdown("**ID**")
                with header_c2: st.markdown("**Partido**")
                with header_c3: st.markdown("**Resultado Oficial**")
                with header_c4: st.markdown("**Estado / Bloqueo**")
                st.markdown("---")
                
                for idx, row in partidos_df.iterrows():
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
                    
                    with c1: 
                        st.write(f"#{row['id']}")
                    with c2: 
                        st.markdown(f"**{row['equipo1']} vs. {row['equipo2']}**")
                    with c3:
                        sub_c1, sub_c2 = st.columns(2)
                        val_res1 = int(row['resultado1']) if pd.notna(row['resultado1']) else 0
                        val_res2 = int(row['resultado2']) if pd.notna(row['resultado2']) else 0
                        
                        ya_jugado = st.checkbox("Cargar", value=pd.notna(row['resultado1']), key=f"play_{row['id']}")
                        g_r1 = sub_c1.number_input("G1", min_value=0, max_value=15, step=1, value=val_res1, key=f"adm_r1_{row['id']}")
                        g_r2 = sub_c2.number_input("G2", min_value=0, max_value=15, step=1, value=val_res2, key=f"adm_r2_{row['id']}")
                    with c4:
                        bloqueado = st.checkbox("🚫 Bloquear", value=(row['estado'] == 1), key=f"block_{row['id']}")
                    
                    admin_inputs.append((row['id'], ya_jugado, g_r1, g_r2, bloqueado))
                    st.markdown("---")
                
                if st.form_submit_button("💾 GUARDAR CAMBIOS DE TODA LA FECHA"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    for p_id, jugado, r1, r2, block in admin_inputs:
                        nuevo_estado = 1 if (block or jugado) else 0
                        if jugado:
                            cursor.execute("UPDATE partidos SET resultado1 = ?, resultado2 = ?, estado = ? WHERE id = ?", (int(r1), int(r2), nuevo_estado, p_id))
                        else:
                            cursor.execute("UPDATE partidos SET resultado1 = NULL, resultado2 = NULL, estado = ? WHERE id = ?", (nuevo_estado, p_id))
                    conn.commit()
                    conn.close()
                    st.success("¡Base de datos actualizada por completo!")
                    st.rerun()
    else:
        st.warning("⚠️ Debes activar el modo Administrador ingresando la contraseña en la barra lateral izquierda para usar esta sección.")
