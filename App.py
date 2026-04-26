import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. CONFIGURACIÓN DE CONEXIÓN (Secrets)
# Estas variables deben estar en .streamlit/secrets.toml o en los Secrets de Streamlit Cloud
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

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

# Colores personalizados (Rojo: Falta, Azul: Una, Verde: Repetida)
COLORS = {
    "Falta": "#FF4B4B",     
    "Tengo": "#14A8FD",     
    "Repetida": "#51D153",  
}

st.set_page_config(page_title="Danna's Panini Hub", layout="wide")

# --- FUNCIONES DE BASE DE DATOS ---

def actualizar_cantidad(codigo, sigla, nueva_cant):
    if nueva_cant < 0: return
    try:
        data = {
            "user_id": st.session_state.user.id,
            "sticker_code": codigo,
            "team_code": sigla,
            "quantity": nueva_cant
        }
        supabase.table("user_stickers").upsert(data).execute()
        st.rerun()
    except Exception as e:
        st.error(f"Error al actualizar: {e}")

def obtener_datos_usuario():
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    return pd.DataFrame(res.data)

# --- VISTAS DE LA APLICACIÓN ---

def login_seccion():
    st.sidebar.title("🔐 Acceso")
    tipo = st.sidebar.radio("Acción", ["Iniciar Sesión", "Registrarse"])
    email = st.sidebar.text_input("Correo")
    password = st.sidebar.text_input("Contraseña", type="password")
    
    if tipo == "Iniciar Sesión":
        if st.sidebar.button("Entrar", use_container_width=True):
            try:
                # 1. Intentar login
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                
                # 2. Guardar el usuario explícitamente en el estado
                if res.user:
                    st.session_state.user = res.user
                    # 3. Limpiar cualquier mensaje previo y forzar reinicio limpio
                    st.rerun()
            except Exception as e:
                # Si realmente hay un error, lo mostramos
                st.sidebar.error("Credenciales incorrectas. Revisa tu correo o contraseña.")
    else:
        if st.sidebar.button("Crear Cuenta", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.sidebar.success("¡Cuenta creada! Intenta iniciar sesión ahora.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

def mostrar_resumen():
    st.title("🏆 Mi Progreso Global")
    df_actual = obtener_datos_usuario()
    
    total_cromos = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo_df = df_actual[df_actual['quantity'] > 0] if not df_actual.empty else pd.DataFrame()
    total_tengo = len(tengo_df)
    
    m1, m2, m3 = st.columns(3)
    progreso = (total_tengo / total_cromos) * 100 if total_cromos > 0 else 0
    m1.metric("Avance Total", f"{progreso:.2f}%")
    m2.metric("Pegadas", total_tengo)
    m3.metric("Faltantes", total_cromos - total_tengo)
    
    st.divider()
    if not df_actual.empty:
        st.subheader("📋 Inventario Detallado")
        st.dataframe(df_actual[['sticker_code', 'team_code', 'quantity']], use_container_width=True)

def mostrar_seccion_dinamica(sigla):
    st.title(f"⚽ Selección: {sigla}")
    
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).eq("team_code", sigla).execute()
    inventario = {item['sticker_code']: item['quantity'] for item in res.data}

    if sigla == 'FWC': codigos = ['00'] + [f'FWC{i}' for i in range(1, 20)]
    elif sigla == 'CC': codigos = [f'CC{i}' for i in range(1, 15)]
    else: codigos = [f'{sigla}{i}' for i in range(1, 21)]

    cols = st.columns(4)
    for idx, cod in enumerate(codigos):
        col_actual = cols[idx % 4]
        cant = inventario.get(cod, 0)
        
        # Color del borde según reglas de Danna
        if cant == 0: color_tarjeta = COLORS["Falta"]
        elif cant == 1: color_tarjeta = COLORS["Tengo"]
        else: color_tarjeta = COLORS["Repetida"]

        with col_actual:
            st.markdown(f"""
                <div style="border: 3px solid {color_tarjeta}; border-radius: 12px; padding: 15px; margin-bottom: 5px; background-color: rgba(255, 255, 255, 0.05); text-align: center;">
                    <h2 style="color: {color_tarjeta}; margin: 0;">{cod}</h2>
                    <p style="margin: 5px 0;">Cantidad: <b>{cant}</b></p>
                </div>
                """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("➖", key=f"min_{cod}", use_container_width=True):
                actualizar_cantidad(cod, sigla, cant - 1)
            if c2.button("➕", key=f"plu_{cod}", use_container_width=True):
                actualizar_cantidad(cod, sigla, cant + 1)
            st.write("") 

def mostrar_intercambios():
    st.title("🤝 Centro de Intercambio")
    mi_id = st.session_state.user.id
    
    st.info(f"Tu código personal para compartir: `{mi_id}`")
    
    st.divider()
    codigo_amigo = st.text_input("Ingresa el código de tu amigo para ver qué tiene repetido:")
    
    if codigo_amigo:
        if codigo_amigo == mi_id:
            st.warning("¡Ese es tu propio código!")
        else:
            try:
                # Datos del usuario actual (lo que tengo)
                mis_datos = obtener_datos_usuario()
                mis_tengo = set(mis_datos[mis_datos['quantity'] > 0]['sticker_code']) if not mis_datos.empty else set()

                # Datos del amigo (solo repetidas > 1 por política RLS)
                res_amigo = supabase.table("user_stickers").select("*").eq("user_id", codigo_amigo).gt("quantity", 1).execute()
                df_amigo = pd.DataFrame(res_amigo.data)

                if not df_amigo.empty:
                    # Comparar: Repetidas de él que yo no tengo
                    df_amigo['necesaria'] = df_amigo['sticker_code'].apply(lambda x: x not in mis_tengo)
                    match = df_amigo[df_amigo['necesaria'] == True]

                    if not match.empty:
                        st.success(f"¡Tu amigo tiene {len(match)} estampas que te faltan!")
                        m_cols = st.columns(4)
                        for i, fila in match.reset_index().iterrows():
                            with m_cols[i % 4]:
                                st.markdown(f"""
                                    <div style="border: 2px solid {COLORS['Tengo']}; border-radius: 10px; padding: 10px; text-align: center;">
                                        <b style="color: {COLORS['Tengo']};">{fila['sticker_code']}</b><br>
                                        <small>{fila['team_code']}</small>
                                    </div>
                                    """, unsafe_allow_html=True)
                    else:
                        st.info("Tu amigo tiene repetidas, pero tú ya las tienes todas.")
                else:
                    st.warning("Este amigo no tiene repetidas disponibles.")
            except Exception as e:
                st.error("Error al buscar amigo. Revisa que el código sea correcto.")

# --- LÓGICA DE NAVEGACIÓN ---

if 'user' not in st.session_state:
    login_seccion()
    st.info("👋 Bienvenido. Inicia sesión para gestionar tu álbum.")
else:
    st.sidebar.success(f"Sesión: {st.session_state.user.email}")
    if st.sidebar.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()

    menu = st.sidebar.radio("Menú:", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios"])

    if menu == "🏠 Resumen":
        mostrar_resumen()
    elif menu == "🚩 Selecciones":
        equipo = st.sidebar.selectbox("Selecciona equipo:", list(CONFIG_ALBUM.keys()))
        mostrar_seccion_dinamica(equipo)
    else:
        mostrar_intercambios()
