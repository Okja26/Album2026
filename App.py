import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

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

st.set_page_config(page_title="Panini Hub", layout="wide")

# --- LEYENDA DE COLORES REUTILIZABLE ---
def mostrar_leyenda():
    st.markdown(f"""
        <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 20px;">
            <span style="color:{COLORS['Falta']}; font-weight:bold;">■ Rojo: Faltante</span>
            <span style="color:{COLORS['Tengo']}; font-weight:bold;">■ Azul: Ya la tienes (1)</span>
            <span style="color:{COLORS['Repetida']}; font-weight:bold;">■ Verde: Repetida (1+)</span>
        </div>
    """, unsafe_allow_html=True)

# --- CALLBACKS ---
def callback_login():
    try:
        res = supabase.auth.sign_in_with_password({"email": st.session_state.email_txt, "password": st.session_state.pass_txt})
        if res.user: st.session_state.user = res.user
    except: st.error("Credenciales incorrectas.")

def callback_signup():
    try:
        res = supabase.auth.sign_up({"email": st.session_state.email_txt, "password": st.session_state.pass_txt})
        if res.user: st.session_state.user = res.user
    except Exception as e: st.error(f"Error: {e}")

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
    st.info("Gestiona tu colección, visualiza tus estadísticas y encuentra intercambios fácilmente. Inicia sesión en el menú de la izquierda ↖️")
    st.sidebar.title("🔐 Acceso")
    tipo = st.sidebar.radio("Acción", ["Iniciar Sesión", "Registrarse"])
    st.sidebar.text_input("Correo", key="email_txt")
    st.sidebar.text_input("Contraseña", type="password", key="pass_txt")
    if tipo == "Iniciar Sesión":
        st.sidebar.button("Entrar", on_click=callback_login, use_container_width=True)
    else:
        st.sidebar.button("Crear Cuenta", on_click=callback_signup, use_container_width=True)

def mostrar_resumen():
    st.title("📊 Estadísticas Generales")
    st.write("Aquí puedes ver un resumen visual de qué tan cerca estás de completar tu álbum.")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df_actual = pd.DataFrame(res.data)
    total_album = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo_df = df_actual[df_actual['quantity'] > 0] if not df_actual.empty else pd.DataFrame()
    repetidas_df = df_actual[df_actual['quantity'] > 1] if not df_actual.empty else pd.DataFrame()
    
    cant_tengo = len(tengo_df)
    cant_faltan = total_album - cant_tengo
    cant_repetidas = (repetidas_df['quantity'] - 1).sum() if not repetidas_df.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Progreso", f"{(cant_tengo/total_album)*100:.1f}%")
    c2.metric("Pegadas", cant_tengo)
    c3.metric("Faltantes", cant_faltan)
    c4.metric("Repetidas", int(cant_repetidas))
    
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        fig_pie = px.pie(names=["Tengo", "Faltan"], values=[cant_tengo, cant_faltan], hole=0.5,
                         color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title="Estado del Álbum")
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_graf2:
        if not tengo_df.empty:
            stats_equipo = tengo_df.groupby('team_code').size().reset_index(name='cuenta').sort_values(by='cuenta', ascending=False).head(10)
            fig_bar = px.bar(stats_equipo, x='team_code', y='cuenta', title="Top 10 Selecciones Avanzadas", color_discrete_sequence=[COLORS["Repetida"]])
            st.plotly_chart(fig_bar, use_container_width=True)

def mostrar_seccion_dinamica(sigla):
    st.title(f"⚽ Selección: {sigla}")
    st.write("Gestiona las estampas de este equipo. Usa los botones para sumar o restar según las consigas.")
    mostrar_leyenda()
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

def mostrar_intercambios():
    st.title("🤝 Centro de Intercambios")
    st.write("Ingresa el código de un amigo para comparar sus colecciones automáticamente.")
    st.info(f"Tu código para compartir: `{st.session_state.user.id}`")
    
    amigo = st.text_input("Código de tu amigo:")
    if amigo and amigo != st.session_state.user.id:
        try:
            # Mis datos
            res_yo = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
            df_yo = pd.DataFrame(res_yo.data)
            mis_tengo = set(df_yo[df_yo['quantity'] > 0]['sticker_code']) if not df_yo.empty else set()
            mis_repetidas = set(df_yo[df_yo['quantity'] > 1]['sticker_code']) if not df_yo.empty else set()

            # Datos del amigo
            res_amigo = supabase.table("user_stickers").select("*").eq("user_id", amigo).execute()
            df_amigo = pd.DataFrame(res_amigo.data)
            amigo_tengo = set(df_amigo[df_amigo['quantity'] > 0]['sticker_code']) if not df_amigo.empty else set()
            amigo_repetidas = set(df_amigo[df_amigo['quantity'] > 1]['sticker_code']) if not df_amigo.empty else set()

            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("🎁 Él tiene para darte")
                st.write("(Repetidas de él que a ti te faltan)")
                lo_que_me_sirve = [r for r in amigo_repetidas if r not in mis_tengo]
                if lo_que_me_sirve:
                    for s in lo_que_me_sirve: st.success(f"✅ {s}")
                else: st.write("No tiene repetidas que te falten.")

            with col_b:
                st.subheader("🤲 Tú tienes para darle")
                st.write("(Tus repetidas que a él le faltan)")
                lo_que_le_sirve = [r for r in mis_repetidas if r not in amigo_tengo]
                if lo_que_le_sirve:
                    for s in lo_que_le_sirve: st.warning(f"💎 {s}")
                else: st.write("No tienes repetidas que le falten.")
        except: st.error("Código no encontrado.")

def mostrar_ajustes():
    st.title("⚙️ Ajustes")
    st.write("Configura tu cuenta o gestiona la eliminación de tus datos.")
    with st.form("cambio_pass"):
        nueva = st.text_input("Nueva contraseña", type="password")
        if st.form_submit_button("Actualizar"):
            supabase.auth.update_user({"password": nueva})
            st.success("Contraseña actualizada.")
    st.divider()
    if st.button("Eliminar mis datos del álbum"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.success("Datos borrados."); st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    st.sidebar.button("Cerrar Sesión", on_click=callback_logout)
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "⚙️ Ajustes"])
    if menu == "🏠 Resumen": mostrar_resumen()
    elif menu == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
    elif menu == "🤝 Intercambios": mostrar_intercambios()
    else: mostrar_ajustes()
