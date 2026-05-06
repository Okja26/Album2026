import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import io

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

ORDEN_SELECCIONES = list(CONFIG_ALBUM.keys())

GRUPOS = {
    "Grupo A": ['MEX', 'RSA', 'KOR', 'CZE'],
    "Grupo B": ['CAN', 'BIH', 'QAT', 'SUI'],
    "Grupo C": ['BRA', 'MAR', 'HAI', 'SCO'],
    "Grupo D": ['USA', 'PAR', 'AUS', 'TUR']
}

COLORS = {"Falta": "#FF4B4B", "Tengo": "#14A8FD", "Repetida": "#51D153"}

st.set_page_config(page_title="Panini Hub", layout="wide")

# --- FUNCIONES DE LÓGICA ---

def actualizar_db(lista_codigos, operacion):
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    inv = {item['sticker_code']: (item['quantity'], item['team_code']) for item in res.data}
    for cod in lista_codigos:
        equipo_sigla = "".join([c for c in cod if c.isalpha()]) if cod != '00' else 'FWC'
        actual, team = inv.get(cod, (0, equipo_sigla))
        nueva_cant = actual + 1 if operacion == "sumar" else max(0, actual - 1)
        supabase.table("user_stickers").upsert({
            "user_id": st.session_state.user.id, "sticker_code": cod, "team_code": team, "quantity": nueva_cant
        }, on_conflict="user_id,sticker_code").execute()

def callback_logout():
    supabase.auth.sign_out()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state.user = None
    st.rerun()

def obtener_orden_numerico(codigo):
    num = "".join([c for c in codigo if c.isdigit()])
    return int(num) if num else 0

def ordenar_dataframe_panini(df):
    if df.empty: return df
    df['sel_idx'] = df['Selección'].apply(lambda x: ORDEN_SELECCIONES.index(x) if x in ORDEN_SELECCIONES else 999)
    df['num_idx'] = df['Código'].apply(obtener_orden_numerico)
    df_sorted = df.sort_values(by=['sel_idx', 'num_idx']).drop(columns=['sel_idx', 'num_idx'])
    return df_sorted

def preparar_excel(df_faltantes, df_repetidas):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        ordenar_dataframe_panini(df_faltantes).to_excel(writer, sheet_name='Faltantes', index=False)
        ordenar_dataframe_panini(df_repetidas).to_excel(writer, sheet_name='Repetidas', index=False)
    return output.getvalue()

# --- VISTAS ---

def mostrar_resumen():
    st.title("📊 Estadísticas de Mi Álbum")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    if not res.data:
        tengo_df = pd.DataFrame(columns=['team_code', 'sticker_code', 'quantity'])
    else:
        df_db = pd.DataFrame(res.data)
        tengo_df = df_db[df_db['quantity'] > 0]

    completadas = 0
    for team, total_req in CONFIG_ALBUM.items():
        count_tengo = len(tengo_df[tengo_df['team_code'] == team])
        total_necesario = total_req + (1 if team == 'FWC' else 0)
        if count_tengo >= total_necesario:
            completadas += 1

    total_album = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    cant_tengo = len(tengo_df)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Progreso Total", f"{(cant_tengo/total_album)*100:.1f}%")
    c2.metric("Estampas Pegadas", cant_tengo)
    c3.metric("Faltantes", total_album - cant_tengo)
    c4.metric("Selecciones Completas", f"{completadas}/{len(CONFIG_ALBUM)}")
    
    st.divider()
    modo = st.radio("Analizar por:", ["Grupos", "Selección Específica"], horizontal=True)
    
    if modo == "Grupos":
        op_g = st.selectbox("Selecciona un Grupo:", list(GRUPOS.keys()))
        equipos = GRUPOS[op_g]
        t_g = len(tengo_df[tengo_df['team_code'].isin(equipos)])
        tot_g = sum([CONFIG_ALBUM.get(e, 20) + (1 if e=='FWC' else 0) for e in equipos])
        cp, ci = st.columns([2, 1])
        with cp:
            fig = px.pie(names=["Tengo", "Faltan"], values=[t_g, tot_g - t_g], hole=0.5,
                         color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title=f"Progreso {op_g}")
            st.plotly_chart(fig, use_container_width=True)
        with ci:
            for e in equipos:
                count = len(tengo_df[tengo_df['team_code'] == e])
                total_e = CONFIG_ALBUM.get(e, 20) + (1 if e=='FWC' else 0)
                st.write(f"- {e}: {count}/{total_e} ({(count/total_e)*100:.0f}%)")
    else:
        op_s = st.selectbox("Selecciona una Selección:", list(CONFIG_ALBUM.keys()))
        t_s = len(tengo_df[tengo_df['team_code'] == op_s])
        total_s = CONFIG_ALBUM.get(op_s, 20) + (1 if op_s=='FWC' else 0)
        fig = px.pie(names=["Tengo", "Faltan"], values=[t_s, total_s - t_s], hole=0.5,
                     color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]], title=f"Progreso {op_s}")
        st.plotly_chart(fig)

