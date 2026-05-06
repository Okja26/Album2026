import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import io

# 1. CONEXIÓN A SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURACIÓN ---
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

# --- FUNCIONES DE AUTENTICACIÓN ---
def callback_login():
    email = st.session_state.get("email_input")
    password = st.session_state.get("pass_input")
    if email and password:
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                if "login_error" in st.session_state: del st.session_state.login_error
            else:
                st.session_state.login_error = "Credenciales incorrectas."
        except:
            st.session_state.login_error = "Error de conexión con el servidor."

def callback_signup():
    email = st.session_state.get("email_input")
    password = st.session_state.get("pass_input")
    if email and password:
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.success("¡Registro exitoso!")
            else:
                st.session_state.login_error = "No se pudo crear la cuenta."
        except:
            st.session_state.login_error = "Error al registrar."

# --- UTILIDADES ---
def obtener_codigos_por_equipo(sigla):
    if sigla == 'FWC': return ['00'] + [f'FWC{i}' for i in range(1, 20)]
    if sigla == 'CC': return [f'CC{i}' for i in range(1, 15)]
    return [f'{sigla}{i}' for i in range(1, 21)]

def actualizar_db(lista_codigos, operacion):
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    inv = {item['sticker_code']: (item['quantity'], item['team_code']) for item in res.data}
    for cod in lista_codigos:
        cod = cod.strip().upper()
        equipo_sigla = "".join([c for c in cod if c.isalpha()]) if cod != '00' else 'FWC'
        actual, team = inv.get(cod, (0, equipo_sigla))
        nueva_cant = actual + 1 if operacion == "sumar" else max(0, actual - 1)
        update_data = {"user_id": st.session_state.user.id, "sticker_code": cod, "team_code": team, "quantity": nueva_cant}
        if operacion == "restar":
            update_data["reserved"] = 0
            update_data["reserved_to"] = None
        supabase.table("user_stickers").upsert(update_data, on_conflict="user_id,sticker_code").execute()

def guardar_apartado(cod, delta, nombre=None, reset_all=False):
    if reset_all:
        supabase.table("user_stickers").update({"reserved": 0, "reserved_to": None}).eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
    else:
        res = supabase.table("user_stickers").select("quantity, reserved").eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
        if res.data:
            q, r = res.data[0]['quantity'], res.data[0]['reserved'] or 0
            nuevo_r = max(0, r + delta)
            if nuevo_r < q:
                supabase.table("user_stickers").update({"reserved": nuevo_r, "reserved_to": nombre if nuevo_r > 0 else None}).eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
    st.rerun()

# --- VISTAS ---
def login_seccion():
    st.title("👋 ¡Bienvenido a tu Panini Tracker!")
    st.markdown("Inicia sesión para sincronizar tu álbum y gestionar tus apartados.")
    
    if "login_error" in st.session_state:
        st.sidebar.error(st.session_state.login_error)

    tipo = st.sidebar.radio("¿Qué deseas hacer?", ["Iniciar Sesión", "Registrarse"])
    st.sidebar.text_input("Correo electrónico", key="email_input")
    st.sidebar.text_input("Contraseña", type="password", key="pass_input")
    
    if tipo == "Iniciar Sesión":
        st.sidebar.button("Entrar", on_click=callback_login, use_container_width=True)
    else:
        st.sidebar.button("Crear Cuenta", on_click=callback_signup, use_container_width=True)

def vista_resumen():
    st.title("📊 Resumen del Álbum")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    total = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo = len(df[df['quantity'] > 0]) if not df.empty else 0
    c1, c2, c3 = st.columns(3); c1.metric("Progreso", f"{(tengo/total)*100:.1f}%"); c2.metric("Tengo", tengo); c3.metric("Faltan", total - tengo)
    fig = px.pie(names=["Tengo", "Faltan"], values=[tengo, total-tengo], hole=0.5, color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]])
    st.plotly_chart(fig, use_container_width=True)

def vista_selecciones(sigla):
    st.title(f"⚽ Selección: {sigla}")
    st.info("🔴 Falta | 🔵 Tengo | 🟢 Repetida")
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

