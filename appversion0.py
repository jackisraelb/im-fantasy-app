import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid
import gspread
import numpy as np
import base64, os, unicodedata
from google.oauth2.service_account import Credentials

# ---------------- Config ----------------
st.set_page_config(page_title="Inter Maccabi Fantasy", page_icon="⚽", layout="wide")

JORNADA_ACTUAL = st.secrets.get("JORNADA_ACTUAL", "J1")
PRESUPUESTO_MAX = 700
SHEET_URL = st.secrets.get("SHEET_URL")
SHEET_ENTRADAS = st.secrets.get("SHEET_ENTRADAS", "Entradas")

PRIMARY_BLUE = "#0033A0"
GOLD = "#FFD700"
TEXT_FAMILY = "JerseyM54, Bebas Neue, Arial Black, sans-serif"

# ---------------- Branding ----------------
LOGO_PATH = "logo.png"
EXCEL_PATH = "IM_Fantasy.xlsx"

st.image(LOGO_PATH, use_column_width=False, width=150)
st.markdown("<h1 style='color:#FFD700;text-align:center;'>⚔️ Inter Maccabi Fantasy ⚔️</h1>", unsafe_allow_html=True)

# ---------------- Datos ----------------
@st.cache_data
def load_convocados(path):
    return pd.read_excel(path, sheet_name="Convocados")

try:
    df = load_convocados(EXCEL_PATH)
except Exception as e:
    st.error(f"❌ No se pudo leer {EXCEL_PATH}. Error: {e}")
    st.stop()

df.columns = [c.strip() for c in df.columns]
pos_col = "Posicion"

def formato_opcion(row):
        return f"{row['Nombre']}, {row['Equipo']}. ({row['ValorActual']}€)"

porteros   = df[df[pos_col] == "Portero"]
defensas   = df[df[pos_col] == "Defensa"]
medios     = df[df[pos_col] == "Mediocentro"]
delanteros = df[df[pos_col] == "Delantero"]

# ---------------- Helpers ----------------
import re

def extrae_valor(txt: str) -> int:
    """Extrae el valor numérico (en €) de un string tipo 'Nombre, Equipo. (100€)'"""
    if not txt:
        return 0
    match = re.search(r"\((\d+)€\)", str(txt))
    if match:
        return int(match.group(1))
    return 0


def limpia_nombre(txt: str) -> str:
    """Devuelve solo el nombre sin tildes"""
    if not txt:
        return ""
    name = str(txt).split(",")[0].strip()
    # quitar tildes manualmente
    name = (name.replace("á","a")
                .replace("Á","A")
                .replace("é","e")
                .replace("É","E")
                .replace("í","i")
                .replace("Í","I")
                .replace("ó","o")
                .replace("Ó","O")
                .replace("ú","u")
                .replace("Ú","U"))
    return name



def font_size_for(name: str) -> int:
    L = len(name)
    if L <= 10: return 26
    if L <= 14: return 24
    if L <= 18: return 22
    return 20

def line_xs(n, low, high):
    return list(np.linspace(low, high, n)) if n and n > 0 else []

def name_and_value(fig, x, y, full_txt):
    if not full_txt: return
    name = limpia_nombre(full_txt.split(" (", 1)[0])
    value = extrae_valor(full_txt)
    size = font_size_for(name)

    # contorno
    for dx, dy in [(-0.02,0), (0.02,0), (0,0.02), (0,-0.02)]:
        fig.add_trace(go.Scatter(
            x=[x+dx], y=[y+dy], mode="text",
            text=[f"<b>{name}</b>"],
            textfont=dict(family=TEXT_FAMILY, size=size, color="rgba(255,255,255,0.8)"),
            hoverinfo="skip", showlegend=False
        ))

    # texto principal
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="text",
        text=[f"<b>{name}</b>"],
        textfont=dict(family=TEXT_FAMILY, size=size, color=PRIMARY_BLUE),
        hoverinfo="skip", showlegend=False
    ))

    # valor
    if value is not None:
        fig.add_trace(go.Scatter(
            x=[x+0.9], y=[y-0.10], mode="text",
            text=[f"{value}€"],
            textfont=dict(family=TEXT_FAMILY, size=max(14, int(size*0.65)), color=GOLD),
            hoverinfo="skip", showlegend=False
        ))

