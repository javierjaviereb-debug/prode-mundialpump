import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽", layout="wide")
st.title("⚽ Prode Mundialista - Pump Control")

# --- DICCIONARIO AUTOMÁTICO DE BANDERAS ---
BANDERAS = {
    "argentina": "🇦🇷", "brasil": "🇧🇷", "uruguay": "🇺🇾", "colombia": "🇨🇴", 
    "chile": "🇨🇱", "peru": "🇵🇪", "ecuador": "🇪🇨", "venezuela": "🇻🇪", 
    "paraguay": "🇵🇾", "bolivia": "🇧🇴", "usa": "🇺🇸", "estados unidos": "🇺🇸", 
    "mexico": "🇲🇽", "méxico": "🇲🇽", "canada": "🇨🇦", "canadá": "🇨🇦",
    "francia": "🇫🇷", "alemania": "🇩🇪", "italia": "🇮🇹", "españa": "🇪🇸", 
    "inglaterra": "🇬🇧", "portugal": "🇵🇹", "holanda": "🇳🇱", "países bajos": "🇳🇱", 
    "belgica": "🇧🇪", "bélgica": "🇧🇪", "croacia": "🇭🇷", "suiza": "🇨🇭",
    "japon": "🇯🇵", "japón": "🇯🇵", "corea del sur": "🇰🇷", "australia": "🇦🇺", 
    "marruecos": "🇲🇦", "senegal": "🇸🇳", "arabia saudita": "🇸🇦", "catar": "🇶🇦"
}

def obtener_bandera(nombre_equipo):
    nombre_limpio = str(nombre_equipo).strip().lower()
    return BANDERAS.get(nombre_limpio, "⚽")