def mostrar_comparador_amigo():
    st.subheader("🔍 Comparador Inteligente de Estampas")
    st.write("Ingresa el código de un amigo para ver qué cambios pueden hacer.")
    
    # Mostrar tu propio ID para que sea fácil copiarlo y pasarlo
    st.info(f"Tu código para compartir: `{st.session_state.user.id}`")
    
    id_amigo = st.text_input("Código del amigo:", placeholder="Pega aquí el UUID de tu amigo")
    
    if id_amigo:
        if id_amigo == st.session_state.user.id:
            st.warning("⚠️ Este es tu propio código. ¡Busca el de un amigo!")
        else:
            try:
                # 1. Obtener MIS datos (Mis repetidas y lo que me falta)
                res_yo = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
                df_yo = pd.DataFrame(res_yo.data) if res_yo.data else pd.DataFrame(columns=['sticker_code', 'quantity'])
                
                # Mis repetidas: las que tienen cantidad > 1
                mis_repetidas = set(df_yo[df_yo['quantity'] > 1]['sticker_code'])
                # Lo que ya tengo (para saber qué me falta)
                mis_tengo = set(df_yo[df_yo['quantity'] > 0]['sticker_code'])

                # 2. Obtener los datos del AMIGO
                res_amigo = supabase.table("user_stickers").select("*").eq("user_id", id_amigo).execute()
                
                if not res_amigo.data:
                    st.error("❌ No se encontraron datos para ese código. Verifica que tu amigo haya iniciado sesión al menos una vez.")
                else:
                    df_amigo = pd.DataFrame(res_amigo.data)
                    
                    # Repetidas del amigo
                    amigo_repetidas = set(df_amigo[df_amigo['quantity'] > 1]['sticker_code'])
                    # Lo que el amigo ya tiene
                    amigo_tengo = set(df_amigo[df_amigo['quantity'] > 0]['sticker_code'])

                    # 3. Lógica de cruce (Match)
                    # Lo que yo tengo repetido y a él LE FALTA
                    le_sirven = [r for r in mis_repetidas if r not in amigo_tengo]
                    
                    # Lo que él tiene repetido y a mí ME FALTA
                    me_sirven = [r for r in amigo_repetidas if r not in mis_tengo]

                    st.divider()
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("### 🎁 Él te puede dar")
                        st.caption("Repetidas de él que tú no tienes")
                        if me_sirven:
                            for s in sorted(me_sirven):
                                st.success(f"✅ **{s}**")
                        else:
                            st.write("Nada por ahora... 😢")

                    with col2:
                        st.markdown("### 🤲 Tú le puedes dar")
                        st.caption("Tus repetidas que a él le faltan")
                        if le_sirven:
                            for s in sorted(le_sirven):
                                st.warning(f"💎 **{s}**")
                        else:
                            st.write("No tienes nada que le sirva. 💔")
                            
                    if me_sirven and le_sirven:
                        st.balloons()
                        st.info("💡 ¡Hay match de intercambio! Ambos tienen algo que el otro necesita.")

            except Exception as e:
                st.error(f"Ocurrió un error al comparar: {e}")

