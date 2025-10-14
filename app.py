import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import uuid
import gspread
import numpy as np
import base64, os, unicodedata, re
from google.oauth2.service_account import Credentials

# ---------------- Config ----------------
st.set_page_config(page_title="Inter Maccabi Fantasy", page_icon="⚽", layout="wide")

JORNADA_ACTUAL = st.secrets.get("JORNADA_ACTUAL", "TEST")
SHEET_URL = st.secrets.get("SHEET_URL")
SHEET_ENTRADAS = st.secrets.get("SHEET_ENTRADAS", "Entradas")
PRESUPUESTO_MAX = 700  # límite de presupuesto

PRIMARY_BLUE = "#0033A0"
GOLD = "#FFD700"
TEXT_FAMILY = "JerseyM54, Bebas Neue, Arial Black, sans-serif"

# ---------------- Branding ----------------
LOGO_PATH = "logo.png"
EXCEL_PATH = "IM_Fantasy.xlsx"

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
    data = ws.get_all_records()
    return pd.DataFrame(data)

try:
    df = load_convocados()
except Exception as e:
    st.error(f"❌ No se pudo leer la pestaña 'Convocados' de la hoja IM Fantasy. Error: {e}")
    st.stop()

# Normalización de columnas y preparación de posiciones
df.columns = [c.strip() for c in df.columns]
pos_col = "Posicion"

def formato_opcion(row):
    return f"{row['Nombre']}, {row['Equipo']}. ({row['ValorActual']}€)"

# Filtrado por posiciones
porteros   = df[df[pos_col] == "Portero"]
defensas   = df[df[pos_col] == "Defensa"]
medios     = df[df[pos_col] == "Mediocentro"]
delanteros = df[df[pos_col] == "Delantero"]



# ---------------- Helpers ----------------
def extrae_valor(txt: str) -> int:
    if not txt:
        return 0
    match = re.search(r"\((\d+)€\)", str(txt))
    if match:
        return int(match.group(1))
    return 0

