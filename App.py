import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. CONEXIÓN A SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURACIÓN Y ORDEN OFICIAL ---
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
ORDEN_EQUIPOS = list(CONFIG_ALBUM.keys())
COLORS = {"Falta": "#FF4B4B", "Tengo": "#14A8FD", "Repetida": "#51D153"}

st.set_page_config(page_title="Panini Hub 2026", layout="wide")

# --- ESTADO DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'carrito_recibir' not in st.session_state: st.session_state.carrito_recibir = []
if 'carrito_entregar' not in st.session_state: st.session_state.carrito_entregar = []

# --- UTILIDADES ---
def obtener_codigos_por_equipo(sigla):
    if sigla == 'FWC': return ['00'] + [f'FWC{i}' for i in range(1, 20)]
    if sigla == 'CC': return [f'CC{i}' for i in range(1, 15)]
    return [f'{sigla}{i}' for i in range(1, 21)]

def actualizar_db(lista_codigos, operacion):
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    inv = {item['sticker_code']: (item['quantity'], item['team_code']) for item in res.data}
    for cod in lista_codigos:
        equipo_sigla = "".join([c for c in cod if c.isalpha()]) if cod != '00' else 'FWC'
        actual, team = inv.get(cod, (0, equipo_sigla))
        nueva_cant = actual + 1 if operacion == "sumar" else max(0, actual - 1)
        supabase.table("user_stickers").upsert({
            "user_id": st.session_state.user.id, "sticker_code": cod,
            "team_code": team, "quantity": nueva_cant
        }, on_conflict="user_id,sticker_code").execute()

def actualizar_apartado(cod, delta):
    res = supabase.table("user_stickers").select("quantity, reserved").eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
    if res.data:
        q, r = res.data[0]['quantity'], res.data[0]['reserved'] or 0
        if 0 <= r + delta < q:
            supabase.table("user_stickers").update({"reserved": r + delta}).eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
            st.rerun()

# --- VISTAS ---
def vista_resumen():
    st.title("📊 Resumen del Álbum")
    st.markdown("Consulta el progreso global de tu colección.")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    total = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo = len(df[df['quantity'] > 0]) if not df.empty else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso", f"{(tengo/total)*100:.1f}%")
    c2.metric("Tengo", tengo)
    c3.metric("Faltan", total - tengo)
    fig = px.pie(names=["Tengo", "Faltan"], values=[tengo, total-tengo], hole=0.5, color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]])
    st.plotly_chart(fig, use_container_width=True)

def vista_selecciones(sigla):
    st.title(f"⚽ Selección: {sigla}")
    st.info("Aqui puedes gestionar tus estampas: 🔴 Rojo: No la tengo | 🔵 Azul: Ya la conseguí | 🟢 Verde: Repetida")
    st.markdown(f"Gestiona las estampas de **{sigla}**.")
    codigos = obtener_codigos_por_equipo(sigla)
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).eq("team_code", sigla).execute()
    inv = {item['sticker_code']: item['quantity'] for item in res.data}
    cols = st.columns(4)
    for idx, cod in enumerate(codigos):
        cant = inv.get(cod, 0)
        color = COLORS["Falta"] if cant == 0 else (COLORS["Tengo"] if cant == 1 else COLORS["Repetida"])
        with cols[idx % 4]:
            st.markdown(f'<div style="border:2px solid {color}; padding:10px; border-radius:5px; text-align:center"><b>{cod}</b><br>Cant: {cant}</div>', unsafe_allow_html=True)
            ca, cb = st.columns(2)
            if ca.button("➖", key=f"m_{cod}"): actualizar_db([cod], "restar"); st.rerun()
            if cb.button("➕", key=f"p_{cod}"): actualizar_db([cod], "sumar"); st.rerun()

def vista_repetidas():
    st.title("💎 Mis Repetidas y Apartados")
    st.markdown("Gestiona tus repetidas Selecciona: 📌 para apartar tu estampa y 🗑️ para eliminarla de apartada")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).gt("quantity", 1).execute()
    if not res.data: st.info("No tienes repetidas actualmente.")
    else:
        df = pd.DataFrame(res.data)
        df['orden'] = df['team_code'].apply(lambda x: ORDEN_EQUIPOS.index(x))
        df = df.sort_values(['orden', 'sticker_code'])
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([1,2,2,1])
            c1.write(f"**{row['sticker_code']}**")
            c2.write(f"Libres: {(row['quantity']-1)-(row['reserved'] or 0)}")
            c3.write(f"Apartadas: {row['reserved'] or 0}")
            with c4:
                sub1, sub2 = st.columns(2)
                if sub1.button("📌", key=f"a_{row['sticker_code']}"): actualizar_apartado(row['sticker_code'], 1)
                if sub2.button("🗑️", key=f"d_{row['sticker_code']}"): actualizar_apartado(row['sticker_code'], -1)
            st.divider()