# ---------------- UI dinámica ----------------
formacion = st.radio("🧭 Selecciona tu formación:", ["1-3-2-1","1-2-3-1","1-2-2-2"], horizontal=True)
usuario = st.text_input("👤 Tu nombre de usuario (obligatorio)")
jornada = st.text_input("📅 Jornada", value=JORNADA_ACTUAL, disabled=True)

elegido_portero = st.selectbox("🧤 Portero", porteros.apply(formato_opcion, axis=1))

elegidos_defensas, elegidos_medios, elegidos_delanteros = [], [], []

st.markdown("### 🛡️ Defensas")
for i in range({"1-3-2-1":3, "1-2-3-1":2, "1-2-2-2":2}[formacion]):
    d = st.selectbox(f"Defensa {i+1}", defensas.apply(formato_opcion, axis=1), key=f"def{i}")
    elegidos_defensas.append(d)

st.markdown("### 🎯 Mediocentros")
for i in range({"1-3-2-1":2, "1-2-3-1":3, "1-2-2-2":2}[formacion]):
    m = st.selectbox(f"Mediocentro {i+1}", medios.apply(formato_opcion, axis=1), key=f"mc{i}")
    elegidos_medios.append(m)

st.markdown("### ⚡ Delanteros")
for i in range({"1-3-2-1":1, "1-2-3-1":1, "1-2-2-2":2}[formacion]):
    dl = st.selectbox(f"Delantero {i+1}", delanteros.apply(formato_opcion, axis=1), key=f"dl{i}")
    elegidos_delanteros.append(dl)

# ---------------- Campo táctico ----------------

FORMACIONES_COORDS = {
    "1-3-2-1": {
        "Portero": [(3,1.2)],
        "Defensa": [(2,2.5),(3,2.5),(4,2.5)],
        "Mediocentro": [(2.3,4.0),(3.7,4.0)],
        "Delantero": [(3,6.0)]
    },
    "1-2-3-1": {
        "Portero": [(3,1.2)],
        "Defensa": [(2.5,2.5),(3.5,2.5)],
        "Mediocentro": [(2,4.0),(3,4.0),(4,4.0)],
        "Delantero": [(3,6.0)]
    },
    "1-2-2-2": {
        "Portero": [(3,1.2)],
        "Defensa": [(2.5,2.5),(3.5,2.5)],
        "Mediocentro": [(2.3,4.0),(3.7,4.0)],
        "Delantero": [(2.5,6.0),(3.5,6.0)]
    }
}

fig = go.Figure()

# Césped y área
fig.add_shape(type="rect", x0=0, y0=0, x1=6, y1=8, line=dict(color="white", width=3))
fig.add_shape(type="rect", x0=1, y0=0, x1=5, y1=2, line=dict(color="white", width=2))

fig.update_layout(
    plot_bgcolor="#117A43",
    xaxis=dict(visible=False, range=[0,6]),
    yaxis=dict(visible=False, range=[0,8]),
    height=800,
    margin=dict(l=20, r=20, t=20, b=120),
    showlegend=False,
    modebar=dict(remove=["zoom","pan","select","lasso2d","resetScale2d"], add=["toImage"])
)

# Logo y jornada
fig.add_layout_image(
    dict(
        source=LOGO_PATH,
        xref="paper", yref="paper",  # relativo al canvas
        x=0.02, y=0.98,  # esquina arriba izquierda
        sizex=0.15, sizey=0.15,
        xanchor="left", yanchor="top",
        layer="above"
    )
)
fig.add_trace(go.Scatter(
    x=[1.2], y=[7.7], mode="text",
    text=[f"Jornada {JORNADA_ACTUAL}"],
    textfont=dict(family=TEXT_FAMILY, size=24, color=GOLD),
    hoverinfo="skip", showlegend=False
))

