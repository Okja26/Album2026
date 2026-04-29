import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. CONEXIÓN A SUPABASE
# Asegúrate de tener SUPABASE_URL y SUPABASE_KEY en tus Secrets de Streamlit
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

# Recuperar sesión automática si existe
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

GRUPOS= {
    "FWC" : ["FWC"],
    "Grupo A" : ["MEX", "RSA", "KOR", "CZE"],
    "Grupo B" : ["CAN", "BIH", "QAT", "SUI"],
    "Grupo C" : ["BRA", "MAR", "HAI", "SCO"],
    "Grupo D" : ["USA", "PAR", "AUS", "TUR"],
    "Grupo E" : ["GER", "CUW", "CIV", "ECU"],
    "Grupo F" : ["NED", "JPN", "SWE", "TUN"],
    "Coca Cola": ["CC"],
    "Grupo G" : ["BEL", "EGY", "IRN", "NZL"],
    "Grupo H" : ["ESP", "CPV", "KSA", "URU"],
    "Grupo I" : ["fFRA", "SEN", "IRQ", "NOR"],
    "Grupo J" : ["ARG", "ALG", "AUT", "JOR"],
    "Grupo K" : ["POR", "COD", "UZB", "COL"],
    "Grupo L" : ["ENG", "CRO", "GHA", "PAN"]
}

COLORS = {"Falta": "#FF4B4B", "Tengo": "#14A8FD", "Repetida": "#51D153"}

st.set_page_config(page_title="Panini Hub", layout="wide")

# --- FUNCIONES DE LÓGICA ---

def callback_login():
    try:
        res = supabase.auth.sign_in_with_password({
            "email": st.session_state.email_txt, 
            "password": st.session_state.pass_txt
        })
        if res.user: st.session_state.user = res.user
    except: st.error("Credenciales incorrectas.")

def callback_signup():
    try:
        res = supabase.auth.sign_up({
            "email": st.session_state.email_txt, 
            "password": st.session_state.pass_txt
        })
        if res.user: st.session_state.user = res.user
    except Exception as e: st.error(f"Error: {e}")

def callback_logout():
    supabase.auth.sign_out()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state.user = None
    st.rerun()

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
    st.success("¡Inventario actualizado con éxito!")
    st.rerun()

# --- VISTAS ---

def login_seccion():
    st.title("👋 ¡Bienvenido a tu Panini Tracker!")
    st.info("Gestiona tu álbum e intercambia con amigos. Inicia sesión a la izquierda ↖️")
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
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    total = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo = len(df[df['quantity'] > 0]) if not df.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso", f"{(tengo/total)*100:.1f}%")
    c2.metric("Pegadas", tengo)
    c3.metric("Faltantes", total - tengo)
    
    fig = px.pie(names=["Tengo", "Faltan"], values=[tengo, total-tengo], hole=0.5, 
                 color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title="Estado del Álbum")
    st.plotly_chart(fig, use_container_width=True)
    st.divider()
    st.subheader("Análisis Detallado")
    modo = st.radio("Ver estadísticas por:", ["Grupos", "Selección Específica", horizontal=True])
    if modo == "Grupos":
        opcion_grupo = st.selectbox("Selecciona un Grupo:", list(GRUPOS.keys()))
        equipos_del_grupo = GRUPOS[opcion_grupo]
        tengo_grupo = tengo_df[tengo_df['team_code'].isin(equipos_del_grupo)]
        total_grupo = sum([CONFIG_ALBUM.get(e, 20) + (1 if e=='FWC' else 0) for e in equipos_del_grupo])
        cant_tengo_g = len(tengo_grupo)
        cant_falta_g = total_grupo - cant_tengo_g
        
        col_pie, col_info = st.columns([2, 1])
        with col_pie:
            fig = px.pie(names=["Tengo", "Faltan"], values=[cant_tengo_g, cant_falta_g], hole=0.5,
                         color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title=f"Progreso {opcion_grupo}")
            st.plotly_chart(fig, use_container_width=True)
        with col_info:
            st.write(f"**Detalle del {opcion_grupo}:**")
            for e in equipos_del_grupo:
                t_e = len(tengo_df[tengo_df['team_code'] == e])
                total_e = CONFIG_ALBUM.get(e, 20) + (1 if e=='FWC' else 0)
                st.write(f"- {e}: {t_e}/{total_e} ({(t_e/total_e)*100:.0f}%)")

    else:
        opcion_sel = st.selectbox("Selecciona una Selección:", list(CONFIG_ALBUM.keys()))
        t_s = len(tengo_df[tengo_df['team_code'] == opcion_sel])
        total_s = CONFIG_ALBUM.get(opcion_sel, 20) + (1 if opcion_sel=='FWC' else 0)
        
        col_pie, col_info = st.columns([2, 1])
        with col_pie:
            fig = px.pie(names=["Tengo", "Faltan"], values=[t_s, total_s - t_s], hole=0.5,
                         color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title=f"Progreso {opcion_sel}")
            st.plotly_chart(fig, use_container_width=True)
        with col_info:
            st.metric(f"Avance {opcion_sel}", f"{(t_s/total_s)*100:.1f}%")
            st.write(f"Te faltan **{total_s - t_s}** estampas para completar esta sección.")

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
    st.title("🤝 Centro de Intercambios")
    tab1, tab2 = st.tabs(["Registro Visual", "Comparar con Amigo"])
    
    with tab1:
        st.write("Agrega las estampas a las listas y confirma el intercambio.")
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
                st.markdown(f'<span style="background:#14A8FD; color:white; padding:5px 10px; border-radius:15px; margin-right:5px; display:inline-block; margin-top:5px;">{item}</span>', unsafe_allow_html=True)
            if st.button("Limpiar recibidas"): st.session_state.carrito_recibir = []

        with col_r:
            st.subheader("📤 Entrego")
            c4, c5, c6 = st.columns([2,2,1])
            s_e = c4.selectbox("Equipo", list(CONFIG_ALBUM.keys()), key="se")
            n_e = (['00'] + [f'FWC{i}' for i in range(1, 20)] if s_e == 'FWC' else 
                   ([f'CC{i}' for i in range(1, 15)] if s_e == 'CC' else [f'{s_e}{i}' for i in range(1, 21)]))
            cod_e = c5.selectbox("Número", n_e, key="ne")
            if c6.button("➕", key="be"): st.session_state.carrito_entregar.append(cod_e)
            for item in st.session_state.carrito_entregar:
                st.markdown(f'<span style="background:#FF4B4B; color:white; padding:5px 10px; border-radius:15px; margin-right:5px; display:inline-block; margin-top:5px;">{item}</span>', unsafe_allow_html=True)
            if st.button("Limpiar entregas"): st.session_state.carrito_entregar = []
        
        st.divider()
        if st.button("🚀 Confirmar Intercambio Completo", use_container_width=True):
            procesar_intercambio_final()

    with tab2:
        st.info(f"Tu código: `{st.session_state.user.id}`")
        amigo = st.text_input("Código de tu amigo:")
        if amigo and amigo != st.session_state.user.id:
            try:
                res_yo = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
                df_yo = pd.DataFrame(res_yo.data)
                mis_tengo = set(df_yo[df_yo['quantity'] > 0]['sticker_code']) if not df_yo.empty else set()
                mis_repetidas = set(df_yo[df_yo['quantity'] > 1]['sticker_code']) if not df_yo.empty else set()

                res_amigo = supabase.table("user_stickers").select("*").eq("user_id", amigo).execute()
                df_amigo = pd.DataFrame(res_amigo.data)
                amigo_tengo = set(df_amigo[df_amigo['quantity'] > 0]['sticker_code']) if not df_amigo.empty else set()
                amigo_repetidas = set(df_amigo[df_amigo['quantity'] > 1]['sticker_code']) if not df_amigo.empty else set()

                c_a, c_b = st.columns(2)
                with c_a:
                    st.write("🎁 Él tiene para darte:")
                    for s in [r for r in amigo_repetidas if r not in mis_tengo]: st.success(f"✅ {s}")
                with c_b:
                    st.write("🤲 Tú tienes para darle:")
                    for s in [r for r in mis_repetidas if r not in amigo_tengo]: st.warning(f"💎 {s}")
            except: st.error("Código no encontrado.")

