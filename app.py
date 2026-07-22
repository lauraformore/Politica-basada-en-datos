"""
Electoral Intelligence Dashboard
Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import unicodedata
import numpy as np

st.set_page_config(page_title="🗳️ Electoral Colombia 2022", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    section[data-testid="stSidebar"] { background: #0f0f1a; }
    h1, h2, h3 { color: #fff; }
    iframe { display: block !important; }
    div[data-testid="stPlotlyChart"] > div { height: auto !important; }
    div[data-testid="stPlotlyChart"] iframe { height: 480px !important; }
</style>
""", unsafe_allow_html=True)

def limpiar_texto(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto

@st.cache_data
def cargar_datos():
    correcciones = {
        "BOGOTA D.C.": "SANTAFE DE BOGOTA D.C",
        "SAN ANDRES": "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA",
        "CHOCÓ": "CHOCO", "VAUPÉS": "VAUPES",
        "GUAINÍA": "GUAINIA", "VALLE": "VALLE DEL CAUCA",
    }
    dfs = []
    for vuelta, path in [("1ra Vuelta", "data/MMV_NACIONAL_PRESIDENTE_2022_1v.csv"),
                         ("2da Vuelta", "data/MMV_NACIONAL_PRESIDENTE_2022_2v.csv")]:
        df = pd.read_csv(path, sep=';', encoding='latin-1', low_memory=False)
        df["DEPNOMBRE"] = df["DEPNOMBRE"].replace(correcciones).apply(limpiar_texto)
        df["Vuelta"] = vuelta
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

@st.cache_data
def cargar_geojson():
    url = "https://gist.githubusercontent.com/john-guerra/43c7656821069d00dcbc/raw/be6a6e239cd5b5b803c6e7c2ec405b793a9064dd/colombia.geo.json"
    geo = requests.get(url).json()
    for f in geo["features"]:
        f["properties"]["NOMBRE_DPT"] = limpiar_texto(f["properties"]["NOMBRE_DPT"])
    return geo

@st.cache_data
def interpolar_frames(df_total, candidato, n_frames=20):
    df_cand = df_total[df_total["CANNOMBRE"] == candidato]
    v1 = df_cand[df_cand["Vuelta"] == "1ra Vuelta"].groupby("DEPNOMBRE")["VOTOS"].sum()
    v2 = df_cand[df_cand["Vuelta"] == "2da Vuelta"].groupby("DEPNOMBRE")["VOTOS"].sum()
    deps = sorted(set(v1.index) | set(v2.index))
    v1 = v1.reindex(deps, fill_value=0)
    v2 = v2.reindex(deps, fill_value=0)
    frames = []
    for i, t in enumerate(np.linspace(0, 1, n_frames)):
        votos_i = (v1 * (1 - t) + v2 * t).round().astype(int)
        frames.append(pd.DataFrame({
            "DEPNOMBRE": deps, "VOTOS": votos_i.values,
            "Frame": i, "Progreso": f"{int(t * 100)}%"
        }))
    return pd.concat(frames, ignore_index=True)

def make_mapa(df_map, geo_data, animation_frame=None, max_votos=None):
    kwargs = dict(
        geojson=geo_data,
        featureidkey="properties.NOMBRE_DPT",
        locations="DEPNOMBRE",
        color="VOTOS",
        color_continuous_scale="Plasma",
        range_color=[0, max_votos or df_map["VOTOS"].max()],
        mapbox_style="carto-darkmatter",
        zoom=4.8,
        center={"lat": 4.0, "lon": -73.5},
        opacity=0.85,
        labels={"VOTOS": "Votos", "DEPNOMBRE": "Departamento"}
    )
    if animation_frame:
        kwargs["animation_frame"] = animation_frame
        kwargs["hover_data"] = {"VOTOS": ":,", "DEPNOMBRE": True, "Frame": False, "Progreso": True}
    else:
        kwargs["hover_data"] = {"VOTOS": ":,", "DEPNOMBRE": True}

    fig = px.choropleth_mapbox(df_map, **kwargs)
    fig.update_layout(
        paper_bgcolor="#0f0f1a",
        font_color="white",
        height=480,
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="Votos", tickfont=dict(color="white"))
    )
    return fig

df_total = cargar_datos()
geo_data = cargar_geojson()

# ─── SIDEBAR ────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/2/21/Flag_of_Colombia.svg", width=80)
    st.markdown("## ⚙️ Filtros")

    vuelta = st.radio("🗓️ Vuelta", ["1ra Vuelta", "2da Vuelta", "Ambas (animado)"])

    candidatos_1v = sorted(df_total[df_total["Vuelta"] == "1ra Vuelta"]["CANNOMBRE"].dropna().unique())
    candidatos_2v = sorted(df_total[df_total["Vuelta"] == "2da Vuelta"]["CANNOMBRE"].dropna().unique())
    candidatos_opciones = candidatos_2v if vuelta in ["2da Vuelta", "Ambas (animado)"] else candidatos_1v
    candidato = st.selectbox("🧑 Candidato", candidatos_opciones)

    dep_seleccionado = st.selectbox(
        "📍 Departamento (detalle)",
        sorted(df_total["DEPNOMBRE"].dropna().unique())
    )
    st.markdown("---")
    st.caption("Fuente: Registraduría Nacional · Colombia 2022")

# ─── DATOS FILTRADOS ────────────────────────────────────────
df_filtrado    = df_total[df_total["CANNOMBRE"] == candidato]
vuelta_vis     = "1ra Vuelta" if vuelta == "Ambas (animado)" else vuelta
df_cand_vuelta = df_filtrado[df_filtrado["Vuelta"] == vuelta_vis]