def vista_intercambios():
    st.title("🤝 Centro de Intercambios")
    t1, t2 = st.tabs(["🔄 Registro de Intercambio", "🔍 Comparar con Amigo"])
    
    with t1:
        res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        col_recibo, col_entrego = st.columns(2)
        
        # --- COLUMNA RECIBO (Doble método) ---
        with col_recibo:
            st.subheader("📥 Recibo (Me dan)")
            with st.expander("Método 1: Selección manual", expanded=True):
                eq_r = st.selectbox("Equipo", ORDEN_SELECCIONES, key="er")
                nums_r = (['00'] + [f'FWC{i}' for i in range(1, 20)] if eq_r == 'FWC' else ([f'CC{i}' for i in range(1, 15)] if eq_r == 'CC' else [f'{eq_r}{i}' for i in range(1, 21)]))
                cod_r = st.selectbox("Estampa", nums_r, key="cr")
                if st.button("➕ Añadir Selección", key="btn_r_sel"):
                    st.session_state.carrito_recibir.append(cod_r); st.rerun()
            
            with st.expander("Método 2: Lista de códigos"):
                man_r = st.text_input("Códigos (ej: ARG1, MEX5):", key="man_r")
                if st.button("➕ Añadir Lista", key="btn_r_man"):
                    st.session_state.carrito_recibir.extend([x.strip().upper() for x in man_r.split(",") if x]); st.rerun()

            for i, item in enumerate(st.session_state.carrito_recibir):
                ct, cd = st.columns([4, 1])
                ct.markdown(f'<span style="background:#14A8FD; color:white; padding:5px 10px; border-radius:15px; display:inline-block; margin:2px;">✅ {item}</span>', unsafe_allow_html=True)
                if cd.button("🗑️", key=f"dr_{i}"): st.session_state.carrito_recibir.pop(i); st.rerun()

        # --- COLUMNA ENTREGO (Doble método + Apartados) ---
        with col_entrego:
            st.subheader("📤 Entrego (Yo doy)")
            with st.expander("Método 1: Selección manual", expanded=True):
                eq_e = st.selectbox("Equipo", ORDEN_SELECCIONES, key="ee")
                nums_e = (['00'] + [f'FWC{i}' for i in range(1, 20)] if eq_e == 'FWC' else ([f'CC{i}' for i in range(1, 15)] if eq_e == 'CC' else [f'{eq_e}{i}' for i in range(1, 21)]))
                cod_e = st.selectbox("Estampa", nums_e, key="ce")
                if st.button("➕ Añadir Selección", key="btn_e_sel"):
                    st.session_state.carrito_entregar.append(cod_e); st.rerun()

            with st.expander("Método 2: Lista de códigos"):
                man_e = st.text_input("Códigos (ej: BRA2, GER19):", key="man_e")
                if st.button("➕ Añadir Lista", key="btn_e_man"):
                    st.session_state.carrito_entregar.extend([x.strip().upper() for x in man_e.split(",") if x]); st.rerun()

            if not df_inv.empty and 'reserved_to' in df_inv.columns:
                amigos = [a for a in df_inv['reserved_to'].unique() if a]
                if amigos:
                    st.divider()
                    amigo_sel = st.selectbox("Cargar apartados de:", amigos)
                    if st.button(f"Cargar apartados de {amigo_sel}"):
                        st.session_state.carrito_entregar.extend(df_inv[df_inv['reserved_to'] == amigo_sel]['sticker_code'].tolist()); st.rerun()

            for i, item in enumerate(st.session_state.carrito_entregar):
                ct, cd = st.columns([4, 1])
                ct.markdown(f'<span style="background:#FF4B4B; color:white; padding:5px 10px; border-radius:15px; display:inline-block; margin:2px;">💎 {item}</span>', unsafe_allow_html=True)
                if cd.button("🗑️", key=f"de_{i}"): st.session_state.carrito_entregar.pop(i); st.rerun()

        st.divider()
        if st.button("🚀 Confirmar e Impactar Álbum", use_container_width=True):
            if not st.session_state.carrito_recibir and not st.session_state.carrito_entregar:
                st.error("Los carritos están vacíos.")
            else:
                actualizar_db(st.session_state.carrito_recibir, "sumar")
                actualizar_db(st.session_state.carrito_entregar, "restar")
                st.session_state.carrito_recibir, st.session_state.carrito_entregar = [], []
                st.success("¡El álbum ha sido actualizado correctamente!"); st.rerun()

    with t2:
        st.subheader("🔍 Comparar con Amigo")
        st.info(f"Tu ID: `{st.session_state.user.id}`")
        id_amigo = st.text_input("ID del Amigo:")
        if id_amigo and id_amigo != st.session_state.user.id:
            try:
                res_yo = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
                df_yo = pd.DataFrame(res_yo.data) if res_yo.data else pd.DataFrame()
                mis_tengo = set(df_yo[df_yo['quantity'] > 0]['sticker_code']) if not df_yo.empty else set()
                mis_rep = set(df_yo[df_yo['quantity'] > 1]['sticker_code']) if not df_yo.empty else set()
                res_amigo = supabase.table("user_stickers").select("*").eq("user_id", id_amigo).execute()
                df_amigo = pd.DataFrame(res_amigo.data)
                am_tengo, am_rep = set(df_amigo[df_amigo['quantity'] > 0]['sticker_code']), set(df_amigo[df_amigo['quantity'] > 1]['sticker_code'])
                c1, c2 = st.columns(2)
                with c1:
                    st.write("🎁 Él te da:")
                    for s in [x for x in am_rep if x not in mis_tengo]: st.success(f"✅ {s}")
                with c2:
                    st.write("🤲 Tú le das:")
                    for s in [x for x in mis_rep if x not in am_tengo]: st.warning(f"💎 {s}")
            except: st.error("ID no válido")