def mostrar_exportar():
    st.title("📥 Exportar Datos")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df_db = pd.DataFrame(res.data)
    
    # Faltantes
    pegadas = set(df_db[df_db['quantity'] > 0]['sticker_code']) if not df_db.empty else set()
    faltantes = []
    for team, total in CONFIG_ALBUM.items():
        rango = (['00'] + [f'FWC{i}' for i in range(1, 20)] if team == 'FWC' else 
                 ([f'CC{i}' for i in range(1, 15)] if team == 'CC' else [f'{team}{i}' for i in range(1, 21)]))
        for c in rango:
            if c not in pegadas: faltantes.append({"Selección": team, "Código": c})
    
    df_f = pd.DataFrame(faltantes)

    # Repetidas
    if not df_db.empty:
        df_r = df_db[df_db['quantity'] > 1].copy()
        df_r['Cantidad Extra'] = df_r['quantity'] - 1
        df_r = df_r[['team_code', 'sticker_code', 'Cantidad Extra']].rename(columns={'team_code': 'Selección', 'sticker_code': 'Código'})
    else:
        df_r = pd.DataFrame(columns=["Selección", "Código", "Cantidad Extra"])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚩 Mis Faltantes")
        st.dataframe(df_f, use_container_width=True)
        st.download_button("Descargar Faltantes (CSV)", df_f.to_csv(index=False), "faltantes.csv", "text/csv")
    with col2:
        st.subheader("💎 Mis Repetidas")
        st.dataframe(df_r, use_container_width=True)
        st.download_button("Descargar Repetidas (CSV)", df_r.to_csv(index=False), "repetidas.csv", "text/csv")

def mostrar_ajustes():
    st.title("⚙️ Ajustes")
    with st.form("pass"):
        st.subheader("Cambiar Contraseña")
        n = st.text_input("Nueva Contraseña", type="password")
        if st.form_submit_button("Actualizar"):
            supabase.auth.update_user({"password": n})
            st.success("Contraseña actualizada.")
    st.divider()
    if st.button("Eliminar todos mis datos"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    st.sidebar.button("Cerrar Sesión", on_click=callback_logout)
    m = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    
    if m == "🏠 Resumen": mostrar_resumen()
    elif m == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
    elif m == "🤝 Intercambios": mostrar_intercambios()
    elif m == "📥 Exportar": mostrar_exportar()
    else: mostrar_ajustes()
