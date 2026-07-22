import pandas as pd
import plotly.express as px
import requests
import unicodedata

# ─── FUNCIONES ──────────────────────────────────────────────
def limpiar_texto(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto

def update_layout(fig, title):
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=dict(size=20)),
        font=dict(family="Arial", size=12),
        margin=dict(l=40, r=40, t=80, b=40)
    )
    return fig

# ─── CARGAR DATOS ───────────────────────────────────────────

url1 = "https://drive.google.com/uc?export=download&id=ID_DEL_ARCHIVO_1"
url2 = "https://drive.google.com/uc?export=download&id=ID_DEL_ARCHIVO_2"

df1 = pd.read_csv(url1, sep=";", encoding="latin-1", low_memory=False)
df2 = pd.read_csv(url2, sep=";", encoding="latin-1", low_memory=False)

# ─── CORRECCIONES ───────────────────────────────────────────
correcciones = {
    "BOGOTA D.C.": "SANTAFE DE BOGOTA D.C",
    "SAN ANDRES": "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA",
    "CHOCÓ": "CHOCO",
    "VAUPÉS": "VAUPES",
    "GUAINÍA": "GUAINIA",
    "VALLE": "VALLE DEL CAUCA",
}

for df in [df1, df2]:
    df["DEPNOMBRE"] = df["DEPNOMBRE"].replace(correcciones)
    df["DEPNOMBRE"] = df["DEPNOMBRE"].apply(limpiar_texto)

# ─── GEOJSON ────────────────────────────────────────────────
url = "https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc/raw/be6a6e239cd5b5b803c6e7c2ec405b793a9064dd/colombia.geo.json"
geo_data = requests.get(url).json()
for f in geo_data["features"]:
    f["properties"]["NOMBRE_DPT"] = limpiar_texto(f["properties"]["NOMBRE_DPT"])

# ─── VOTOS PETRO POR DEPARTAMENTO ───────────────────────────
petro_1v = (
    df1[df1["CANNOMBRE"].str.contains("PETRO", na=False)]
    .groupby("DEPNOMBRE")["VOTOS"].sum()
    .reset_index()
    .rename(columns={"VOTOS": "VOTOS_PETRO"})
)

petro_2v = (
    df2[df2["CANNOMBRE"].str.contains("PETRO", na=False)]
    .groupby("DEPNOMBRE")["VOTOS"].sum()
    .reset_index()
    .rename(columns={"VOTOS": "VOTOS_PETRO"})
)

# ─── ANIMACIÓN PRIMERA VS SEGUNDA VUELTA ────────────────────

# Agregar columna de vuelta
petro_1v["Vuelta"] = "1ra Vuelta"
petro_2v["Vuelta"] = "2da Vuelta"

# Unir ambos dataframes
petro_anim = pd.concat([petro_1v, petro_2v], ignore_index=True)

# Escala fija para que los colores sean comparables entre frames
max_votos = petro_anim["VOTOS_PETRO"].max()

fig_anim = px.choropleth(
    petro_anim,
    geojson=geo_data,
    featureidkey="properties.NOMBRE_DPT",
    locations="DEPNOMBRE",
    color="VOTOS_PETRO",
    animation_frame="Vuelta",
    color_continuous_scale="Plasma",
    range_color=[0, max_votos],
    hover_data={"VOTOS_PETRO": ":,", "DEPNOMBRE": True, "Vuelta": False},
    labels={"VOTOS_PETRO": "Votos", "DEPNOMBRE": "Departamento"}
)

fig_anim.update_geos(fitbounds="locations", visible=False)
fig_anim.update_layout(
    paper_bgcolor="black",
    geo_bgcolor="black",
    font_color="white",
    coloraxis_colorbar=dict(title="Votos", tickfont=dict(color="white")),
    title=dict(
        text="🔥 Petro — Cambio de votos entre vueltas",
        x=0.5,
        xanchor="center",
        font=dict(size=20, color="white")
    ),
    updatemenus=[{
        "buttons": [{
            "args": [None, {"frame": {"duration": 1500, "redraw": True}, "fromcurrent": True}],
            "label": "▶ Play",
            "method": "animate"
        }, {
            "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}],
            "label": "⏸ Pausa",
            "method": "animate"
        }],
        "type": "buttons",
        "showactive": False,
        "bgcolor": "#333",
        "font": {"color": "white"}
    }]
)

fig_anim.show()