def limpia_nombre(txt: str) -> str:
    if not txt:
        return ""
    name = str(txt).split(",")[0].strip()
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
    if L <= 10: return 18
    if L <= 14: return 16
    if L <= 18: return 14
    return 12

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

    # Texto principal
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="text",
        text=[f"<b>{name}</b>"],
        textfont=dict(family=TEXT_FAMILY, size=size, color=PRIMARY_BLUE),
        hoverinfo="skip", showlegend=False
    ))

    # Valor encima centrado
    if value is not None:
        fig.add_trace(go.Scatter(
            x=[x], y=[y+0.35], mode="text",
            text=[f"{value}€"],
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
# ---------------- Porra ----------------
RIVAL_NIMI = st.secrets["partidos"].get("Nimi_rival", "Rival Nimi")
RIVAL_ARMANDO = st.secrets["partidos"].get("Armando_rival", "Rival Armando")

st.markdown("## 🔮 Predicciones de la Jornada (Resultado +5 Puntos | Ganador/Empate +2 Puntos )")

st.markdown(f"### Partido I. Maccabi vs {RIVAL_NIMI}") 
ganador1 = st.selectbox("Ganador", ["I. Maccabi", RIVAL_NIMI, "Empate"], key="ganador1")
goles_local1 = st.selectbox("Goles I. Maccabi", ["0","1","2","3","4","5","+"], key="goles_local1")
goles_rival1 = st.selectbox(f"Goles {RIVAL_NIMI}", ["0","1","2","3","4","5","+"], key="goles_rival1")

st.markdown(f"### Partido Inter M. vs {RIVAL_ARMANDO}")
ganador2 = st.selectbox("Ganador", ["Inter M.", RIVAL_ARMANDO, "Empate"], key="ganador2")
goles_local2 = st.selectbox("Goles Inter M.", ["0","1","2","3","4","5","+"], key="goles_local2")
goles_rival2 = st.selectbox(f"Goles {RIVAL_ARMANDO}", ["0","1","2","3","4","5","+"], key="goles_rival2")

st.markdown(
    f"<p style='text-align:center; font-size:18px;'><b>I. Maccabi {goles_local1}-{goles_rival1} {RIVAL_NIMI}</b></p>",
    unsafe_allow_html=True
)
st.markdown(
    f"<p style='text-align:center; font-size:18px;'><b>Inter M. {goles_local2}-{goles_rival2} {RIVAL_ARMANDO}</b></p>",
    unsafe_allow_html=True
)

# ---------------- Campo táctico ----------------
FORMACIONES_COORDS = {
    "1-3-2-1": {
        "Portero": [(3,1.2)],
        "Defensa": [(1.5,2.8),(3,2.5),(4.5,2.8)],   # más abiertos
        "Mediocentro": [(2,4.0),(4,4.0)],           # abiertos a los lados
        "Delantero": [(3,6.0)]
    },
    "1-2-3-1": {
        "Portero": [(3,1.2)],
        "Defensa": [(2.2,2.5),(3.8,2.5)],           # un poco más separados
        "Mediocentro": [(1.5,4.3),(3,4.0),(4.5,4.3)], # tres bien repartidos
        "Delantero": [(3,6.0)]
    },
    "1-2-2-2": {
        "Portero": [(3,1.2)],
        "Defensa": [(2.2,2.5),(3.8,2.5)],           # abiertos
        "Mediocentro": [(2,4.0),(4,4.0)],           # dos medios separados
        "Delantero": [(1.9,6.0),(4.1,6.0)]          # dos delanteros abiertos
    }
}


fig = go.Figure()
fig.add_shape(type="rect", x0=0, y0=0, x1=6, y1=8, line=dict(color="white", width=3))
fig.add_shape(type="rect", x0=1, y0=0, x1=5, y1=2, line=dict(color="white", width=2))

fig.update_layout(
    plot_bgcolor="#117A43",
    xaxis=dict(visible=False, range=[0,6]),  # prueba con [0,6] o [0,7]
    yaxis=dict(visible=False, range=[0,8]),
    height=600,
    autosize=True,
    margin=dict(l=10, r=10, t=40, b=40),
    showlegend=False
)

# Logo y jornada
fig.add_trace(go.Scatter(x=[1.2], y=[7.7], mode="text", text=[f"Jornada {JORNADA_ACTUAL}"], textfont=dict(family=TEXT_FAMILY, size=24, color=GOLD), hoverinfo="skip", showlegend=False))

# Colocar jugadores
coords = FORMACIONES_COORDS[formacion]
if elegido_portero: name_and_value(fig, coords["Portero"][0][0], coords["Portero"][0][1], elegido_portero)
for coord, j in zip(coords["Defensa"], elegidos_defensas): name_and_value(fig, coord[0], coord[1], j)
for coord, j in zip(coords["Mediocentro"], elegidos_medios): name_and_value(fig, coord[0], coord[1], j)
for coord, j in zip(coords["Delantero"], elegidos_delanteros): name_and_value(fig, coord[0], coord[1], j)

# ---- Carteles dinámicos de presupuesto ----
jugadores_seleccionados = [elegido_portero] + elegidos_defensas + elegidos_medios + elegidos_delanteros
valor_equipo = sum([extrae_valor(j) for j in jugadores_seleccionados if j])
presu_restante = PRESUPUESTO_MAX - valor_equipo
warning = " ⚠️" if presu_restante < 0 else ""

fig.add_annotation(
    text=f"Valor Equipo: {valor_equipo}€",
    xref="paper", yref="paper",
    x=0.25, y=0.02,
    showarrow=False,
    font=dict(family=TEXT_FAMILY, size=18, color="white"),
    align="center",
    bordercolor="white", borderwidth=1, bgcolor="black", opacity=1
)

fig.add_annotation(
    text=f"Presupuesto: {presu_restante}€{warning}",
    xref="paper", yref="paper",
    x=0.75, y=0.02,
    showarrow=False,
    font=dict(family=TEXT_FAMILY, size=18, color="white"),
    align="center",
    bordercolor="white", borderwidth=1, bgcolor="black", opacity=1
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- Envío ----------------
if st.button("🚀 Enviar Alineación"):
    if not usuario.strip():
        st.error("❌ Debes introducir tu usuario.")
        st.stop()

    # Jugadores elegidos
    jugadores = [elegido_portero] + elegidos_defensas + elegidos_medios + elegidos_delanteros
    nombres_limpios = [limpia_nombre(j) for j in jugadores if j]

    # 🔒 Validación: jugadores duplicados
    if len(nombres_limpios) != len(set(nombres_limpios)):
        st.error("❌ No puedes repetir jugadores en la alineación.")
        st.stop()

    # ---- Validación: coherencia ganador/marcador ----
    # Partido Nimi
    if (goles_local1 > goles_rival1 and ganador1 != "I. Maccabi") or \
    (goles_local1 < goles_rival1 and ganador1 != "Nimi_rival") or \
    (goles_local1 == goles_rival1 and ganador1 != "Empate"):
        st.error("❌ El resultado del partido de I. Maccabi no coincide con el ganador elegido.")
        st.stop()

    # Partido Armando
    if (goles_local2 > goles_rival2 and ganador2 != "Inter M.") or \
    (goles_local2 < goles_rival2 and ganador2 != "Armando_rival") or \
    (goles_local2 == goles_rival2 and ganador2 != "Empate"):
        st.error("❌ El resultado del partido de Inter M. no coincide con el ganador elegido.")
        st.stop()

    # Validación presupuesto
    presupuesto = sum([extrae_valor(j) for j in jugadores if j])
    if presupuesto > PRESUPUESTO_MAX:
        st.error("❌ Te pasas del presupuesto máximo permitido.")
        st.stop()

    # ---- Construcción de fila para Google Sheets ----
    alineacion_id = "AID" + str(uuid.uuid4())[:6]   # AID + 6 chars
    row = [
        alineacion_id, usuario, jornada
    ] + nombres_limpios + [
        ganador1, f"{goles_local1}-{goles_rival1}",
        ganador2, f"{goles_local2}-{goles_rival2}"
    ]

    # ---- Intento de escritura en Google Sheets ----
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(SHEET_URL)
        ws = sh.worksheet(SHEET_ENTRADAS)
        ws.append_row(row, value_input_option="USER_ENTERED")

        st.success("✅ Alineación recibida con éxito")
        st.balloons()

    except Exception as e:
        import traceback
        st.error("⚠️ Error escribiendo en Google Sheets")
        st.code(traceback.format_exc())
