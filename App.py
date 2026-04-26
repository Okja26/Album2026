import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. CONFIGURACIÓN DE CONEXIÓN
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- REFUERZO DE SESIÓN (ESTO QUITA EL DOBLE CLIC) ---
# Intentamos obtener la sesión activa de Supabase antes de que Streamlit haga nada
if 'user' not in st.session_state:
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            st.session_state.user = session.user
        else:
            st.session_state.user = None
    except:
        st.session_state.user = None

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

# --- FUNCIONES DE BASE DE DATOS ---

def actualizar_cantidad(codigo, sigla, nueva_cant):
    if nueva_cant < 0: return
    try:
        data = {"user_id": st.session_state.user.id, "sticker_code": codigo, "team_code": sigla, "quantity": nueva_cant}
        supabase.table("user_stickers").upsert(data).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Error al actualizar: {e}")

def obtener_datos_usuario():
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    return pd.DataFrame(res.data)

# --- COMPONENTES DE SEGURIDAD ---

def formulario_nueva_clave():
    st.markdown("### 🔐 Restablecer Contraseña")
    with st.form("reset_pass_form_final", clear_on_submit=True):
        n_pass = st.text_input("Nueva Contraseña", type="password")
        c_pass = st.text_input("Confirmar Contraseña", type="password")
        submit = st.form_submit_button("Actualizar Contraseña Ahora", use_container_width=True)
        if submit:
            if n_pass == c_pass and len(n_pass) >= 6:
                try:
                    supabase.auth.update_user({"password": n_pass})
                    st.query_params.clear()
                    st.success("¡Contraseña actualizada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Las contraseñas no coinciden o son cortas.")

def login_seccion():
    st.sidebar.title("🔐 Acceso")
    tipo = st.sidebar.radio("Acción", ["Iniciar Sesión", "Registrarse"])
    email = st.sidebar.text_input("Correo")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if tipo == "Iniciar Sesión":
        if st.sidebar.button("Entrar", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state.user = res.user
                    st.rerun() # ESTO AHORA SÍ FUNCIONARÁ AL PRIMER CLIC
            except:
                st.sidebar.error("Credenciales incorrectas.")
        
        if st.sidebar.button("¿Olvidaste tu contraseña?"):
            if email:
                try:
                    supabase.auth.reset_password_for_email(email)
                    st.sidebar.success("Enlace enviado.")
                except: st.sidebar.error("Límite de correos excedido.")
    else:
        if st.sidebar.button("Crear Cuenta", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("Cuenta creada. ¡Inicia sesión!")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

# --- VISTAS ---

def mostrar_resumen():
    st.title("🏆 Mi Progreso Global")
    df_actual = obtener_datos_usuario()
    total_cromos = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo_df = df_actual[df_actual['quantity'] > 0] if not df_actual.empty else pd.DataFrame()
    m1, m2, m3 = st.columns(3)
    progreso = (len(tengo_df)/total_cromos)*100 if total_cromos > 0 else 0
    m1.metric("Avance", f"{progreso:.2f}%")
    m2.metric("Tengo", len(tengo_df))
    m3.metric("Faltan", total_cromos - len(tengo_df))

def mostrar_seccion_dinamica(sigla):
    st.title(f"⚽ Selección: {sigla}")
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).eq("team_code", sigla).execute()
    inventario = {item['sticker_code']: item['quantity'] for item in res.data}
    codigos = ['00'] + [f'FWC{i}' for i in range(1, 20)] if sigla == 'FWC' else ([f'CC{i}' for i in range(1, 15)] if sigla == 'CC' else [f'{sigla}{i}' for i in range(1, 21)])
    cols = st.columns(4)
    for idx, cod in enumerate(codigos):
        cant = inventario.get(cod, 0)
        color = COLORS["Falta"] if cant == 0 else (COLORS["Tengo"] if cant == 1 else COLORS["Repetida"])
        with cols[idx % 4]:
            st.markdown(f'<div style="border:3px solid {color}; border-radius:10px; padding:10px; text-align:center; background:rgba(255,255,255,0.05);"><h3>{cod}</h3><p>Cant: {cant}</p></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("➖", key=f"m_{cod}", use_container_width=True): actualizar_cantidad(cod, sigla, cant - 1)
            if c2.button("➕", key=f"p_{cod}", use_container_width=True): actualizar_cantidad(cod, sigla, cant + 1)

def mostrar_intercambios():
    st.title("🤝 Intercambios")
    st.info(f"Tu código personal: `{st.session_state.user.id}`")
    amigo = st.text_input("Código de tu amigo:")
    if amigo and amigo != st.session_state.user.id:
        try:
            mis_tengo = set(obtener_datos_usuario().query("quantity > 0")['sticker_code'])
            res = supabase.table("user_stickers").select("*").eq("user_id", amigo).gt("quantity", 1).execute()
            matches = [f for f in res.data if f['sticker_code'] not in mis_tengo]
            if matches:
                st.success(f"¡Tiene {len(matches)} que necesitas!")
                for m in matches: st.button(f"{m['sticker_code']} ({m['team_code']})", key=f"btn_{m['sticker_code']}", disabled=True)
            else: st.info("No hay coincidencias.")
        except: st.error("No se encontró al amigo.")

def mostrar_ajustes():
    st.title("⚙️ Ajustes de Cuenta")
    formulario_nueva_clave()
    st.divider()
    conf = st.text_input("Escribe 'BORRAR TODO' para confirmar:")
    if st.button("Eliminar mis datos"):
        if conf == "BORRAR TODO":
            supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
            st.rerun()

# --- LÓGICA PRINCIPAL ---

st.markdown("""<script>if(window.location.hash.includes('type=recovery')){window.location.search = '?recovery=true';}</script>""", unsafe_allow_html=True)

if not st.session_state.user:
    login_seccion()
else:
    is_recovery = st.query_params.get("recovery") == "true" or st.query_params.get("type") == "recovery"
    if is_recovery:
        formulario_nueva_clave()
        if st.button("Regresar"):
            st.query_params.clear()
            st.rerun()
    else:
        st.sidebar.write(f"Usuario: {st.session_state.user.email}")
        if st.sidebar.button("Cerrar Sesión"): 
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()
        
        menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "⚙️ Ajustes"])
        if menu == "🏠 Resumen": mostrar_resumen()
        elif menu == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
        elif menu == "🤝 Intercambios": mostrar_intercambios()
        else: mostrar_ajustes()
