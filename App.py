import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from io import BytesIO

# 1. CONEXIÓN
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.user = session.user
    except:
        pass

# 2. CONFIGURACIÓN DEL ÁLBUM
CONFIG_ALBUM = {
    'FWC': 19, 'MEX': 20, 'RSA': 20, 'KOR': 20, 'CZE': 20, 'CAN': 20,
    'BIH': 20, 'QAT': 20, 'SUI': 20, 'BRA': 20, 'MAR': 20, 'HAI': 20,
    'SCO': 20, 'USA': 20, 'PAR': 20, 'AUS': 20, 'TUR': 20, 'GER': 20,
    'CUW': 20, 'CIV': 20, 'ECU': 20, 'NED': 20, 'JPN': 20, 'SWE': 20,
    'TUN': 20, 'CC': 14,  'BEL': 20, 'EGY': 20, 'IRN': 20, 'NZL': 20,
    'ESP': 20, 'CPV': 20, 'KSA': 20, 'URU': 20, 'FRA': 20, 'SEN': 20,
    'IRQ': 20, 'NOR': 20, 'ARG': 20, 'ALG': 20, 'AUT': 20, 'JOR': 20,
    'POR': 20, 'COD': 20, 'UZB': 20, 'COL': 20, 'ENG': 20, 'CRO': 20,
    'GHA': 20, 'PAN': 20
}

COLORS = {"Falta": "#FF4B4B", "Tengo": "#14A8FD", "Repetida": "#51D153"}

st.set_page_config(page_title="Danna's Panini Hub", layout="wide")

# --- FUNCIONES DE APOYO ---
def callback_logout():
    supabase.auth.sign_out()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state.user = None
    st.rerun()

def actualizar_cantidad(codigo, sigla, nueva_cant):
    if nueva_cant < 0: return
    try:
        data = {"user_id": st.session_state.user.id, "sticker_code": codigo, "team_code": sigla, "quantity": nueva_cant}
        supabase.table("user_stickers").upsert(data, on_conflict="user_id,sticker_code").execute()
        st.rerun()
    except Exception as e: st.error(f"Error: {e}")

# --- VISTAS ---

def login_seccion():
    st.title("👋 ¡Bienvenida a tu Panini Tracker!")
    st.info("Gestiona tu colección e intercambia fácilmente. Inicia sesión a la izquierda ↖️")
    st.sidebar.title("🔐 Acceso")
    email = st.sidebar.text_input("Correo")
    passw = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Error en datos")
    if st.sidebar.button("Registrarse"):
        try:
            res = supabase.auth.sign_up({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Error al crear cuenta")

def mostrar_exportar():
    st.title("📥 Exportar mis Listas")
    st.write("Descarga tus listas para compartirlas por WhatsApp o redes sociales.")
    
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    
    if df.empty:
        st.warning("Aún no tienes datos cargados en tu álbum.")
        return

    # 1. Preparar lista de FALTANTES
    pegadas = set(df[df['quantity'] > 0]['sticker_code'])
    faltantes = []
    for team, total in CONFIG_ALBUM.items():
        rango = (['00'] + [f'FWC{i}' for i in range(1, 20)] if team == 'FWC' else 
                 ([f'CC{i}' for i in range(1, 15)] if team == 'CC' else [f'{team}{i}' for i in range(1, 21)]))
        for cod in rango:
            if cod not in pegadas:
                faltantes.append({"Equipo": team, "Código": cod})
    
    df_faltantes = pd.DataFrame(faltantes)

    # 2. Preparar lista de REPETIDAS
    df_repetidas = df[df['quantity'] > 1].copy()
    df_repetidas['Cantidad Extra'] = df_repetidas['quantity'] - 1
    df_repetidas = df_repetidas[['team_code', 'sticker_code', 'Cantidad Extra']].rename(columns={'team_code': 'Equipo', 'sticker_code': 'Código'})

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚩 Mis Faltantes")
        st.dataframe(df_faltantes, use_container_width=True)
        csv_f = df_faltantes.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Faltantes (CSV)", data=csv_f, file_name="mis_faltantes.csv", mime="text/csv")

    with col2:
        st.subheader("💎 Mis Repetidas")
        st.dataframe(df_repetidas, use_container_width=True)
        csv_r = df_repetidas.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar Repetidas (CSV)", data=csv_r, file_name="mis_repetidas.csv", mime="text/csv")

# (Las demás funciones: mostrar_resumen, mostrar_seccion_dinamica, mostrar_intercambios, mostrar_ajustes se mantienen igual)
# Solo recuerda agregar "📥 Exportar" al radio button del menú.

def mostrar_resumen():
    st.title("📊 Estadísticas Generales")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df_actual = pd.DataFrame(res.data)
    total_album = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo_df = df_actual[df_actual['quantity'] > 0] if not df_actual.empty else pd.DataFrame()
    cant_tengo = len(tengo_df)
    cant_faltan = total_album - cant_tengo
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso", f"{(cant_tengo/total_album)*100:.1f}%")
    c2.metric("Pegadas", cant_tengo)
    c3.metric("Faltantes", cant_faltan)
    fig_pie = px.pie(names=["Tengo", "Faltan"], values=[cant_tengo, cant_faltan], hole=0.5,
                     color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title="Distribución")
    st.plotly_chart(fig_pie)

def mostrar_seccion_dinamica(sigla):
    st.title(f"⚽ Selección: {sigla}")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).eq("team_code", sigla).execute()
    inventario = {item['sticker_code']: item['quantity'] for item in res.data}
    codigos = (['00'] + [f'FWC{i}' for i in range(1, 20)] if sigla == 'FWC' else 
               ([f'CC{i}' for i in range(1, 15)] if sigla == 'CC' else [f'{sigla}{i}' for i in range(1, 21)]))
    cols = st.columns(4)
    for idx, cod in enumerate(codigos):
        cant = inventario.get(cod, 0)
        color = COLORS["Falta"] if cant == 0 else (COLORS["Tengo"] if cant == 1 else COLORS["Repetida"])
        with cols[idx % 4]:
            st.markdown(f'<div style="border:3px solid {color}; border-radius:10px; padding:10px; text-align:center; background:rgba(255,255,255,0.05);"><h3>{cod}</h3><p>Cant: {cant}</p></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("➖", key=f"m_{cod}"): actualizar_cantidad(cod, sigla, cant - 1)
            if c2.button("➕", key=f"p_{cod}"): actualizar_cantidad(cod, sigla, cant + 1)

# --- NAVEGACIÓN PRINCIPAL ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    st.sidebar.button("Cerrar Sesión", on_click=callback_logout)
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    
    if menu == "🏠 Resumen": mostrar_resumen()
    elif menu == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
    elif menu == "🤝 Intercambios": # Lógica de intercambios anterior
        st.title("🤝 Intercambios")
        st.info(f"Tu código: {st.session_state.user.id}")
        # ... (aquí va el código de comparar con amigo que ya teníamos)
    elif menu == "📥 Exportar": mostrar_exportar()
    else: # Ajustes
        st.title("⚙️ Ajustes")
        if st.button("Eliminar mis datos"):
            supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
            st.rerun()