# --- Función nombre + valor encima ---
def name_and_value(fig, x, y, full_txt):
    if not full_txt: return
    name = limpia_nombre(full_txt)
    value = extrae_valor(full_txt)
    size = font_size_for(name)

    # Contorno nombre
    for dx, dy in [(-0.02,0),(0.02,0),(0,0.02),(0,-0.02)]:
        fig.add_trace(go.Scatter(
            x=[x+dx], y=[y+dy], mode="text",
            text=[f"<b>{name}</b>"],
            textfont=dict(family=TEXT_FAMILY, size=size, color="rgba(255,255,255,0.8)"),
            hoverinfo="skip", showlegend=False
        ))

    # Texto nombre principal
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="text",
        text=[f"<b>{name}</b>"],
        textfont=dict(family=TEXT_FAMILY, size=size, color=PRIMARY_BLUE),
        hoverinfo="skip", showlegend=False
    ))

    # Valor encima, centrado
    if value is not None:
        fig.add_trace(go.Scatter(
            x=[x], y=[y+0.35], mode="text",
            text=[f"{value}€"],
            textfont=dict(family=TEXT_FAMILY, size=max(14,int(size*0.7)), color=GOLD),
            hoverinfo="skip", showlegend=False
        ))

# Colocar jugadores según formación
coords = FORMACIONES_COORDS[formacion]

if elegido_portero:
    name_and_value(fig, coords["Portero"][0][0], coords["Portero"][0][1], elegido_portero)

for coord, j in zip(coords["Defensa"], elegidos_defensas):
    name_and_value(fig, coord[0], coord[1], j)

for coord, j in zip(coords["Mediocentro"], elegidos_medios):
    name_and_value(fig, coord[0], coord[1], j)

for coord, j in zip(coords["Delantero"], elegidos_delanteros):
    name_and_value(fig, coord[0], coord[1], j)

# ---- Cálculo de valor de equipo y presupuesto restante ----
jugadores_seleccionados = [elegido_portero] + elegidos_defensas + elegidos_medios + elegidos_delanteros
valor_equipo = sum([extrae_valor(j) for j in jugadores_seleccionados if j])
presu_restante = PRESUPUESTO_MAX - valor_equipo
warning = " ⚠️" if presu_restante < 0 else ""

# Cartel Valor Equipo
fig.add_annotation(
    text=f"Valor Equipo: {valor_equipo}€",
    xref="paper", yref="paper",
    x=0.25, y=0.02,  # parte baja izquierda
    showarrow=False,
    font=dict(family=TEXT_FAMILY, size=18, color="white"),
    align="center",
    bordercolor="white",
    borderwidth=1,
    bgcolor="black",
    opacity=1
)

# Cartel Presupuesto restante
fig.add_annotation(
    text=f"Presupuesto: {presu_restante}€{warning}",
    xref="paper", yref="paper",
    x=0.75, y=0.02,  # parte baja derecha
    showarrow=False,
    font=dict(family=TEXT_FAMILY, size=18, color="white"),
    align="center",
    bordercolor="white",
    borderwidth=1,
    bgcolor="black",
    opacity=1
)

st.plotly_chart(fig, use_container_width=True)


# ---------------- Envío ----------------
if st.button("🚀 Enviar Alineación"):
    if not usuario.strip():
        st.error("❌ Debes introducir tu usuario.")
        st.stop()
    jugadores = [elegido_portero] + elegidos_defensas + elegidos_medios + elegidos_delanteros
    nombres_limpios = [limpia_nombre(j) for j in jugadores]
    presupuesto = sum([extrae_valor(j) for j in jugadores])
    st.markdown(f"**💰 Presupuesto usado: {presupuesto}/{PRESUPUESTO_MAX}**")
    if presupuesto > PRESUPUESTO_MAX:
        st.error("❌ Te pasas del presupuesto.")
        st.stop()
    alineacion_id = str(uuid.uuid4())[:8]
    row = [alineacion_id, usuario, jornada] + nombres_limpios + [presupuesto, formacion]
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(SHEET_URL)
        ws = sh.worksheet(SHEET_ENTRADAS)
        ws.append_row(row, value_input_option="USER_ENTERED")
        st.success("✅ Alineación guardada en *Entradas*")
    except Exception as e:
        st.error(f"⚠️ Error escribiendo en Google Sheets: {e}")
