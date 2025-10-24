import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid
import gspread
import base64
from google.oauth2.service_account import Credentials

# ---------------- Config ----------------
st.set_page_config(page_title="Inter Maccabi Fantasy", page_icon="⚽", layout="wide")

JORNADA_ACTUAL = st.secrets.get("JORNADA_ACTUAL", "TEST")
SHEET_URL_ENTRADAS = st.secrets.get("SHEET_URL_ENTRADAS")
SHEET_ENTRADAS = st.secrets.get("SHEET_ENTRADAS", "Entradas")
PRESUPUESTO_MAX = 700  # límite de presupuesto

PRIMARY_BLUE = "#0033A0"
GOLD = "#FFD700"
TEXT_FAMILY = "JerseyM54, Bebas Neue, Arial Black, sans-serif"

# ---------------- Branding ----------------
LOGO_PATH = "logo.png"
st.markdown(
    f"<div style='text-align:center;'><img src='data:image/png;base64,{base64.b64encode(open(LOGO_PATH, 'rb').read()).decode()}' width='80'></div>", 
    unsafe_allow_html=True
)
st.markdown("<h1 style='color:#FFD700;text-align:center;'>⚔️ Inter Maccabi Fantasy ⚔️</h1>", unsafe_allow_html=True)

# ---------------- Datos ----------------
@st.cache_data
def load_convocados():
    """Carga la pestaña Convocados desde la hoja IM Fantasy"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(st.secrets["SHEET_URL_IMFANTASY"])   # Hoja IM Fantasy
    ws = sh.worksheet("Convocados")                         # pestaña Convocados
    rows = ws.get_values(value_render_option='UNFORMATTED_VALUE')
    df = pd.DataFrame(rows[1:], columns=rows[0])  # primera fila = encabezados
    return df

try:
    df = load_convocados()
except Exception as e:
    st.error(f"❌ No se pudo leer la pestaña 'Convocados' de la hoja IM Fantasy. Error: {e}")
    st.stop()

# ---------------- Limpieza y normalización ----------------
df.columns = [c.strip() for c in df.columns]

# Convierte ValorActual a float (admite comas o puntos)
df["ValorActual"] = (
    df["ValorActual"].astype(str)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

pos_col = "Posicion"

def _fmt_eu(val: float) -> str:
    return f"{val:.2f}".replace(".", ",")  # 100.35 -> "100,35"

def formato_opcion(row):
    nombre = str(row.get("Nombre","")).strip()
    equipo = str(row.get("Equipo","")).strip()
    valor  = float(row.get("ValorActual", 0.0))
    return f"{nombre}, {equipo}. ({_fmt_eu(valor)}€)"

# Filtrado por posiciones
porteros   = df[df[pos_col] == "Portero"]
defensas   = df[df[pos_col] == "Defensa"]
medios     = df[df[pos_col] == "Mediocentro"]
delanteros = df[df[pos_col] == "Delantero"]

# Diccionario nombre -> valor (para cálculos)
nombre_a_valor = dict(zip(df["Nombre"].astype(str), df["ValorActual"].astype(float)))

# ---------------- Helpers ----------------
def limpia_nombre(txt: str) -> str:
    if not txt:
        return ""
    name = str(txt).split(",")[0].strip()
    reemplazos = {"á":"a","Á":"A","é":"e","É":"E","í":"i","Í":"I","ó":"o","Ó":"O","ú":"u","Ú":"U"}
    for k,v in reemplazos.items():
        name = name.replace(k,v)
    return name

def font_size_for(name: str) -> int:
    L = len(name)
    if L <= 10: return 18
    if L <= 14: return 16
    if L <= 18: return 14
    return 12

def name_and_value(fig, x, y, full_txt):
    if not full_txt: return
    name = limpia_nombre(full_txt)
    valor = nombre_a_valor.get(name, 0.0)
    size = font_size_for(name)

    # Contorno del texto
    for dx, dy in [(-0.02,0),(0.02,0),(0,0.02),(0,-0.02)]:
        fig.add_trace(go.Scatter(
            x=[x+dx], y=[y+dy], mode="text",
            text=[f"<b>{name}</b>"],
            textfont=dict(family=TEXT_FAMILY, size=size, color="rgba(255,255,255,0.8)"),
            hoverinfo="skip", showlegend=False
        ))

    # Texto principal
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="text",
        text=[f"<b>{name}</b>"],
        textfont=dict(family=TEXT_FAMILY, size=size, color=PRIMARY_BLUE),
        hoverinfo="skip", showlegend=False
    ))

    # Valor encima
    fig.add_trace(go.Scatter(
        x=[x], y=[y+0.35], mode="text",
        text=[f"{_fmt_eu(valor)}€"],
        textfont=dict(family=TEXT_FAMILY, size=max(14,int(size*0.7)), color=GOLD),
        hoverinfo="skip", showlegend=False
    ))

# ---------------- UI dinámica ----------------
formacion = st.radio("🧭 Selecciona tu formación:", ["1-3-2-1","1-2-3-1","1-2-2-2"], horizontal=True)
usuario = st.text_input("👤 Tu nombre de usuario (obligatorio)")
jornada = st.text_input("📅 Jornada", value=JORNADA_ACTUAL, disabled=True)

# Portero
elegido_portero = st.selectbox("🧤 Portero", porteros.apply(formato_opcion, axis=1))

# Defensas
elegidos_defensas = []
st.markdown("### 🛡️ Defensas")
for i in range({"1-3-2-1":3, "1-2-3-1":2, "1-2-2-2":2}[formacion]):
    d = st.selectbox(f"Defensa {i+1}", defensas.apply(formato_opcion, axis=1), key=f"def{i}")
    elegidos_defensas.append(d)

# Mediocentros
elegidos_medios = []
st.markdown("### 🎯 Mediocentros")
for i in range({"1-3-2-1":2, "1-2-3-1":3, "1-2-2-2":2}[formacion]):
    m = st.selectbox(f"Mediocentro {i+1}", medios.apply(formato_opcion, axis=1), key=f"mc{i}")
    elegidos_medios.append(m)

# Delanteros
elegidos_delanteros = []
st.markdown("### ⚡ Delanteros")
for i in range({"1-3-2-1":1, "1-2-3-1":1, "1-2-2-2":2}[formacion]):
    dl = st.selectbox(f"Delantero {i+1}", delanteros.apply(formato_opcion, axis=1), key=f"dl{i}")
    elegidos_delanteros.append(dl)

# ---------------- Campo táctico ----------------
FORMACIONES_COORDS = {
    "1-3-2-1": {
        "Portero": [(3,1.2)],
        "Defensa": [(1.5,2.8),(3,2.5),(4.5,2.8)],
        "Mediocentro": [(2,4.0),(4,4.0)],
        "Delantero": [(3,6.0)]
    },
    "1-2-3-1": {
        "Portero": [(3,1.2)],
        "Defensa": [(2.2,2.5),(3.8,2.5)],
        "Mediocentro": [(1.5,4.3),(3,4.0),(4.5,4.3)],
        "Delantero": [(3,6.0)]
    },
    "1-2-2-2": {
        "Portero": [(3,1.2)],
        "Defensa": [(2.2,2.5),(3.8,2.5)],
        "Mediocentro": [(2,4.0),(4,4.0)],
        "Delantero": [(1.9,6.0),(4.1,6.0)]
    }
}

fig = go.Figure()
fig.add_shape(type="rect", x0=0, y0=0, x1=6, y1=8, line=dict(color="white", width=3))
fig.add_shape(type="rect", x0=1, y0=0, x1=5, y1=2, line=dict(color="white", width=2))
fig.update_layout(
    plot_bgcolor="#117A43",
    xaxis=dict(visible=False, range=[0,6]),
    yaxis=dict(visible=False, range=[0,8]),
    height=600,
    margin=dict(l=10, r=10, t=40, b=40),
    showlegend=False
)

# Colocar jugadores
coords = FORMACIONES_COORDS[formacion]
if elegido_portero: name_and_value(fig, coords["Portero"][0][0], coords["Portero"][0][1], elegido_portero)
for coord, j in zip(coords["Defensa"], elegidos_defensas): name_and_value(fig, coord[0], coord[1], j)
for coord, j in zip(coords["Mediocentro"], elegidos_medios): name_and_value(fig, coord[0], coord[1], j)
for coord, j in zip(coords["Delantero"], elegidos_delanteros): name_and_value(fig, coord[0], coord[1], j)

# ---- Presupuesto ----
jugadores_seleccionados = [elegido_portero] + elegidos_defensas + elegidos_medios + elegidos_delanteros
nombres_limpios = [limpia_nombre(j) for j in jugadores_seleccionados if j]
valor_equipo = sum(nombre_a_valor.get(n, 0.0) for n in nombres_limpios)
presu_restante = PRESUPUESTO_MAX - valor_equipo
warning = " ⚠️" if presu_restante < 0 else ""

fig.add_annotation(
    text=f"Valor Equipo: {_fmt_eu(valor_equipo)}€",
    xref="paper", yref="paper",
    x=0.25, y=0.02,
    showarrow=False,
    font=dict(family=TEXT_FAMILY, size=18, color="white"),
    bgcolor="black"
)
fig.add_annotation(
    text=f"Presupuesto: {_fmt_eu(presu_restante)}€{warning}",
    xref="paper", yref="paper",
    x=0.75, y=0.02,
    showarrow=False,
    font=dict(family=TEXT_FAMILY, size=18, color="white"),
    bgcolor="black"
)
st.plotly_chart(fig, use_container_width=True)

# ---------------- Envío ----------------
if st.button("🚀 Enviar Alineación"):
    if not usuario.strip():
        st.error("❌ Debes introducir tu usuario.")
        st.stop()

    # Validar duplicados
    if len(nombres_limpios) != len(set(nombres_limpios)):
        st.error("❌ No puedes repetir jugadores en la alineación.")
        st.stop()

    if valor_equipo > PRESUPUESTO_MAX:
        st.error("❌ Te pasas del presupuesto máximo permitido.")
        st.stop()

    alineacion_id = "AID" + str(uuid.uuid4())[:6]
    row = [alineacion_id, usuario, jornada] + nombres_limpios

    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(SHEET_URL_ENTRADAS)
        ws = sh.worksheet(SHEET_ENTRADAS)
        ws.append_row(row, value_input_option="USER_ENTERED")
        st.success("✅ Alineación recibida con éxito")
        st.balloons()
    except Exception as e:
        import traceback
        st.error("⚠️ Error escribiendo en Google Sheets")
        st.code(traceback.format_exc())
