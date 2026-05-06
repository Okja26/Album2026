import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. CONEXIÓN A SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- INICIALIZACIÓN DE ESTADO ---
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

GRUPOS = {
    "Grupo A": ["QAT", "ECU", "SEN", "NED"],
    "Grupo B": ["ENG", "IRN", "USA", "WAL"],
    "Grupo C": ["ARG", "KSA", "MEX", "POL"],
    "Grupo D": ["FRA", "AUS", "DEN", "TUN"],
    "Grupo E": ["ESP", "CRC", "GER", "JPN"],
    "Grupo F": ["BEL", "CAN", "MAR", "CRO"],
    "Grupo G": ["BRA", "SRB", "SUI", "CMR"],
    "Grupo H": ["POR", "GHA", "URU", "KOR"],
    "Especiales": ["FWC", "CC"]
}

COLORS = {"Falta": "#FF4B4B", "Tengo": "#14A8FD", "Repetida": "#51D153"}

st.set_page_config(page_title="Danna's Panini Hub", layout="wide")

# --- FUNCIONES DE LÓGICA ---

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

def callback_logout():
    supabase.auth.sign_out()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state.user = None
    st.rerun()

# --- VISTAS ---

def login_seccion():
    st.title("👋 Panini Tracker")
    st.sidebar.title("🔐 Acceso")
    email = st.sidebar.text_input("Correo", key="email_txt")
    passw = st.sidebar.text_input("Contraseña", type="password", key="pass_txt")
    if st.sidebar.button("Entrar", use_container_width=True):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Error en credenciales")

def mostrar_resumen():
    st.title("📊 Estadísticas Detalladas")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    
    if not res.data:
        tengo_df = pd.DataFrame(columns=['team_code', 'sticker_code', 'quantity'])
    else:
        df_db = pd.DataFrame(res.data)
        tengo_df = df_db[df_db['quantity'] > 0]
    
    total_album = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    cant_tengo = len(tengo_df)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso Total", f"{(cant_tengo/total_album)*100:.1f}%")
    c2.metric("Pegadas", cant_tengo)
    c3.metric("Faltantes", total_album - cant_tengo)
    
    st.divider()
    modo = st.radio("Analizar por:", ["Grupos", "Selección Específica"], horizontal=True)
    
    if modo == "Grupos":
        op_g = st.selectbox("Selecciona Grupo", list(GRUPOS.keys()))
        equipos = GRUPOS[op_g]
        t_g = len(tengo_df[tengo_df['team_code'].isin(equipos)])
        tot_g = sum([CONFIG_ALBUM.get(e, 20) + (1 if e=='FWC' else 0) for e in equipos])
        
        col_p, col_i = st.columns([2, 1])
        with col_p:
            fig = px.pie(names=["Tengo", "Faltan"], values=[t_g, tot_g - t_g], hole=0.5,
                         color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title=f"Avance {op_g}")
            st.plotly_chart(fig, use_container_width=True)
        with col_i:
            for e in equipos:
                count = len(tengo_df[tengo_df['team_code'] == e])
                total_e = CONFIG_ALBUM.get(e, 20) + (1 if e=='FWC' else 0)
                st.write(f"**{e}:** {count}/{total_e}")

    else:
        op_s = st.selectbox("Selecciona Selección", list(CONFIG_ALBUM.keys()))
        t_s = len(tengo_df[tengo_df['team_code'] == op_s])
        tot_s = CONFIG_ALBUM.get(op_s, 20) + (1 if op_s=='FWC' else 0)
        fig = px.pie(names=["Tengo", "Faltan"], values=[t_s, tot_s - t_s], hole=0.5,
                     color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title=f"Avance {op_s}")
        st.plotly_chart(fig)