def vista_intercambios():
    st.title("🤝 Centro de Intercambios")
    st.write("Gestiona tus cambios: carga tus apartados automáticamente o añade estampas manualmente.")
    
    # Pestañas para separar el registro de la comparación
    t1, t2 = st.tabs(["🔄 Registro de Intercambio", "🔍 Comparar con Amigo"])
    
    with t1:
        # 1. Consultar inventario actual para manejar los apartados y nombres de amigos
        res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        
        cl, cr = st.columns(2)
        
        # --- COLUMNA IZQUIERDA: RECIBO (ENTRAN AL ÁLBUM) ---
        with cl:
            st.subheader("📥 Recibo")
            st.caption("Estampas que te dieron y vas a pegar")
            
            # Selectores para añadir una por una
            c_eq, c_num, c_add = st.columns([2, 2, 1])
            with c_eq:
                # Usamos la lista de equipos que ya tienes definida
                eq_r = st.selectbox("Equipo", list(CONFIG_ALBUM.keys()), key="eq_r_view")
            with c_num:
                # Generación dinámica de códigos según el equipo
                rango_r = (['00'] + [f'FWC{i}' for i in range(1, 20)] if eq_r == 'FWC' else 
                          ([f'CC{i}' for i in range(1, 15)] if eq_r == 'CC' else [f'{eq_r}{i}' for i in range(1, 21)]))
                cod_r = st.selectbox("Número", rango_r, key="cod_r_view")
            with c_add:
                st.write(" ") # Espaciador visual
                if st.button("➕", key="btn_add_rec"):
                    st.session_state.carrito_recibir.append(cod_r)
                    st.rerun()

            st.write("---")
            # Mostrar la lista de recibidas como "tarjetas"
            if st.session_state.carrito_recibir:
                for i, item in enumerate(st.session_state.carrito_recibir):
                    col_txt, col_del = st.columns([4, 1])
                    col_txt.markdown(f'<span style="background:#14A8FD; color:white; padding:5px 12px; border-radius:15px; display:inline-block; margin:2px; font-weight:bold;">✅ {item}</span>', unsafe_allow_html=True)
                    if col_del.button("🗑️", key=f"del_r_{i}"):
                        st.session_state.carrito_recibir.pop(i)
                        st.rerun()
            else:
                st.info("Lista de recibo vacía.")

        # --- COLUMNA DERECHA: ENTREGO (SALEN DEL ÁLBUM) ---
        with cr:
            st.subheader("📤 Entrego")
            st.caption("Estampas que diste o tenías apartadas")
            
            # Lógica especial de apartados (Liz, etc.)
            if not df_inv.empty and 'reserved_to' in df_inv.columns:
                # Obtenemos nombres únicos de personas que tienen apartados
                amigos_con_apartado = [a for a in df_inv['reserved_to'].unique() if a]
                if amigos_con_apartado:
                    st.write("**Cargar Apartados:**")
                    c_amigo, c_btn_am = st.columns([3, 1])
                    amigo_sel = c_amigo.selectbox("Amigo(a)", amigos_con_apartado, key="sel_amigo_res")
                    if c_btn_am.button("Cargar"):
                        estampas_apartadas = df_inv[df_inv['reserved_to'] == amigo_sel]['sticker_code'].tolist()
                        st.session_state.carrito_entregar.extend(estampas_apartadas)
                        st.rerun()
            
            st.write("**Entrada Manual:**")
            lista_txt = st.text_input("Códigos separados por comas:", placeholder="ej: MEX10, ARG1, 00")
            if st.button("Añadir a lista"):
                manuales = [x.strip().upper() for x in lista_txt.split(",") if x]
                st.session_state.carrito_entregar.extend(manuales)
                st.rerun()

            st.write("---")
            # Mostrar la lista de entregadas como "tarjetas"
            if st.session_state.carrito_entregar:
                for i, item in enumerate(st.session_state.carrito_entregar):
                    col_txt, col_del = st.columns([4, 1])
                    col_txt.markdown(f'<span style="background:#FF4B4B; color:white; padding:5px 12px; border-radius:15px; display:inline-block; margin:2px; font-weight:bold;">💎 {item}</span>', unsafe_allow_html=True)
                    if col_del.button("🗑️", key=f"del_e_{i}"):
                        st.session_state.carrito_entregar.pop(i)
                        st.rerun()
            else:
                st.info("Lista de entrega vacía.")

        # --- BOTÓN DE ACCIÓN FINAL ---
        st.divider()
        if st.button("🚀 CONFIRMAR INTERCAMBIO", use_container_width=True):
            if not st.session_state.carrito_recibir and not st.session_state.carrito_entregar:
                st.error("No hay estampas en ninguna lista para procesar.")
            else:
                with st.spinner("Sincronizando inventario con Supabase..."):
                    # 1. Sumar las recibidas
                    if st.session_state.carrito_recibir:
                        actualizar_db(st.session_state.carrito_recibir, "sumar")
                    
                    # 2. Restar las entregadas
                    if st.session_state.carrito_entregar:
                        actualizar_db(st.session_state.carrito_entregar, "restar")
                    
                    # 3. Limpiar estados y notificar
                    st.session_state.carrito_recibir = []
                    st.session_state.carrito_entregar = []
                    st.success("¡Álbum actualizado con éxito!")
                    st.balloons()
                    st.rerun()

    with t2:
        # Llamamos a la función de comparación que ya tienes
        mostrar_comparador_amigo()
        
