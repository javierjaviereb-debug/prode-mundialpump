import streamlit as st
import gspread
import pandas as pd
import json

st.set_page_config(page_title="Prode Empresarial", page_icon="⚽")
st.title("⚽ Prode Mundialista de la Empresa")

# 1. CREDENCIALES OFICIALES EMBEBIDAS DIRECTAMENTE EN EL CÓDIGO
credentials_dict = {
  "type": "service_account",
  "project_id": "evocative-fort-149211",
  "private_key_id": "31715bad40a8cfe2e3d95e9ea76fab8725c50d7d",
  
  # ACÁ USAMOS COMILLAS TRIPLES PARA QUE COPIES Y PEGUES TU CLAVE RESPETANDO SUS RENGLONES ORIGINALES
  "private_key": """-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDG8D0P94I+hpmE\n7jJRyZaEWJMp7SmXQGsIRLbQJqFvHVdNvfv8Ip3dmzz/qdl7q9eMtLFnhbg9KTAn\nFG8mZOdtDtEBgw12DfeobT+3YXGNpvk7rvshMRYZRy10LKDPNnGLS6owiEUiMqEF\nndRXtWP0yEhHmLTIFWistHORS9HySvkkMUCoiEDdHRo9PeBgRqbAeRohMrh7qUpN\nBGVq0ET5Xb3MOI28c+A+eDUnm5QzzcvCzwArEco+4qhsB5ZSuxrIH2HwbdeagRS2\n6e9/gGJrGIx3h0XtNyamLQ45iQPChx/gYweOZCbkbI5xudZQvf7Mjn+nLs+ut2ik\ntDFD+EhFAgMBAAECggEAG3lCiZG2OkHW8kF+EAb9wzXDTyM6XvHNxkTNFXZ8TW7Z\nJ3qhEetK73eYpzsy9o4fFMbAiEoyjTnCtWbwSbZeMpS8/w80/PSFWwyJY98wci5Y\n1an+8xDHG0MV7ykZpTxA1oqizJSJLaWd0LuA/4LktMGzH7YiY053mABMxIhazHHZ\nV1LLkw75UGkq0GL6mzV16fSjvNIY5WgHgKHHWEtopx21lgLpmLyc8x+vPF0h8NbD\nCKUvZyUpHV10r817GMtqGdp1sBIV/Bh8yTeXr2P50kbdwNIOlbEDAm15B2WVFa78\nG5MAM0wqdivUzAIYHaVxDy2Q1hBd97Hb0PA/ZMq3sQKBgQDnrIz6ec98zLzYIrBF\n5FFFihDToO5iceuQ1fi7UZeJ6/bldbUboNUsW1MRYzq1L5Ntu/3NR8PIbhm+NMvm\nHaAwfzLlM+4/x0iG3Q2V9ZDpSn7cHOuWEUjAA6/8wamHB/+LcP9InLCRRG7ueJAz\n6HGUYKxLZIyEIDrA74eU/c0atQKBgQDb079uOybP4+0+ySl3xfUFz+Ti517IkE8R\nuxAbGEYh1QM0o77cvrgat7PiOPHELpYHPKTyE+dN3bHlhSy22oshr//eTB1UX95d\nI3f7vxQL8oajW9naVgjetL86W5sqWveJnUzTye34rvdlYrQ0t/m/RAw8NGagjRWt\nJrcemIuhUQKBgGa/pn7oS1ekThTlvZwh2NGonDHf7BoJQFqqK3iYhUcMOiImhD5O\npHzZvAu4IK9+/Dns6HGE5JYeDpjHPa8/cG5R27a/w2jR756wp3fcw3pUKdNhmDKk\nU8mlWQYWtiNHLtUfNnlz1PN4kGJ/YiVDcCxIe+GsJI3s5WHwWgeAUNkJAoGBAIJY\nkE4AbQcgE3EDPr9yddM4bnPM1Xr/dqMA1I/8WLl+4SO5ZFboD6pn+xXMxi6ZoQQx\nhWy1OJYHOpDp4pWaCJ21Cnb5kvqQzf1UJrTznCNpb0Q2FntMQH4tlqY3402+GsFS\nsFd0iNLIjJFlcY1A+anb45VfTOsuPQgqyLIvqbvBAoGANbWcR2g38uwEF2ayCWSf\nGJJk5ySH8s/J9ADLvL5K9+GwfzSA4Da1nVwig/ZHqG4TKiu6D+7ecZgGa6+GkNK6\nyteTJ1ZdjFvw5/4R6ew3klolrMvje+FLoc8rm+6KdKe17QYapBO5vFtANpG+bX1j\n6sakcJwLUj7TLiQzQhpZaeE=\n-----END PRIVATE KEY-----\n",
  "client_email": "robot-prode-pump-874@evocative-fort-149211.iam.gserviceaccount.com""",
  
  "client_email": "robot-prode-pump-874@evocative-fort-149211.iam.gserviceaccount.com",
  "client_id": "100746124507407454473",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/robot-prode-pump-874%40evocative-fort-149211.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

url_sheet = "https://docs.google.com/spreadsheets/d/16GJrGu8Nto7EKCmmeH6yQTecXNU0jrYcUQX0VF0MGx8/edit?gid=0#gid=0"

# Conexión directa a la Google Sheet
try:
    gc = gspread.service_account_from_dict(credentials_dict)
    sh = gc.open_by_url(url_sheet)
    
    worksheet_partidos = sh.worksheet("Partidos")
    worksheet_predicciones = sh.worksheet("Predicciones")
    
    partidos_df = pd.DataFrame(worksheet_partidos.get_all_records())
    pred_data = worksheet_predicciones.get_all_records()
    
    if pred_data:
        predicciones_df = pd.DataFrame(pred_data)
    else:
        predicciones_df = pd.DataFrame(columns=["Usuario", "Partido_ID", "Pred_1", "Pred_2", "Puntos"])

    partidos_df.columns = partidos_df.columns.str.strip()
    predicciones_df.columns = predicciones_df.columns.str.strip()

except Exception as e:
    st.error("🚨 Error de conexión directa con Google Sheets:")
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
