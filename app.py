"""Punto de entrada: configuración, tema, barra lateral y navegación.

La app se organiza con `st.navigation` y la carpeta `app_pages/`. Este archivo
se ejecuta ANTES que la página seleccionada en cada interacción, así que aquí
vive todo lo compartido: el tema, la barra lateral y el estado inicial de la
sesión. Las páginas leen de `st.session_state` lo que necesitan.

Los títulos de página se pintan aquí desde `st.Page`, así que las páginas no
deben volver a llamar a `st.title`.
"""

import streamlit as st

import observability as obs

st.set_page_config(page_title="Ecosistema Unificado", page_icon="🧠", layout="wide")

# ═══════════════════════════════════════════════════════════════
# TEMA
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); }
    h1, h2, h3, h4 { color: #00d4ff !important; text-shadow: 0 0 10px rgba(0, 212, 255, 0.3); }
    p, label, div, li { color: #e0e0e0 !important; }
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #1e2540 !important; color: #ffffff !important;
        border: 1px solid #2a3560 !important; border-radius: 8px !important;
    }
    .stButton > button {
        background: linear-gradient(90deg, #00d4ff 0%, #0099cc 100%) !important;
        color: #ffffff !important; border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; box-shadow: 0 4px 15px rgba(0, 212, 255, 0.4) !important;
    }
    /* El workbook se previsualiza como papel: las tablas HTML crudas no las
       estiliza Streamlit, y sobre el fondo oscuro no se leerían. Este CSS es
       de maquetación del documento, no del chrome de la app. */
    .workbook-preview {
        background: #ffffff; border-radius: 8px; padding: 28px;
        margin: 10px 0; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
    }
    .workbook-preview h1, .workbook-preview h2, .workbook-preview h3,
    .workbook-preview h4 { color: #004466 !important; text-shadow: none !important; }
    .workbook-preview p, .workbook-preview li, .workbook-preview td,
    .workbook-preview th, .workbook-preview div, .workbook-preview span,
    .workbook-preview small, .workbook-preview strong, .workbook-preview em {
        color: #222222 !important;
    }
    .workbook-preview table { width: 100%; border-collapse: collapse; margin: 15px 0; }
    .workbook-preview th, .workbook-preview td {
        border: 1px solid #cccccc; padding: 8px; text-align: left;
    }
    .workbook-preview th { background: #f0f4f8; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# ESTADO COMPARTIDO ENTRE PÁGINAS
# ═══════════════════════════════════════════════════════════════
# Se inicializa aquí, que es el único sitio que se ejecuta siempre antes que
# cualquier página. Las páginas leen estas claves y escriben sus resultados.
for clave, valor in {
    "api_key": "",
    "model_id": "claude-sonnet-4-5",
    # Paso 0
    "icai_dossier": None,
    "icai_sections": None,
    "icai_offer_feed": "",
    "icai_spce_feed": "",
    "icai_design_feed": "",
    # Fase 1
    "producto_html": None,
    "producto_audit": None,
    "producto_roadmap": None,
    # Fase 2
    "brief_landing": None,
    # Design Pack
    "design_pack": None,
}.items():
    st.session_state.setdefault(clave, valor)

# ═══════════════════════════════════════════════════════════════
# BARRA LATERAL: API KEY, MODELO Y OBSERVABILIDAD
# ═══════════════════════════════════════════════════════════════
# Etiquetas cortas: en una barra lateral de 300 px, "Claude Sonnet 4.5
# (recomendado)" se cortaba con puntos suspensivos en el selector.
MODELOS = {
    "Sonnet 4.5 · recomendado": "claude-sonnet-4-5",
    "Sonnet 4.5 · versión fija": "claude-sonnet-4-5-20250929",
    "Haiku 4.5 · rápido y barato": "claude-haiku-4-5",
    "Opus 4.5 · máxima potencia": "claude-opus-4-5",
}
MODELO_POR_DEFECTO = "claude-sonnet-4-5"

# st.secrets.get() NO absorbe la ausencia de secretos: si no existe
# .streamlit/secrets.toml, Streamlit lanza StreamlitSecretNotFoundError incluso
# con valor por defecto. Es un caso previsto, no un fallo.
try:
    saved_api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
except Exception:
    saved_api_key = ""

with st.sidebar:
    st.header("Configuración", icon=":material/settings:")

    if saved_api_key:
        st.success("API Key cargada de forma segura", icon=":material/lock:")
        api_key = saved_api_key
    else:
        st.warning("No se encontró ANTHROPIC_API_KEY en Secrets. Introdúcela abajo.",
                   icon=":material/key_off:")
        api_key = st.text_input("API key de Anthropic (solo esta sesión)",
                                type="password", key="entrada_api_key").strip()

    st.divider()
    nombres = list(MODELOS.keys())
    candidatos = [i for i, k in enumerate(nombres) if MODELOS[k] == MODELO_POR_DEFECTO]
    modelo_sel = st.selectbox("Modelo de IA", nombres,
                              index=candidatos[0] if candidatos else 0,
                              key="selector_modelo")

    st.divider()
    st.info("Key gratis en [console.anthropic.com](https://console.anthropic.com)",
            icon=":material/lightbulb:")
    obs.render_sidebar()

# La configuración queda disponible para las páginas. No son claves de widget,
# así que asignarlas aquí no interfiere con ningún widget.
st.session_state["api_key"] = api_key
st.session_state["model_id"] = MODELOS[modelo_sel]

# ═══════════════════════════════════════════════════════════════
# NAVEGACIÓN
# ═══════════════════════════════════════════════════════════════
pagina = st.navigation(
    [
        st.Page("app_pages/inicio.py", title="Inicio",
                icon=":material/home:", default=True),
        st.Page("app_pages/icai.py", title="Paso 0 · ICAI",
                icon=":material/explore:", url_path="icai"),
        st.Page("app_pages/producto.py", title="Fase 1 · Producto",
                icon=":material/inventory_2:", url_path="producto"),
        st.Page("app_pages/landing.py", title="Fase 2 · Landing",
                icon=":material/rocket_launch:", url_path="landing"),
        st.Page("app_pages/design.py", title="Design Pack",
                icon=":material/palette:", url_path="design"),
    ],
    position="top",
)

st.title(pagina.title, icon=pagina.icon)
pagina.run()