def vista_intercambios():
    st.title("🤝 Centro de Intercambios")
    t1, t2 = st.tabs(["🔄 Registro", "🔍 Comparar"])
    with t1:
        res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
        df_inv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        cl, cr = st.columns(2)
        with cl:
            st.subheader("📥 Recibo")
            eq_r = st.selectbox("Equipo", ORDEN_EQUIPOS, key="eq_r")
            cod_r = st.selectbox("Estampa", obtener_codigos_por_equipo(eq_r), key="cod_r")
            if st.button("Añadir a Recibo"): st.session_state.carrito_recibir.append(cod_r)
            for i, item in enumerate(st.session_state.carrito_recibir):
                st.write(f"✅ {item}")
                if st.button("X", key=f"dr_{i}"): st.session_state.carrito_recibir.pop(i); st.rerun()
        with cr:
            st.subheader("📤 Entrego")
            if not df_inv.empty:
                amigos = df_inv[df_inv['reserved'] > 0]['reserved_to'].unique().tolist()
                if amigos:
                    amigo_sel = st.selectbox("Cargar apartados de:", [a for a in amigos if a], key="sel_amigo")
                    if st.button(f"Añadir todas las de {amigo_sel}"):
                        estampas = df_inv[df_inv['reserved_to'] == amigo_sel]['sticker_code'].tolist()
                        st.session_state.carrito_entregar.extend(estampas)
                        st.rerun()
            st.divider()
            lista_txt = st.text_input("Lista manual (comas):")
            if st.button("Añadir lista"):
                st.session_state.carrito_entregar.extend([x.strip().upper() for x in lista_txt.split(",") if x])
                st.rerun()
            for i, item in enumerate(st.session_state.carrito_entregar):
                st.write(f"💎 {item}")
                if st.button("X", key=f"de_{i}"): st.session_state.carrito_entregar.pop(i); st.rerun()
        if st.button("🚀 Confirmar Intercambio", use_container_width=True):
            actualizar_db(st.session_state.carrito_recibir, "sumar")
            actualizar_db(st.session_state.carrito_entregar, "restar")
            st.session_state.carrito_recibir, st.session_state.carrito_entregar = [], []
            st.success("¡Álbum actualizado!")
            st.rerun()

def vista_exportar():
    st.title("📥 Exportar Datos")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df_db = pd.DataFrame(res.data)
    quitar_apartados = st.toggle("Ocultar estampas apartadas", value=False)
    pegadas = set(df_db[df_db['quantity'] > 0]['sticker_code']) if not df_db.empty else set()
    faltantes = [{"Selección": t, "Código": c} for t in ORDEN_EQUIPOS for c in obtener_codigos_por_equipo(t) if c not in pegadas]
    df_f = pd.DataFrame(faltantes)
    repetidas = []
    if not df_db.empty:
        df_r_raw = df_db[df_db['quantity'] > 1].copy()
        df_r_raw['orden'] = df_r_raw['team_code'].apply(lambda x: ORDEN_EQUIPOS.index(x))
        df_r_raw = df_r_raw.sort_values(['orden', 'sticker_code'])
        for _, row in df_r_raw.iterrows():
            q_libre = (row['quantity'] - 1) - (row['reserved'] if quitar_apartados else 0)
            if q_libre > 0:
                repetidas.append({"Selección": row['team_code'], "Código": row['sticker_code'], "Cantidad Extra": int(q_libre)})
    df_r = pd.DataFrame(repetidas)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚩 Mis Faltantes"); st.dataframe(df_f, use_container_width=True)
    with col2:
        st.subheader("💎 Mis Repetidas"); st.dataframe(df_r, use_container_width=True)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_f.to_excel(writer, sheet_name='Faltantes', index=False)
        df_r.to_excel(writer, sheet_name='Repetidas', index=False)
    st.download_button(label="Descargar Excel (.xlsx)", data=buffer.getvalue(), file_name="Mi_Album_2026.xlsx")

def vista_ajustes():
    st.title("⚙️ Ajustes")
    if st.button("🗑️ Borrar todo mi progreso", type="primary"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    m = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "💎 Repetidas", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    if m == "🏠 Resumen": vista_resumen()
    elif m == "🚩 Selecciones": vista_selecciones(st.sidebar.selectbox("Equipo", ORDEN_EQUIPOS))
    elif m == "💎 Repetidas": vista_repetidas()
    elif m == "🤝 Intercambios": vista_intercambios()
    elif m == "📥 Exportar": vista_exportar()
    elif m == "⚙️ Ajustes": vista_ajustes()
    if st.sidebar.button("Cerrar Sesión"): 
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
