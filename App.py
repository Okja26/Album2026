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

COLORS = {"Falta": "#FF4B4B", "Tengo": "#14A8FD", "Repetida": "#51D153", "Apartada": "#FFD700"}

st.set_page_config(page_title="Panini Hub 2026", layout="wide")

# --- FUNCIONES DE LÓGICA ---

def actualizar_apartado(cod, delta):
    # Obtener valor actual
    res = supabase.table("user_stickers").select("quantity, reserved").eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
    if res.data:
        actual_q = res.data[0]['quantity']
        actual_r = res.data[0]['reserved'] or 0
        nueva_r = actual_r + delta
        
        # Validar que no apartes más de lo que tienes como repetida (quantity - 1)
        if 0 <= nueva_r < actual_q:
            supabase.table("user_stickers").update({"reserved": nueva_r}).eq("user_id", st.session_state.user.id).eq("sticker_code", cod).execute()
            st.rerun()
        else:
            st.error("No puedes apartar la estampa principal o valores negativos.")

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

# --- VISTAS ---

def mostrar_resumen():
    st.title("📊 Resumen de Colección")
    st.markdown("""
    Bienvenido a tu panel de control. Aquí puedes ver el avance porcentual de tu álbum, 
    cuántas estampas has pegado y cuáles te faltan para completar la gloria mundialista.
    """)
    
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).execute()
    df = pd.DataFrame(res.data)
    total_album = sum([v + (1 if k=='FWC' else 0) for k, v in CONFIG_ALBUM.items()])
    tengo = len(df[df['quantity'] > 0]) if not df.empty else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Progreso Total", f"{(tengo/total_album)*100:.1f}%")
    c2.metric("Pegadas en Álbum", tengo)
    c3.metric("Faltantes", total_album - tengo)
    
    fig = px.pie(names=["Tengo", "Faltan"], values=[tengo, total_album-tengo], hole=0.5, 
                 color_discrete_sequence=[COLORS["Tengo"], COLORS["Falta"]])
    st.plotly_chart(fig, use_container_width=True)

def mostrar_repetidas_y_apartados():
    st.title("💎 Repetidas y Apartados")
    st.markdown("""
    En esta sección puedes gestionar tus estampas duplicadas. 
    **Apartar** una estampa te ayuda a marcar aquellas que ya prometiste a un amigo 
    para que no las cuentes en futuros intercambios.
    """)
    
    res = supabase.table("user_stickers").select("*").eq("user_id", st.session_state.user.id).gt("quantity", 1).execute()
    
    if not res.data:
        st.info("Aún no tienes estampas repetidas. ¡Sigue abriendo sobres!")
    else:
        df_rep = pd.DataFrame(res.data)
        for _, row in df_rep.iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                rep_disponibles = row['quantity'] - 1
                apartadas = row['reserved'] or 0
                
                col1.subheader(row['sticker_code'])
                col2.write(f"**Disponibles para cambio:** {rep_disponibles - apartadas}")
                col3.write(f"**Apartadas:** {apartadas}")
                
                with col4:
                    sub_c1, sub_c2 = st.columns(2)
                    if sub_c1.button("📌", key=f"ap_{row['sticker_code']}", help="Apartar una"):
                        actualizar_apartado(row['sticker_code'], 1)
                    if sub_c2.button("🗑️", key=f"unap_{row['sticker_code']}", help="Quitar de apartados"):
                        actualizar_apartado(row['sticker_code'], -1)
                st.divider()

def mostrar_seccion_dinamica(sigla):
    st.title(f"⚽ Selección: {sigla}")
    st.markdown(f"Gestiona las estampas correspondientes a **{sigla}**. Haz clic en **+** si conseguiste una o en **-** si te equivocaste.")
    
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

# --- NAVEGACIÓN ACTUALIZADA ---
if st.session_state.user is None:
    # (Aquí va tu función login_seccion ya existente)
    pass 
else:
    st.sidebar.write(f"👤 {st.session_state.user.email}")
    menu = st.sidebar.radio("Menú", ["🏠 Resumen", "🚩 Selecciones", "💎 Repetidas", "🤝 Intercambios", "📥 Exportar", "⚙️ Ajustes"])
    
    if menu == "🏠 Resumen":
        mostrar_resumen()
    elif menu == "🚩 Selecciones":
        equipo = st.sidebar.selectbox("Elegir Equipo", list(CONFIG_ALBUM.keys()))
        mostrar_seccion_dinamica(equipo)
    elif menu == "💎 Repetidas":
        mostrar_repetidas_y_apartados()
    elif menu == "🤝 Intercambios":
        # (Aquí va tu función mostrar_intercambios ya existente)
        pass
    elif menu == "📥 Exportar":
        # (Aquí va tu función mostrar_exportar ya existente)
        pass
    else:
        # (Ajustes)
        pass