# --- 1. BASE DE DATOS LOCAL (SQLITE) ---
DB_NAME = "prode_internal.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def inicializar_base_datos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partidos (
        id TEXT PRIMARY KEY,
        grupo TEXT,
        equipo1 TEXT,
        equipo2 TEXT,
        resultado1 INTEGER,
        resultado2 INTEGER,
        fecha_partido TEXT,
        estado INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predicciones (
        usuario TEXT,
        partido_id TEXT,
        pred_1 INTEGER,
        pred_2 INTEGER,
        PRIMARY KEY (usuario, partido_id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios_autorizados (
        usuario TEXT PRIMARY KEY,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

inicializar_base_datos()

# --- CARGAR DATOS EN TIEMPO REAL ---
conn = get_connection()
partidos_df = pd.read_sql_query("SELECT * FROM partidos", conn)
predicciones_df = pd.read_sql_query("SELECT * FROM predicciones", conn)
try:
    usuarios_auth_df = pd.read_sql_query("SELECT * FROM usuarios_autorizados", conn)
except:
    usuarios_auth_df = pd.DataFrame(columns=["usuario", "password"])
conn.close()

# --- PANEL DE ADMINISTRADOR EN LA BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Control (Admin)")
    modo_admin = st.checkbox("Activar modo Administrador")
    if modo_admin:
        password = st.text_input("Contraseña de Admin", type="password")
        if password == "pump2026":
            st.success("¡Acceso Admin concedido!")
            
            st.markdown("---")
            st.subheader("👥 Cuentas Habilitadas")
            if not usuarios_auth_df.empty:
                st.write(f"Total: **{len(usuarios_auth_df)}** usuarios")
                st.dataframe(usuarios_auth_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("👥 Carga Masiva de Empleados")
            data_usuarios_masiva = st.text_area("Formato: usuario, contraseña", height=100, key="txt_usuarios_masiva")
            if st.button("👥 Cargar Listado de Usuarios"):
                if data_usuarios_masiva.strip():
                    lineas = data_usuarios_masiva.strip().split("\n")
                    usuarios_a_insertar = []
                    for linea in lineas:
                        if not linea.strip(): continue
                        partes = linea.split(",")
                        if len(partes) == 2:
                            usuarios_a_insertar.append((partes[0].strip().lower(), partes[1].strip()))
                    if usuarios_a_insertar:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.executemany("INSERT OR REPLACE INTO usuarios_autorizados (usuario, password) VALUES (?, ?)", usuarios_a_insertar)
                        conn.commit()
                        conn.close()
                        st.success("¡Usuarios habilitados!")
                        st.rerun()

            st.markdown("---")
            st.subheader("⚡ Carga Masiva de Partidos")
            st.caption("ID, Grupo, Equipo A, Equipo B, AAAA-MM-DD HH:MM")
            data_masiva = st.text_area("Lista de partidos:", height=100)
            if st.button("🚀 Inyectar Fixture Masivo"):
                if data_masiva.strip():
                    lineas = data_masiva.strip().split("\n")
                    partidos_a_insertar = []
                    for linea in lineas:
                        if not linea.strip(): continue
                        partes = linea.split(",")
                        if len(partes) == 5:
                            partidos_a_insertar.append((partes[0].strip(), partes[1].strip(), partes[2].strip(), partes[3].strip(), partes[4].strip()))
                    if partidos_a_insertar:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.executemany("INSERT OR REPLACE INTO partidos (id, grupo, equipo1, equipo2, fecha_partido, estado) VALUES (?, ?, ?, ?, ?, 0)", partidos_a_insertar)
                        conn.commit()
                        conn.close()
                        st.success("¡Fixture actualizado!")
                        st.rerun()
        elif password != "":
            st.error("Contraseña incorrecta")

# --- 2. MOTOR AUTOMÁTICO DE PUNTOS ---
if not predicciones_df.empty and not partidos_df.empty:
    prode_merge = pd.merge(predicciones_df, partidos_df, left_on="partido_id", right_on="id", how="left")
    def calcular_puntos(row):
        if pd.isna(row['resultado1']) or row['resultado1'] is None: return 0
        try:
            p1, p2 = int(row['pred_1']), int(row['pred_2'])
            r1, r2 = int(row['resultado1']), int(row['resultado2'])
            if p1 == r1 and p2 == r2: return 3
            if (p1 == p2) and (r1 == r2): return 1
            if (p1 > p2) and (r1 > r2): return 1
            if (p1 < p2) and (r1 < r2): return 1
            return 0
        except: return 0
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

# TAB 1: MI JUEGO (REDISEÑADO CON BANDERAS Y SIN LA PALABRA 'GOLES')
with tab1:
    st.header("📝 Tus Pronósticos de la Fecha")
    col_user, col_pass = st.columns(2)
    with col_user: usuario = st.text_input("Ingresá tu usuario de la empresa:").strip().lower()
    with col_pass: user_password = st.text_input("Ingresá tu contraseña:", type="password").strip()
    
    if usuario and user_password:
        credenciales_correctas = False
        if not usuarios_auth_df.empty:
            usuario_row = usuarios_auth_df[usuarios_auth_df['usuario'] == usuario]
            if not usuario_row.empty and str(usuario_row.iloc[0]['password']).strip() == user_password:
                credenciales_correctas = True
        
        if not credenciales_correctas:
            st.error("❌ Usuario o contraseña incorrectos.")
        else:
            st.success(f"🔓 ¡Autenticado como: **{usuario}**!")
            now = datetime.now()
            partidos_abiertos = []
            
            if not partidos_df.empty:
                for idx, row in partidos_df.iterrows():
                    if row['estado'] == 1: continue
                    if row['fecha_partido']:
                        dt_partido = datetime.strptime(row['fecha_partido'], "%Y-%m-%d %H:%M")
                        if now < (dt_partido - timedelta(days=1)):
                            partidos_abiertos.append(row)
            
            partidos_votables = pd.DataFrame(partidos_abiertos)
            
            if partidos_votables.empty:
                st.info("No hay partidos abiertos para pronosticar en este momento (el límite cierra 24hs antes).")
            else:
                with st.form("form_prode_usuario"):
                    inputs = []
                    for idx, row in partidos_votables.iterrows():
                        voto_previo = predicciones_df[(predicciones_df['usuario'] == usuario) & (predicciones_df['partido_id'] == row['id'])]
                        val_def1 = int(voto_previo.iloc[0]['pred_1']) if not voto_previo.empty else 0
                        val_def2 = int(voto_previo.iloc[0]['pred_2']) if not voto_previo.empty else 0
                        
                        dt_p = datetime.strptime(row['fecha_partido'], "%Y-%m-%d %H:%M")
                        dt_l = dt_p - timedelta(days=1)
                        
                        # Obtener banderas animadas por texto
                        b1 = obtener_bandera(row['equipo1'])
                        b2 = obtener_bandera(row['equipo2'])
                        
                        col_info, col_inputs = st.columns([2, 2])
                        with col_info:
                            st.markdown(f"🏆 **{row['grupo']}** | {b1} **{row['equipo1']}** vs. **{row['equipo2']}** {b2}")
                            st.caption(f"📅 Partido: {dt_p.strftime('%d/%m %H:%M')} hs | 🔒 Cierra: {dt_l.strftime('%d/%m %H:%M')} hs")
                            if not voto_previo.empty:
                                st.markdown(f"<span style='color:green;'>✔️ Tu carga actual: {val_def1} - {val_def2}</span>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span style='color:orange;'>⏳ Pendiente de carga</span>", unsafe_allow_html=True)
                        
                        with col_inputs:
                            sub_c1, sub_c2 = st.columns(2)
                            # Se eliminó la palabra 'Goles' y se colocó directo la bandera para máxima limpieza visual
                            with sub_c1: g1 = st.number_input(f"{b1} {row['equipo1']}", min_value=0, max_value=15, step=1, value=val_def1, key=f"u1_{row['id']}")
                            with sub_c2: g2 = st.number_input(f"{row['equipo2']} {b2}", min_value=0, max_value=15, step=1, value=val_def2, key=f"u2_{row['id']}")
                        
                        inputs.append((row['id'], g1, g2))
                        st.markdown("---")
                        
                    if st.form_submit_button("💾 Guardar / Modificar mis Pronósticos"):
                        conn = get_connection()
                        cursor = conn.cursor()
                        for p_id, g1, g2 in inputs:
                            cursor.execute("INSERT OR REPLACE INTO predicciones (usuario, partido_id, pred_1, pred_2) VALUES (?, ?, ?, ?)", (usuario, str(p_id), int(g1), int(g2)))
                        conn.commit()
                        conn.close()
                        st.success("¡Tus pronósticos se guardaron con éxito!")
                        st.rerun()

# TAB 2: RANKING EN VIVO
with tab2:
    st.header("🏆 Ranking de la Oficina en Vivo")
    if tabla_posiciones.empty: st.info("Aún no hay predicciones cargadas.")
    else: st.table(tabla_posiciones)

# TAB 3: CONSULTAR JUGADAS DE CUALQUIERA
with tab3:
    st.header("🔍 Consultar Pronósticos Registrados")
    if predicciones_df.empty: st.info("No hay pronósticos registrados.")
    else:
        todos_usuarios = sorted(predicciones_df["usuario"].unique())
        user_sel = st.selectbox("Seleccioná un compañero para ver su juego:", todos_usuarios)
        if user_sel:
            votos_user = predicciones_df[predicciones_df["usuario"] == user_sel]
            votos_merge = pd.merge(votos_user, partidos_df, left_on="partido_id", right_on="id")
            votos_merge["Resultado Real"] = votos_merge.apply(lambda r: f"{r['resultado1']} - {r['resultado2']}" if pd.notna(r['resultado1']) else "Pendiente ⏳", axis=1)
            votos_merge["Su Pronóstico"] = votos_merge["pred_1"].astype(str) + " - " + votos_merge["pred_2"].astype(str)
            
            # Sumar banderas a la consulta de otros usuarios
            votos_merge["Partido"] = votos_merge["equipo1"].apply(obtener_bandera) + " " + votos_merge["equipo1"] + " vs. " + votos_merge["equipo2"] + " " + votos_merge["equipo2"].apply(obtener_bandera)
            
            tabla_ver = votos_merge[["grupo", "Partido", "Su Pronóstico", "Resultado Real"]]
            tabla_ver.columns = ["Grupo/Etapa", "Partido", "Su Pronóstico", "Resultado Oficial"]
            st.dataframe(tabla_ver, use_container_width=True, hide_index=True)

# TAB 4: PANTALLA MASIVA DEL ADMINISTRADOR
with tab4:
    st.header("👑 Panel de Gestión Masiva (Exclusivo Administrador)")
    if modo_admin and password == "pump2026":
        if partidos_df.empty:
            st.info("No hay partidos creados en el fixture todavía.")
        else:
            with st.form("form_