def vista_intercambios():
    st.title("🤝 Centro de Intercambios")
    t1, t2 = st.tabs(["🔄 Registro Visual", "🔍 Comparar con Amigo"])
    
    with t1:
        res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        cl, cr = st.columns(2)
        with cl:
            st.subheader("📥 Recibo")
            eq_r = st.selectbox("Equipo", list(CONFIG_ALBUM.keys()), key="er")
            nums = (['00'] + [f'FWC{i}' for i in range(1, 20)] if eq_r == 'FWC' else 
                    ([f'CC{i}' for i in range(1, 15)] if eq_r == 'CC' else [f'{eq_r}{i}' for i in range(1, 21)]))
            cod_r = st.selectbox("Estampa", nums, key="cr")
            if st.button("Añadir a Recibo"): st.session_state.carrito_recibir.append(cod_r); st.rerun()
            
            for i, item in enumerate(st.session_state.carrito_recibir):
                ct, cd = st.columns([4, 1])
                ct.markdown(f'<span style="background:#14A8FD; color:white; padding:5px 10px; border-radius:15px; display:inline-block; margin:2px;">✅ {item}</span>', unsafe_allow_html=True)
                if cd.button("🗑️", key=f"dr_{i}"): st.session_state.carrito_recibir.pop(i); st.rerun()

        with cr:
            st.subheader("📤 Entrego")
            if not df_inv.empty and 'reserved_to' in df_inv.columns:
                amigos = [a for a in df_inv['reserved_to'].unique() if a]
                if amigos:
                    amigo_sel = st.selectbox("Cargar apartados de:", amigos)
                    if st.button(f"Cargar de {amigo_sel}"):
                        st.session_state.carrito_entregar.extend(df_inv[df_inv['reserved_to'] == amigo_sel]['sticker_code'].tolist())
                        st.rerun()
            
            man = st.text_input("Manual (comas):")
            if st.button("Añadir Manual"):
                st.session_state.carrito_entregar.extend([x.strip().upper() for x in man.split(",") if x]); st.rerun()
            
            for i, item in enumerate(st.session_state.carrito_entregar):
                ct, cd = st.columns([4, 1])
                ct.markdown(f'<span style="background:#FF4B4B; color:white; padding:5px 10px; border-radius:15px; display:inline-block; margin:2px;">💎 {item}</span>', unsafe_allow_html=True)
                if cd.button("🗑️", key=f"de_{i}"): st.session_state.carrito_entregar.pop(i); st.rerun()

        if st.button("🚀 Confirmar Intercambio", use_container_width=True):
            actualizar_db(st.session_state.carrito_recibir, "sumar")
            actualizar_db(st.session_state.carrito_entregar, "restar")
            st.session_state.carrito_recibir, st.session_state.carrito_entregar = [], []
            st.success("¡Hecho!"); st.rerun()

    with t2:
        st.subheader("🔍 Comparador de Álbumes")
        st.info(f"Tu ID: `{st.session_state.user.id}`")
        id_amigo = st.text_input("ID del Amigo:")
        if id_amigo and id_amigo != st.session_state.user.id:
            try:
                # Mis datos
                res_yo = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
                df_yo = pd.DataFrame(res_yo.data) if res_yo.data else pd.DataFrame()
                mis_tengo = set(df_yo[df_yo['quantity'] > 0]['sticker_code']) if not df_yo.empty else set()
                mis_rep = set(df_yo[df_yo['quantity'] > 1]['sticker_code']) if not df_yo.empty else set()
                
                # Datos amigo
                res_am = supabase.table("user_stickers").select("*").eq("user_id", id_amigo).execute()
                df_am = pd.DataFrame(res_am.data)
                am_tengo = set(df_am[df_am['quantity'] > 0]['sticker_code'])
                am_rep = set(df_am[df_am['quantity'] > 1]['sticker_code'])
                
                c1, c2 = st.columns(2)
                with c1:
                    st.write("🎁 Él te da:")
                    for s in [x for x in am_rep if x not in mis_tengo]: st.success(f"✅ {s}")
                with c2:
                    st.write("🤲 Tú le das:")
                    for s in [x for x in mis_rep if x not in am_tengo]: st.warning(f"💎 {s}")
            except: st.error("ID no válido")

def mostrar_exportar():
    st.title("📥 Exportar")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    pegadas = set(df[df['quantity'] > 0]['sticker_code']) if not df.empty else set()
    faltantes = []
    for t, tot in CONFIG_ALBUM.items():
        r = (['00'] + [f'FWC{i}' for i in range(1, 20)] if t == 'FWC' else 
             ([f'CC{i}' for i in range(1, 15)] if t == 'CC' else [f'{t}{i}' for i in range(1, 21)]))
        for c in r:
            if c not in pegadas: faltantes.append({"Selección": t, "Código": c})
    
    st.download_button("Descargar Faltantes (CSV)", pd.DataFrame(faltantes).to_csv(index=False), "faltantes.csv")
    rep = df[df['quantity'] > 1].copy() if not df.empty else pd.DataFrame()
    if not rep.empty:
        rep['Extra'] = rep['quantity'] - 1
        st.download_button("Descargar Repetidas (CSV)", rep[['team_code', 'sticker_code', 'Extra']].to_csv(index=False), "repetidas.csv")

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.button("Cerrar Sesión", on_click=callback_logout)
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    
    if menu == "🏠 Resumen": mostrar_resumen()
    elif menu == "🚩 Selecciones":
        sigla = st.sidebar.selectbox("Selección", list(CONFIG_ALBUM.keys()))
        res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).eq("team_code", sigla).execute()
        inv = {item['sticker_code']: item['quantity'] for item in res.data}
        cods = (['00'] + [f'FWC{i}' for i in range(1, 20)] if sigla == 'FWC' else ([f'CC{i}' for i in range(1, 15)] if sigla == 'CC' else [f'{sigla}{i}' for i in range(1, 21)]))
        cols = st.columns(4)
        for i, c in enumerate(cods):
            cant = inv.get(c, 0)
            color = COLORS["Falta"] if cant == 0 else (COLORS["Tengo"] if cant == 1 else COLORS["Repetida"])
            with cols[i % 4]:
                st.markdown(f'<div style="border:2px solid {color}; padding:10px; text-align:center;">{c}<br>Cant: {cant}</div>', unsafe_allow_html=True)
                if st.button("➕", key=f"p_{c}"): actualizar_db([c], "sumar"); st.rerun()
                if st.button("➖", key=f"m_{c}"): actualizar_db([c], "restar"); st.rerun()
    elif menu == "🤝 Intercambios": vista_intercambios()
    elif menu == "📥 Exportar": mostrar_exportar()
    else:
        st.title("⚙️ Ajustes")
        if st.button("Borrar Datos"): supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute(); st.rerun()