total_votos = df_cand_vuelta["VOTOS"].sum()
total_dep   = df_cand_vuelta["DEPNOMBRE"].nunique()
dep_top     = df_cand_vuelta.groupby("DEPNOMBRE")["VOTOS"].sum().idxmax() if total_votos > 0 else "—"
votos_top   = df_cand_vuelta.groupby("DEPNOMBRE")["VOTOS"].sum().max()   if total_votos > 0 else 0

# ─── HEADER ─────────────────────────────────────────────────
st.markdown("# 🗳️ Mapa Electoral Colombia 2022")
st.markdown(f"**{candidato}** · {vuelta_vis}")
st.markdown("---")

# ─── KPIs ───────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("🗳️ Total votos",       f"{total_votos:,}")
k2.metric("🗺️ Departamentos",      total_dep)
k3.metric("🏆 Depto. líder",       dep_top)
k4.metric("📊 Votos depto. líder", f"{votos_top:,}")
st.markdown("---")

# ─── MAPA + PANEL ───────────────────────────────────────────
col_mapa, col_pie = st.columns([3, 1])

with col_mapa:
    st.markdown("### 🗺️ Distribución por departamento")

    if vuelta == "Ambas (animado)":
        df_anim   = interpolar_frames(df_total, candidato, n_frames=20)
        max_votos = df_anim["VOTOS"].max()
        fig_mapa  = make_mapa(df_anim, geo_data, animation_frame="Frame", max_votos=max_votos)
        fig_mapa.update_layout(sliders=[{"visible": False}])
        fig_mapa.update_layout(
            updatemenus=[{
                "buttons": [
                    {"args": [None, {"frame": {"duration": 80, "redraw": True},
                                     "transition": {"duration": 50, "easing": "linear"},
                                     "fromcurrent": True}],
                     "label": "▶ Play", "method": "animate"},
                    {"args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}],
                     "label": "⏸ Pausa", "method": "animate"}
                ],
                "type": "buttons", "showactive": False,
                "x": 0.5, "xanchor": "center", "y": 0.02,
                "bgcolor": "#333", "font": {"color": "white"}
            }]
        )
    else:
        df_map   = df_cand_vuelta.groupby("DEPNOMBRE")["VOTOS"].sum().reset_index()
        fig_mapa = make_mapa(df_map, geo_data)

    st.plotly_chart(fig_mapa, use_container_width=True, config={"displayModeBar": False})

with col_pie:
    st.markdown("### 🏆 Ganador por depto.")

    df_group_vuelta = df_total[df_total["Vuelta"] == vuelta_vis].groupby(["DEPNOMBRE", "CANNOMBRE"])["VOTOS"].sum().reset_index()
    df_winner = df_group_vuelta.sort_values("VOTOS", ascending=False).drop_duplicates("DEPNOMBRE")
    conteo = df_winner["CANNOMBRE"].value_counts().reset_index()
    conteo.columns = ["Candidato", "Departamentos"]

    fig_pie = px.pie(
        conteo, values="Departamentos", names="Candidato",
        color_discrete_sequence=px.colors.qualitative.Bold, hole=0.4
    )
    fig_pie.update_traces(texttemplate='%{percent}', textposition='outside')
    fig_pie.update_layout(
        paper_bgcolor="#0f0f1a", font_color="white",
        showlegend=True, height=240,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(font=dict(size=10))
    )
    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f"### 📍 {dep_seleccionado}")
    df_dep = df_group_vuelta[df_group_vuelta["DEPNOMBRE"] == dep_seleccionado].sort_values("VOTOS", ascending=False).copy()
    if not df_dep.empty:
        total_dep_votos = df_dep["VOTOS"].sum()
        df_dep["%"] = (df_dep["VOTOS"] / total_dep_votos * 100).round(1)
        st.success(f"🏆 {df_dep.iloc[0]['CANNOMBRE']}")
        st.dataframe(
            df_dep[["CANNOMBRE", "VOTOS", "%"]].rename(
                columns={"CANNOMBRE": "Candidato", "VOTOS": "Votos"}
            ).reset_index(drop=True),
            use_container_width=True, hide_index=True
        )

st.markdown("---")

# ─── BARRAS + TABLA ─────────────────────────────────────────
col_bar, col_tabla = st.columns([2, 1])

with col_bar:
    st.markdown("### 📊 Top departamentos")
    df_top = df_cand_vuelta.groupby("DEPNOMBRE")["VOTOS"].sum().reset_index()
    df_top = df_top.sort_values("VOTOS", ascending=False).head(15)

    fig_bar = px.bar(
        df_top, x="VOTOS", y="DEPNOMBRE", orientation="h",
        color="VOTOS", color_continuous_scale="Plasma",
        text="VOTOS", labels={"VOTOS": "Votos", "DEPNOMBRE": "Departamento"}
    )
    fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig_bar.update_layout(
        paper_bgcolor="#0f0f1a", plot_bgcolor="#0f0f1a",
        font_color="white", height=420,
        margin=dict(l=0, r=60, t=10, b=0),
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

with col_tabla:
    st.markdown("### 📋 Tabla completa")
    df_tabla = df_cand_vuelta.groupby("DEPNOMBRE")["VOTOS"].sum().reset_index()
    df_tabla = df_tabla.sort_values("VOTOS", ascending=False).reset_index(drop=True)
    total_t  = df_tabla["VOTOS"].sum()
    df_tabla["%"] = (df_tabla["VOTOS"] / total_t * 100).round(1)
    st.dataframe(df_tabla, use_container_width=True, hide_index=True, height=420)