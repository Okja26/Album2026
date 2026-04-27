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

st.set_page_config(page_title="Danna's Panini Hub", layout="wide")

# --- LÓGICA DE DATOS ---
def actualizar_db(lista_codigos, operacion):
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    inv = {item['sticker_code']: (item['quantity'], item['team_code']) for item in res.data}
    
    for cod in lista_codigos:
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
    st.success("¡Inventario actualizado!")
    st.rerun()

# --- VISTAS ---
def login_seccion():
    st.title("👋 ¡Bienvenida!")
    st.sidebar.title("🔐 Acceso")
    email = st.sidebar.text_input("Correo")
    passw = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar", use_container_width=True):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Credenciales incorrectas")

def mostrar_resumen():
    st.title("📊 Estadísticas")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    total = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo = len(df[df['quantity'] > 0]) if not df.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso", f"{(tengo/total)*100:.1f}%")
    c2.metric("Tengo", tengo)
    c3.metric("Faltan", total - tengo)
    
    fig = px.pie(names=["Tengo", "Faltan"], values=[tengo, total-tengo], hole=0.5, 
                 color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]])
    st.plotly_chart(fig, use_container_width=True)

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
                actualizar_db([cod], "restar")
                st.rerun()
            if c2.button("➕", key=f"p_{cod}"):
                actualizar_db([cod], "sumar")
                st.rerun()

def mostrar_intercambios():
    st.title("🤝 Intercambios")
    tab1, tab2 = st.tabs(["Registro Visual", "Comparar con Amigo"])
    
    with tab1:
        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("📥 Recibo")
            c1, c2, c3 = st.columns([2,2,1])
            s_r = c1.selectbox("Equipo", list(CONFIG_ALBUM.keys()), key="sr")
            n_r = (['00'] + [f'FWC{i}' for i in range(1, 20)] if s_r == 'FWC' else 
                   ([f'CC{i}' for i in range(1, 15)] if s_r == 'CC' else [f'{s_r}{i}' for i in range(1, 21)]))
            cod_r = c2.selectbox("Número", n_r, key="nr")
            if c3.button("➕", key="br"): st.session_state.carrito_recibir.append(cod_r)
            for item in st.session_state.carrito_recibir:
                st.markdown(f'<span style="background:#14A8FD; color:white; padding:5px 10px; border-radius:15px; margin-right:5px;">{item}</span>', unsafe_allow_html=True)

        with col_r:
            st.subheader("📤 Entrego")
            c4, c5, c6 = st.columns([2,2,1])
            s_e = c4.selectbox("Equipo", list(CONFIG_ALBUM.keys()), key="se")
            n_e = (['00'] + [f'FWC{i}' for i in range(1, 20)] if s_e == 'FWC' else 
                   ([f'CC{i}' for i in range(1, 15)] if s_e == 'CC' else [f'{s_e}{i}' for i in range(1, 21)]))
            cod_e = c5.selectbox("Número", n_e, key="ne")
            if c6.button("➕", key="be"): st.session_state.carrito_entregar.append(cod_e)
            for item in st.session_state.carrito_entregar:
                st.markdown(f'<span style="background:#FF4B4B; color:white; padding:5px 10px; border-radius:15px; margin-right:5px;">{item}</span>', unsafe_allow_html=True)
        
        if st.button("🚀 Confirmar Intercambio", use_container_width=True):
            procesar_intercambio_final()

def mostrar_exportar():
    st.title("📥 Exportar Datos")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    
    # Lógica de Faltantes
    pegadas = set(df[df['quantity'] > 0]['sticker_code']) if not df.empty else set()
    faltantes = []
    for team, total in CONFIG_ALBUM.items():
        rango = (['00'] + [f'FWC{i}' for i in range(1, 20)] if team == 'FWC' else 
                 ([f'CC{i}' for i in range(1, 15)] if team == 'CC' else [f'{team}{i}' for i in range(1, 21)]))
        for c in rango:
            if c not in pegadas: faltantes.append(c)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Tienes {len(faltantes)} faltantes")
        df_f = pd.DataFrame(faltantes, columns=["Código"])
        st.download_button("Descargar Faltantes (CSV)", df_f.to_csv(index=False), "faltantes.csv", "text/csv")
    with col2:
        df_r = df[df['quantity'] > 1].copy() if not df.empty else pd.DataFrame()
        st.write(f"Tienes {len(df_r)} repetidas")
        st.download_button("Descargar Repetidas (CSV)", df_r.to_csv(index=False), "repetidas.csv", "text/csv")

def mostrar_ajustes():
    st.title("⚙️ Ajustes")
    with st.form("pass"):
        n = st.text_input("Nueva Contraseña", type="password")
        if st.form_submit_button("Actualizar"):
            supabase.auth.update_user({"password": n})
            st.success("Actualizada")
    if st.button("Borrar Cuenta"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"user": None}))
    m = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    if m == "🏠 Resumen": mostrar_resumen()
    elif m == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
    elif m == "🤝 Intercambios": mostrar_intercambios()
    elif m == "📥 Exportar": mostrar_exportar()
    else: mostrar_ajustes()
