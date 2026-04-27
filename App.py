import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime

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

st.set_page_config(page_title="Danna's Panini Hub", layout="wide")

# --- FUNCIONES DE INVENTARIO ---
def actualizar_cantidad(codigo, sigla, nueva_cant):
    if nueva_cant < 0: return
    try:
        data = {"user_id": st.session_state.user.id, "sticker_code": codigo, "team_code": sigla, "quantity": nueva_cant}
        supabase.table("user_stickers").upsert(data, on_conflict="user_id,sticker_code").execute()
    except Exception as e:
        st.error(f"Error: {e}")

def procesar_intercambio_logico(recibidas, entregadas):
    # Esta función recorre las listas y actualiza la base de datos
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    inv = {item['sticker_code']: (item['quantity'], item['team_code']) for item in res.data}
    
    # Procesar Recibidas (Sumar)
    for cod in recibidas:
        cod = cod.strip().upper()
        if cod:
            actual, team = inv.get(cod, (0, cod[:3] if cod != '00' else 'FWC'))
            actualizar_cantidad(cod, team, actual + 1)
            
    # Procesar Entregadas (Restar)
    for cod in entregadas:
        cod = cod.strip().upper()
        if cod:
            actual, team = inv.get(cod, (0, cod[:3] if cod != '00' else 'FWC'))
            if actual > 0:
                actualizar_cantidad(cod, team, actual - 1)
            else:
                st.warning(f"No tenías la estampa {cod} para entregar, se ignoró esa resta.")
    
    st.success("¡Inventario actualizado con éxito!")
    st.rerun()

# --- VISTAS ---

def login_seccion():
    st.title("👋 Panini Tracker")
    st.sidebar.title("🔐 Acceso")
    email = st.sidebar.text_input("Correo")
    passw = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": passw})
            st.session_state.user = res.user
            st.rerun()
        except: st.error("Error en datos")

def mostrar_intercambios():
    tab1, tab2 = st.tabs(["Comparar con Amigo", "📝 Registrar Nuevo Intercambio"])
    
    with tab1:
        st.subheader("🤝 Comparador")
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

    with tab2:
        st.subheader("Registro Manual")
        st.write("Escribe los códigos separados por comas (ejemplo: ARG1, MEX5, 00)")
        
        with st.form("form_intercambio"):
            recibidas = st.text_input("📥 Estampas que RECIBISTE:")
            entregadas = st.text_input("📤 Estampas que ENTREGASTE:")
            
            if st.form_submit_button("Confirmar Intercambio"):
                list_rec = recibidas.split(",") if recibidas else []
                list_ent = entregadas.split(",") if entregadas else []
                procesar_intercambio_logico(list_rec, list_ent)

def mostrar_ajustes():
    st.title("⚙️ Ajustes")
    
    # 🔐 REINTEGRADO: CAMBIAR CONTRASEÑA
    st.subheader("🔐 Seguridad")
    with st.form("cambio_pass"):
        nueva = st.text_input("Nueva contraseña", type="password")
        confirmar = st.text_input("Confirmar nueva contraseña", type="password")
        if st.form_submit_button("Actualizar Contraseña"):
            if nueva == confirmar and len(nueva) >= 6:
                try:
                    supabase.auth.update_user({"password": nueva})
                    st.success("¡Contraseña actualizada correctamente!")
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")
            else:
                st.error("Las contraseñas no coinciden o son muy cortas (mínimo 6 caracteres).")
                
    st.divider()
    st.subheader("🗑️ Datos")
    if st.button("Eliminar todos mis datos"):
        supabase.table("user_stickers").delete().eq("user_id", st.session_state.user.id).execute()
        st.success("Datos borrados."); st.rerun()

# (Las funciones mostrar_resumen, mostrar_seccion_dinamica, mostrar_exportar se mantienen igual)

# --- NAVEGACIÓN PRINCIPAL ---
if st.session_state.user is None:
    login_seccion()
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    if st.sidebar.button("Cerrar Sesión"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
    
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    
    if menu == "🏠 Resumen": mostrar_resumen()
    elif menu == "🚩 Selecciones": mostrar_seccion_dinamica(st.sidebar.selectbox("Equipo", list(CONFIG_ALBUM.keys())))
    elif menu == "🤝 Intercambios": mostrar_intercambios()
    elif menu == "📥 Exportar": mostrar_exportar()
    else: mostrar_ajustes()