def mostrar_exportar():
    st.title("📥 Exportar a Excel")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df_db = pd.DataFrame(res.data)
    pegadas = set(df_db[df_db['quantity'] > 0]['sticker_code']) if not df_db.empty else set()
    faltantes = []
    for team, total in CONFIG_ALBUM.items():
        rango = (['00'] + [f'FWC{i}' for i in range(1, 20)] if team == 'FWC' else ([f'CC{i}' for i in range(1, 15)] if team == 'CC' else [f'{team}{i}' for i in range(1, 21)]))
        for c in rango:
            if c not in pegadas: faltantes.append({"Selección": team, "Código": c})
    df_f = ordenar_dataframe_panini(pd.DataFrame(faltantes))
    df_r = df_db[df_db['quantity'] > 1].copy() if not df_db.empty else pd.DataFrame()
    if not df_r.empty:
        df_r['Cantidad Extra'] = df_r['quantity'] - 1
        df_r = df_r[['team_code', 'sticker_code', 'Cantidad Extra']].rename(columns={'team_code': 'Selección', 'sticker_code': 'Código'})
    else: df_r = pd.DataFrame(columns=['Selección', 'Código', 'Cantidad Extra'])
    df_r = ordenar_dataframe_panini(df_r)
    excel_data = preparar_excel(df_f, df_r)
    st.download_button(label="📊 Descargar Excel Completo", data=excel_data, file_name="Album.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚩 Mis Faltantes")
        st.dataframe(df_f, use_container_width=True, height=400)
    with col2:
        st.subheader("💎 Mis Repetidas")
        st.dataframe(df_r, use_container_width=True, height=400)

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    st.title("👋 Panini Hub")
    st.sidebar.title("🔐 Acceso")
    em, pw = st.sidebar.text_input("Email"), st.sidebar.text_input("Pass", type="password")
    if st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": em, "password": pw})
            st.session_state.user = res.user; st.rerun()
        except: st.error("Error")
    if st.sidebar.button("Registrar"):
        try:
            res = supabase.auth.sign_up({"email": em, "password": pw})
            st.session_state.user = res.user; st.rerun()
        except: st.error("Error")
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    st.sidebar.button("Cerrar Sesión", on_click=callback_logout)
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    if menu == "🏠 Resumen": mostrar_resumen()
    elif menu == "🚩 Selecciones":
        sigla = st.sidebar.selectbox("Equipo", ORDEN_SELECCIONES)
        res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).eq("team_code", sigla).execute()
        inv = {item['sticker_code']: item['quantity'] for item in res.data}
        cods = (['00'] + [f'FWC{i}' for i in range(1, 20)] if sigla == 'FWC' else ([f'CC{i}' for i in range(1, 15)] if sigla == 'CC' else [f'{sigla}{i}' for i in range(1, 21)]))
        cols = st.columns(4)
        for i, c in enumerate(cods):
            cant = inv.get(c, 0)
            color = COLORS["Falta"] if cant == 0 else (COLORS["Tengo"] if cant == 1 else COLORS["Repetida"])
            with cols[i % 4]:
                st.markdown(f'<div style="border:3px solid {color}; border-radius:10px; padding:10px; text-align:center;"><h3>{c}</h3><p>Cant: {cant}</p></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("➖", key=f"m_{c}"): actualizar_db([c], "restar"); st.rerun()
                if c2.button("➕", key=f"p_{c}"): actualizar_db([c], "sumar"); st.rerun()
    elif menu == "🤝 Intercambios": vista_intercambios()
    elif menu == "📥 Exportar": mostrar_exportar()
    else:
        st.title("⚙️ Ajustes")
        with st.form("p"):
            n = st.text_input("Nueva Contraseña", type="password")
            if st.form_submit_button("Actualizar"): supabase.auth.update_user({"password": n}); st.success("OK")
        if st.button("Borrar Datos"): supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute(); st.rerun()
