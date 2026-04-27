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
if 'carrito_recibir' not in st.session_state:
    st.session_state.carrito_recibir = []
if 'carrito_entregar' not in st.session_state:
    st.session_state.carrito_entregar = []

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

# --- FUNCIONES DE LÓGICA ---
def actualizar_db(lista_codigos, operacion):
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    inv = {item['sticker_code']: (item['quantity'], item['team_code']) for item in res.data}
    
    for cod in lista_codigos:
        # Extraer sigla del código (ej: ARG de ARG5)
        equipo_sigla = "".join([c for c in cod if c.isalpha()]) if cod != '00' else 'FWC'
        actual, team = inv.get(cod, (0, equipo_sigla))
        nueva_cant = actual + 1 if operacion == "sumar" else max(0, actual - 1)
        
        supabase.table("user_stickers").upsert({
            "user_id": st.session_state.user.id,
            "sticker_code": cod,
            "team_code": team,
            "quantity": nueva_cant
        }, on_conflict="user_id,sticker_code").execute()

def procesar_intercambio_final():
    actualizar_db(st.session_state.carrito_recibir, "sumar")
    actualizar_db(st.session_state.carrito_entregar, "restar")
    st.session_state.carrito_recibir = []
    st.session_state.carrito_entregar = []
    st.success("¡Inventario actualizado correctamente!")
    st.balloons()

# --- VISTAS ---

def mostrar_intercambios():
    st.title("🤝 Centro de Intercambio")
    tab1, tab2 = st.tabs(["Comparar con Amigo", "📝 Registrar Intercambio Visual"])

    with tab2:
        st.write("Selecciona las estampas que vas a cambiar y agrégalas a las listas.")
        
        col_input_l, col_input_r = st.columns(2)
        
        # COLUMNA IZQUIERDA: RECIBIR
        with col_input_l:
            st.subheader("📥 Voy a RECIBIR")
            c1, c2, c3 = st.columns([2, 2, 1])
            sel_r = c1.selectbox("Selección", list(CONFIG_ALBUM.keys()), key="sel_rec")
            # Generar números para esa selección
            nums = (['00'] + [f'FWC{i}' for i in range(1, 20)] if sel_r == 'FWC' else 
                    ([f'CC{i}' for i in range(1, 15)] if sel_r == 'CC' else [f'{sel_r}{i}' for i in range(1, 21)]))
            num_r = c2.selectbox("Número", nums, key="num_rec")
            if c3.button("➕", key="add_rec"):
                st.session_state.carrito_recibir.append(num_r)
            
            # Mostrar tarjetas agregadas
            for i, item in enumerate(st.session_state.carrito_recibir):
                st.markdown(f'<div style="background:#14A8FD; color:white; padding:5px 15px; border-radius:20px; display:inline-block; margin:5px;">{item}</div>', unsafe_allow_html=True)
            if st.button("Limpiar lista recibidas"): st.session_state.carrito_recibir = []

        # COLUMNA DERECHA: ENTREGAR
        with col_input_r:
            st.subheader("📤 Voy a ENTREGAR")
            c4, c5, c6 = st.columns([2, 2, 1])
            sel_e = c4.selectbox("Selección", list(CONFIG_ALBUM.keys()), key="sel_ent")
            nums_e = (['00'] + [f'FWC{i}' for i in range(1, 20)] if sel_e == 'FWC' else 
                      ([f'CC{i}' for i in range(1, 15)] if sel_e == 'CC' else [f'{sel_e}{i}' for i in range(1, 21)]))
            num_e = c5.selectbox("Número", nums_e, key="num_ent")
            if c6.button("➕", key="add_ent"):
                st.session_state.carrito_entregar.append(num_e)
                
            # Mostrar tarjetas agregadas
            for i, item in enumerate(st.session_state.carrito_entregar):
                st.markdown(f'<div style="background:#FF4B4B; color:white; padding:5px 15px; border-radius:20px; display:inline-block; margin:5px;">{item}</div>', unsafe_allow_html=True)
            if st.button("Limpiar lista entregas"): st.session_state.carrito_entregar = []

        st.divider()
        if st.button("🚀 CONFIRMAR INTERCAMBIO", use_container_width=True):
            if not st.session_state.carrito_recibir and not st.session_state.carrito_entregar:
                st.error("Las listas están vacías.")
            else:
                procesar_intercambio_final()

# --- LAS DEMÁS FUNCIONES SE MANTIENEN IGUAL ---
def login_seccion():
    st.sidebar.title("🔐 Acceso")
    email = st.sidebar.text_input("Correo")
    passw = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Error")
    if st.sidebar.button("Registrarse"):
        try:
            res = supabase.auth.sign_up({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Error")

def mostrar_resumen():
    st.title("📊 Estadísticas Generales")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    total = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo = len(df[df['quantity'] > 0]) if not df.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso", f"{(tengo/total)*100:.1f}%")
    c2.metric("Tengo", tengo)
    c3.metric("Faltan", total - tengo)
    fig = px.pie(names=["Tengo", "Faltan"], values=[tengo, total-tengo], hole=0.5, color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]])
    st.plotly_chart(fig)

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
            if c1.button("➖", key=f"m_{cod}"): 
                nueva = max(0, cant - 1)
                supabase.table("user_stickers").upsert({"user_id": st.session_state.user.id, "sticker_code": cod, "team_code": sigla, "quantity": nueva}, on_conflict="user_id,sticker_code").execute()
                st.rerun()
            if c2.button("➕", key=f"p_{cod}"):
                supabase.table("user_stickers").upsert({"user_id": st.session_state.user.id, "sticker_code": cod, "team_code": sigla, "quantity": cant + 1}, on_conflict="user_id,sticker_code").execute()
                st.rerun()

def mostrar_ajustes():
    st.title("⚙️ Ajustes")
    with st.form("c_pass"):
        nueva = st.text_input("Nueva contraseña", type="password")
        if st.form_submit_button("Actualizar"):
            supabase.auth.update_user({"password": nueva})
            st.success("Cambiado.")
    if st.button("Eliminar Datos"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.button("Salir", on_click=lambda: (supabase.auth.sign_out(), st.session_state.update({"user": None})))
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "⚙️ Ajustes"])
    if menu == "🏠 Resumen": mostrar_resumen()
    elif menu == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
    elif menu == "🤝 Intercambios": mostrar_intercambios()
    else: mostrar_ajustes()