def vista_intercambios():
    st.title("🤝 Centro de Intercambios")
    st.markdown("Registra los intercambios que realices para actualizar tu album automaticamente")
    cl, cr = st.columns(2)
    with cl:
        st.subheader("📥 Recibo")
        eq_r = st.selectbox("Seleccionar Equipo", ORDEN_EQUIPOS, key="eq_r")
        cod_r = st.selectbox("Elegir Estampa", obtener_codigos_por_equipo(eq_r), key="cod_r")
        if st.button("Añadir a Recibo"): st.session_state.carrito_recibir.append(cod_r)
        st.write(st.session_state.carrito_recibir)
    with cr:
        st.subheader("📤 Entrego")
        eq_e = st.selectbox("Seleccionar Equipo ", ORDEN_EQUIPOS, key="eq_e")
        cod_e = st.selectbox("Elegir Estampa ", obtener_codigos_por_equipo(eq_e), key="cod_e")
        if st.button("Añadir a Entrega"): st.session_state.carrito_entregar.append(cod_e)
        st.write(st.session_state.carrito_entregar)
    if st.button("🚀 Ejecutar Intercambio", use_container_width=True):
        actualizar_db(st.session_state.carrito_recibir, "sumar")
        actualizar_db(st.session_state.carrito_entregar, "restar")
        st.session_state.carrito_recibir, st.session_state.carrito_entregar = [], []
        st.rerun()

def vista_exportar():
    st.title("📥 Exportar Datos")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df_db = pd.DataFrame(res.data)
    
    # 1. Faltantes Ordenadas
    pegadas = set(df_db[df_db['quantity'] > 0]['sticker_code']) if not df_db.empty else set()
    faltantes = []
    for team in ORDEN_EQUIPOS:
        for c in obtener_codigos_por_equipo(team):
            if c not in pegadas: faltantes.append({"Selección": team, "Código": c})
    df_f = pd.DataFrame(faltantes)
    
    # 2. Repetidas Ordenadas
    repetidas = []
    if not df_db.empty:
        df_r_raw = df_db[df_db['quantity'] > 1].copy()
        df_r_raw['orden'] = df_r_raw['team_code'].apply(lambda x: ORDEN_EQUIPOS.index(x))
        df_r_raw = df_r_raw.sort_values(['orden', 'sticker_code'])
        for _, row in df_r_raw.iterrows():
            repetidas.append({"Selección": row['team_code'], "Código": row['sticker_code'], "Cantidad Extra": row['quantity']-1})
    df_r = pd.DataFrame(repetidas)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚩 Mis Faltantes")
        st.dataframe(df_f, use_container_width=True)
        st.download_button("Descargar Faltantes (CSV)", df_f.to_csv(index=False), "faltantes.csv", "text/csv")
    with col2:
        st.subheader("💎 Mis Repetidas")
        st.dataframe(df_r, use_container_width=True)
        st.download_button("Descargar Repetidas (CSV)", df_r.to_csv(index=False), "repetidas.csv", "text/csv")

def vista_ajustes():
    st.title("⚙️ Ajustes de Cuenta")
    with st.form("perfil"):
        st.subheader("Seguridad")
        nueva_p = st.text_input("Nueva Contraseña", type="password")
        if st.form_submit_button("Actualizar Contraseña"):
            try:
                supabase.auth.update_user({"password": nueva_p})
                st.success("Contraseña actualizada.")
            except: st.error("Error al actualizar.")
    st.divider()
    if st.button("🗑️ Eliminar todos mis datos", type="primary"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.warning("Datos eliminados."); st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    st.title("Panini Tracker 2026")
    e = st.text_input("Email"); p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        res = supabase.auth.sign_in_with_password({"email": e, "password": p})
        if res.user: st.session_state.user = res.user; st.rerun()
else:
    m = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "💎 Repetidas", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    if m == "🏠 Resumen": vista_resumen()
    elif m == "🚩 Selecciones": vista_selecciones(st.sidebar.selectbox("Equipo", ORDEN_EQUIPOS))
    elif m == "💎 Repetidas": vista_repetidas()
    elif m == "🤝 Intercambios": vista_intercambios()
    elif m == "📥 Exportar": vista_exportar()
    elif m == "⚙️ Ajustes": vista_ajustes()
    if st.sidebar.button("Cerrar Sesión"): st.session_state.user = None; st.rerun()
