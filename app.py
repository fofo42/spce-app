import observability as obs
import streamlit as st
import io
import re
import base64
from xhtml2pdf import pisa

from parsing import extraer_json
from sanitize import limpiar_html

# ═══════════════════════════════════════════════════════════════
# HELPERS DE ARCHIVOS
# ═══════════════════════════════════════════════════════════════
def procesar_archivos(files, etiqueta):
    texto = ""
    bloques = []
    for f in files or []:
        if f.type == "application/pdf":
            try:
                from pypdf import PdfReader
                txt = "\n".join([p.extract_text() or "" for p in PdfReader(io.BytesIO(f.read())).pages])
                texto += f"\n--- {etiqueta} | {f.name} ---\n{txt[:12000]}\n"
            except Exception:
                st.warning(f"PDF no legible: {f.name}", icon=":material/warning:")
        elif f.type in ["image/png", "image/jpeg"]:
            bloques.append({"type": "text", "text": f"[IMAGEN — {etiqueta}: {f.name}]"})
            bloques.append({"type": "image", "source": {"type": "base64",
                "media_type": f.type, "data": base64.b64encode(f.read()).decode()}})
    return texto, bloques

# ═══════════════════════════════════════════════════════════════
# TEMA OSCURO
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="Ecosistema Unificado", page_icon="🧠", layout="wide")

# ═══════════════════════════════════════════════════════════════
# API KEY (desde Streamlit Secrets — nunca en disco)
# ═══════════════════════════════════════════════════════════════
# OJO: st.secrets.get() NO absorbe la ausencia de secretos. Si no existe
# .streamlit/secrets.toml, Streamlit lanza StreamlitSecretNotFoundError
# incluso con valor por defecto, y al estar en el nivel de módulo la app
# no llegaba a arrancar. Ahora es un caso previsto: se pide la clave en la
# barra lateral y solo vive en memoria durante la sesión.
try:
    saved_api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
except Exception:
    saved_api_key = ""

saved_model = "claude-sonnet-4-5"

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
    .phase-container, .menu-card {
        background: rgba(30, 37, 64, 0.6); border-radius: 12px; padding: 25px;
        margin: 15px 0; border: 1px solid #2a3560;
    }
    .icai-badge {
        background: rgba(0, 212, 255, 0.1); border: 1px solid #00d4ff;
        border-radius: 8px; padding: 15px; margin: 15px 0;
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

st.title("Ecosistema unificado: ICAI + Offer Engine + SPCE")
st.markdown("*Capa 0 (cliente) → Oferta → Landing → Diseño, con inteligencia encadenada.*")

# ═══════════════════════════════════════════════════════════════
# SIDEBAR: API KEY + MODELO + OBSERVABILIDAD
# ═══════════════════════════════════════════════════════════════
MODELOS = {
    "Claude Sonnet 4.5 (recomendado)": "claude-sonnet-4-5",
    "Claude Sonnet 4.5 (versión fija)": "claude-sonnet-4-5-20250929",
    "Claude Haiku 4.5 (rápido y barato)": "claude-haiku-4-5",
    "Claude Opus 4.5 (máxima potencia)": "claude-opus-4-5",
}

with st.sidebar:
    st.header("Configuración", icon=":material/settings:")
    if saved_api_key:
        st.success("API Key cargada de forma segura", icon=":material/lock:")
        api_key = saved_api_key
    else:
        st.warning("No se encontró ANTHROPIC_API_KEY en Secrets. Introdúcela abajo.",
                   icon=":material/key_off:")
        api_key_input = st.text_input("API Key de Anthropic (solo esta sesión)", type="password")
        api_key = api_key_input.strip() if api_key_input else ""

    st.divider()
    nombres = list(MODELOS.keys())
    idx = 0
    for i, k in enumerate(nombres):
        if MODELOS[k] == saved_model:
            idx = i
    modelo_sel = st.selectbox("Modelo de IA", nombres, index=idx)
    MODEL_ID = MODELOS[modelo_sel]

    st.divider()
    st.info("Key gratis en [console.anthropic.com](https://console.anthropic.com)",
            icon=":material/lightbulb:")
    obs.render_sidebar()

# ═══════════════════════════════════════════════════════════════
# WORKBOOK: VISTA PREVIA SEGURA Y PDF
# ═══════════════════════════════════════════════════════════════
CSS_IMPRESION = (
    "<style>"
    "body{font-family:Helvetica;color:#222;padding:40px;line-height:1.5;}"
    "h1{color:#004466;border-bottom:3px solid #004466;padding-bottom:10px;}"
    "h2{color:#006699;margin-top:25px;}"
    "table{width:100%;border-collapse:collapse;margin:15px 0;}"
    "th,td{border:1px solid #ccc;padding:10px;text-align:left;}"
    "th{background:#f0f4f8;}"
    "hr{border:none;border-top:1px solid #ddd;}"
    "@page{size:A4;margin:2cm;}"
    ".page-break{page-break-before:always;}"
    "</style>"
)


def _documento_pdf(cuerpo):
    """Envuelve el cuerpo ya saneado en un documento con la hoja de impresión."""
    return f"<html><head>{CSS_IMPRESION}</head><body>{cuerpo}</body></html>"


@st.cache_data(show_spinner="Generando el PDF…", max_entries=4)
def _construir_pdf(html_raw):
    """Convierte el workbook a PDF y devuelve (bytes, mensaje de error).

    Se sanea ANTES de convertir, igual que la vista previa, por dos motivos:

    * xhtml2pdf resuelve las referencias `url(...)` del CSS y puede llegar a
      descargar recursos remotos desde el servidor (SSRF) a partir de HTML
      generado por el modelo.
    * su parser de CSS lanza CSSParseError con entradas hostiles, así que el
      PDF fallaba directamente.

    Además, el código anterior no miraba el valor de retorno de CreatePDF: si
    fallaba, se ofrecía un PDF roto sin ningún aviso.

    Se cachea porque xhtml2pdf es lento y bloqueante y el HTML solo cambia al
    regenerar el workbook.
    """
    cuerpo = limpiar_html(html_raw)
    if not cuerpo.strip():
        return None, "el HTML quedó vacío tras el saneado de seguridad."
    buffer = io.BytesIO()
    try:
        resultado = pisa.CreatePDF(io.StringIO(_documento_pdf(cuerpo)), dest=buffer)
    except Exception as e:  # xhtml2pdf puede lanzar con HTML degenerado
        return None, f"{type(e).__name__}: {e}"
    if resultado.err:
        return None, f"xhtml2pdf reportó {resultado.err} error(es) al maquetar el HTML."
    pdf = buffer.getvalue()
    if not pdf:
        return None, "el PDF resultante está vacío."
    return pdf, ""


def _mostrar_workbook(html_raw):
    """Renderiza el workbook saneado, avisando si el saneado lo dejó vacío."""
    limpio = limpiar_html(html_raw)
    if limpio.strip():
        st.markdown(f'<div class="workbook-preview">{limpio}</div>',
                    unsafe_allow_html=True)
    else:
        st.warning("La vista previa quedó vacía tras el saneado de seguridad: "
                   "el HTML generado solo contenía etiquetas descartadas.",
                   icon=":material/gpp_maybe:")


# ═══════════════════════════════════════════════════════════════
# ESTADO DE SESIÓN
# ═══════════════════════════════════════════════════════════════
for k, v in {"modo_seleccionado": None, "producto_html": None,
             "producto_audit": None, "producto_roadmap": None,
             "continuar_landing": False, "modo_modelado": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════
# PROMPTS MAESTROS
# ═══════════════════════════════════════════════════════════════
OFFER_SYSTEM = """Eres el OFFER MODELING & ENGINEERING ENGINE V1.0.1 (motor completo).

DISTINCIÓN DE INPUTS:
- REFERENCIA DE ESTILO: solo para extraer estilo, patrones y técnicas. NUNCA copies su contenido.
- PRODUCTO BASE: contenido real que debes remodelar y superar.
- INTELIGENCIA ICAI (si existe): contexto prioritario de cliente (segmentos, dolores, lenguaje, objeciones, triggers).

INVARIANTES (SIEMPRE ACTIVOS):
INV-01 NO INVENTION: nunca inventes resultados, testimonios, credenciales, estudios, garantías, precios ni datos.
INV-02 TRANSFORMATION FIRST: la oferta se construye alrededor de la transformación, no del volumen de contenido.
INV-03 EVIDENCE ≠ INFERENCE: separa siempre evidencia, inferencia e hipótesis.
INV-04 UNKNOWN IS VALID: si falta información, UNKNOWN es preferible a inventar.
INV-05 PRACTICALITY > CONTENT VOLUME: prioriza CHECKLIST, WORKSHEET, TRACKER, TEMPLATE, SCORECARD, DECISION TOOL, PROTOCOL, ROUTINE, QUICK REFERENCE. GUIDE solo como último recurso justificado.
INV-06 BEGINNER-FIRST: comprensible sin conocimientos previos, sin jerga.
INV-07 PRINTABILITY: espacios de escritura, casillas, tablas, campos, instrucciones cortas.
INV-08 REDUNDANCY CONTROL: dos entregables que resuelven el mismo problema → MERGE o REMOVE.
INV-09 CORE ≠ BONUS: si un componente es necesario para la transformación, es CORE, nunca bonus decorativo.

LOS 6 PILARES OBLIGATORIOS (cada uno produce INSIGHT → NEED → SOLUTION → DELIVERABLE):
P01 TRANSFORMATION DIFFICULTY | P02 SPEED TO RESULT | P03 PROCESS SUPPORT
P04 FUTURE PROBLEM PREVENTION | P05 BLIND SPOTS | P06 PROCESS MEASUREMENT

SELECCIÓN DE FORMATO (IF/THEN):
comprobar→CHECKLIST | completar→WORKSHEET | registrar→TRACKER/LOG | reutilizar→TEMPLATE |
medir→SCORECARD | diagnosticar→DIAGNOSTIC | decidir→DECISION TOOL | ejecutar→PROTOCOL/ACTION PLAN |
practicar→EXERCISE | consultar rápido→QUICK REFERENCE | calcular→CALCULATOR | rutinizar→ROUTINE |
comprender antes de actuar→GUIDE (último recurso).

QUALITY GATES POR ENTREGABLE (DQS 0-100):
DQS = 0.20×Problem Relevance + 0.20×Transformation Impact + 0.15×Practicality + 0.15×Ease of Use + 0.10×Printability + 0.10×Perceived Value + 0.10×Complementarity
DECISIONES: ≥85 ACCEPT | 70-84 ACCEPT_WITH_IMPROVEMENT | 55-69 IMPROVE | 40-54 SIMPLIFY/REDESIGN | <40 REJECT.
HARD GATES: no accionable → REJECT | sin relevancia de transformación → REJECT | redundante → MERGE | demasiado complejo para el avatar → SIMPLIFY | no imprimible siendo práctico → REWORK.

PROCESO INTERNO OBLIGATORIO (no omitas pasos):
1 Extraer producto base. 2 Transformation Map (current → stages → desired). 3 Cliente y obstáculos.
4 Seis pilares. 5 Gap analysis (prioridad = impacto × frecuencia × urgencia × riesgo). 6 Engineering de entregables.
7 Evaluación DQS + gates. 8 Arquitectura (CORE → SUPPORT → MEASUREMENT → PREVENTION → BONUSES). 9 Validación final.

SALIDA:
Responde ÚNICAMENTE con un objeto JSON válido (nada de texto antes o después, nada de bloques ```), con EXACTAMENTE estas 3 claves:

{
  "audit": "AUDITORÍA INGENIERIL breve en español (formato Markdown): Transformation Map en 3 líneas; tabla de pilares [Pilar|Insight|Need|Deliverable|Formato]; Deliverable Matrix [ID|Nombre|Formato|Problema que resuelve|DQS|Decisión]; entregables RECHAZADOS o FUSIONADOS con su motivo; UNKNOWNs y warnings.",
  "workbook_html": "HTML COMPLETO del WORKBOOK: <html><head><style> para A4 </style></head><body> con portada centrada (nombre + promesa DE→A + qué incluye) y una sección <h1> por pilar con sus entregables APROBADOS: tablas con bordes, casillas &#9744;, espacios de escritura, cajas de consejo/advertencia, saltos class='page-break'. Cero relleno.",
  "roadmap": "ROADMAP en Markdown: estructura de carpetas OFFER/01_CORE_TRANSFORMATION…07_BONUSES indicando qué entregable va en cada una; qué crear con Claude, qué con Gamma, qué con hoja de cálculo; orden de creación y dependencias; instrucciones de maquetación."
}

IMPORTANTE: escapa correctamente comillas dobles, saltos de línea y caracteres especiales dentro de los valores para que el JSON sea válido y parseable. No escribas nada fuera de ese objeto JSON."""

SPCE_SYSTEM = """Eres el SALES PAGE CONVERSION ENGINE (SPCE).
REGLAS: Mobile-First, Anti-Invención, Message Match, Beneficios > Características, CTA en primera persona repetido 3+ veces.
Vendes el WORKBOOK/SISTEMA generado (destaca su valor práctico, no teórico). Nunca inventes testimonios, cifras ni escasez."""

# ═══════════════════════════════════════════════════════════════
# MENÚ INICIAL (5 MODOS)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] is None:
    st.markdown('<div class="menu-card">', unsafe_allow_html=True)
    st.subheader("¿Qué quieres hacer hoy?", icon=":material/rocket_launch:")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("ICAI (Paso 0)", width="stretch", icon=":material/explore:"):
            st.session_state['modo_seleccionado'] = 'icai'
            st.rerun()
    with c2:
        if st.button("Modelar producto", width="stretch", icon=":material/inventory_2:"):
            st.session_state['modo_seleccionado'] = 'producto'
            st.rerun()
    with c3:
        if st.button("Modelar landing", width="stretch", icon=":material/rocket_launch:"):
            st.session_state['modo_seleccionado'] = 'landing'
            st.rerun()
    with c4:
        if st.button("Flujo completo", width="stretch", icon=":material/sync:"):
            st.session_state['modo_seleccionado'] = 'completo'
            st.rerun()
    with c5:
        if st.button("Design Pack", width="stretch", icon=":material/palette:"):
            st.session_state['modo_seleccionado'] = 'design'
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
- **ICAI (Paso 0)**: modela al cliente y su decisión; genera los puentes OFFER_FEED / SPCE_FEED / DESIGN_FEED.
- **Modelar producto**: Offer Engine V1.0.1: auditoría con DQS + Workbook PDF + Roadmap de carpetas.
- **Modelar landing**: brief de página de ventas para Lovable.
- **Flujo completo**: primero el producto; si te convence, pasas a la landing.
- **Design Pack**: prompts listos para Canva/Gamma/Bing con tu estilo visual.
    """)
    st.stop()

# ══════════════════════════════════════════════════════════════
# MODO 0: ICAI (CAPA DE INTELIGENCIA DE CLIENTE)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] == 'icai':
    try:
        import icai_engine
        icai_engine.render(api_key, MODEL_ID)
    except Exception as e:
        st.error(f"Módulo ICAI no disponible: {e}", icon=":material/error:")
        st.markdown("El archivo `icai_engine.py` debe estar junto a `app.py` (y en la raíz del repo).")
        if st.button("Volver al menú", key="v7", icon=":material/arrow_back:"):
            st.session_state['modo_seleccionado'] = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════
# FASE 1: MODELAR PRODUCTO (OFFER ENGINE V1.0.1)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] in ['producto', 'completo']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("Fase 1: Offer Engine V1.0.1 — modelar nuevo producto",
                 icon=":material/inventory_2:")

    if st.button("Volver al menú", key="v1", icon=":material/arrow_back:"):
        st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False, 'modo_modelado': None})
        st.rerun()

    # ═══════════════════════════════════════════════════════════════
    # DETECCIÓN DE ICAI Y SELECTOR DE MODO
    # ═══════════════════════════════════════════════════════════════
    feed0 = st.session_state.get('icai_offer_feed', '')
    tiene_icai = bool(feed0)

    if tiene_icai:
        st.markdown('<div class="icai-badge">', unsafe_allow_html=True)
        st.success("Inteligencia ICAI detectada y disponible", icon=":material/psychology:")
        st.markdown("El análisis del Paso 0 está listo para usarse. **Elige cómo quieres modelar el producto:**")

        # Los textos se usan como valor de estado y más abajo se comprueba
        # "Crear desde cero" in modo_modelado, así que el literal importa.
        MODO_DESDE_CERO = "Crear desde cero (usando inteligencia ICAI)"
        MODO_REMODELAR = "Remodelar producto existente (subir archivo de referencia)"

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            elegido_cero = st.button("Crear desde cero (con la inteligencia ICAI del Paso 0)",
                                      width="stretch", key="btn_modo_desde_cero",
                                      icon=":material/add_circle:")
        with bcol2:
            elegido_remodelar = st.button("Remodelar producto existente (subiré un archivo de referencia)",
                                           width="stretch", key="btn_modo_remodelar",
                                           icon=":material/autorenew:")

        if elegido_cero:
            st.session_state['modo_modelado'] = MODO_DESDE_CERO
        elif elegido_remodelar:
            st.session_state['modo_modelado'] = MODO_REMODELAR

        modo_actual = st.session_state.get('modo_modelado')
        if modo_actual in (MODO_DESDE_CERO, MODO_REMODELAR):
            st.info(f"Modo seleccionado: **{modo_actual}** (puedes cambiarlo pulsando el otro botón)",
                    icon=":material/check_circle:")
        else:
            st.warning("Elige una de las dos opciones de arriba para continuar.",
                       icon=":material/arrow_upward:")

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("No hay análisis ICAI disponible. Debes subir un producto de referencia.",
                   icon=":material/warning:")
        st.session_state['modo_modelado'] = "Remodelar producto existente (subir archivo de referencia)"

    # ═══════════════════════════════════════════════════════════════
    # BLOQUE A: REFERENCIA DE ESTILO
    # ═══════════════════════════════════════════════════════════════
    # OJO: st.session_state.get('modo_modelado', '') NO devuelve '' cuando la
    # clave YA existe con valor None (y se inicializa a None), sino None. Con
    # `"Crear desde cero" in None` Python lanza TypeError, así que en cuanto el
    # Paso 0 generaba el OFFER_FEED, entrar en la Fase 1 rompía la app.
    modo_modelado = st.session_state.get('modo_modelado') or ''

    st.markdown("#### A) Referencia de estilo y modelado *(cómo debe quedar)*")
    c1, c2 = st.columns(2)
    with c1:
        referencia_url = st.text_input("URL de referencia (opcional)")
        uploaded_ref = st.file_uploader("Archivos de referencia (PDF/PNG/JPG)",
            type=['pdf', 'png', 'jpg', 'jpeg'], accept_multiple_files=True, key="ref_files")
    with c2:
        descripcion_ref = st.text_area("Descripción de la referencia (opcional)", height=90)
        tipo_producto = st.selectbox("Tipo de producto",
            ["Ebook/Guía", "Plantilla de Notion", "Curso Online", "Libro de Recetas",
             "Software/SaaS", "Servicio", "Otro"])

    # ═══════════════════════════════════════════════════════════════
    # BLOQUE B: PRODUCTO BASE (condicional según modo)
    # ═══════════════════════════════════════════════════════════════
    st.markdown("#### B) Producto base")

    if tiene_icai and "Crear desde cero" in modo_modelado:
        st.info("Modo: crear desde cero usando inteligencia ICAI. No necesitas subir producto base.",
                icon=":material/lightbulb:")
        st.markdown("*El Offer Engine diseñará el producto usando la inteligencia de cliente del Paso 0 + la referencia de estilo.*")
        uploaded_producto = None
        descripcion_producto = ""
    else:
        uploaded_producto = st.file_uploader("Sube TU producto (PDF/PNG/JPG)",
            type=['pdf', 'png', 'jpg', 'jpeg'], accept_multiple_files=True, key="prod_files")
        descripcion_producto = st.text_area("O describe tu producto si no tienes archivos", height=90, key="desc_prod")

    c3, c4 = st.columns(2)
    with c3:
        avatar = st.text_input("Avatar/Público Objetivo", placeholder="Ej: mujeres sin tiempo para cocinar")
    with c4:
        transformacion = st.text_input("Transformación deseada", placeholder="Ej: cocinar 2 veces/semana y tener comida para 7 días")

    # ═══════════════════════════════════════════════════════════════
    # VALIDACIÓN Y EJECUCIÓN
    # ═══════════════════════════════════════════════════════════════
    producto_aportado = bool(uploaded_producto) or bool(descripcion_producto.strip())
    
    if st.button("Ejecutar motor V1.0.1 (auditoría + workbook + roadmap)", type="primary",
                 width="stretch", icon=":material/psychology:"):
        if not api_key:
            st.error("Introduce tu API Key en la barra lateral", icon=":material/key_off:")
        elif tiene_icai and not st.session_state.get('modo_modelado'):
            st.error("Elige primero cómo quieres modelar el producto (los dos botones de arriba).",
                     icon=":material/warning:")
        elif not tiene_icai and not producto_aportado:
            st.error("Falta TU PRODUCTO: sube archivos en el Bloque B o descríbelo "
                     "(o ejecuta primero el Paso 0 ICAI).", icon=":material/warning:")
        else:
            modo_texto = "Diseño desde cero con ICAI" if (tiene_icai and "Crear desde cero" in modo_modelado) else "Remodelado de producto base"
            with st.spinner(f"Ejecutando la state machine ({modo_texto}): extracción → pilares → gaps → DQS → arquitectura → validación…"):
                ref_texto, ref_bloques = procesar_archivos(uploaded_ref, "REFERENCIA DE ESTILO")
                prod_texto, prod_bloques = procesar_archivos(uploaded_producto, "PRODUCTO A MODELAR") if uploaded_producto else ("", [])
                
                contenido = []
                
                # Inteligencia ICAI (si existe)
                if feed0:
                    contenido.append({"type": "text", "text":
                        f"=== INTELIGENCIA ICAI (OFFER_FEED) ===\nContexto prioritario de cliente:\n{feed0}"})
                
                # Referencia de estilo
                contenido.append({"type": "text", "text": f"""=== REFERENCIA DE ESTILO/MODELADO ===
(Úsala SOLO para estilo/patrones/técnicas. NO copies su contenido.)
URL: {referencia_url or '-'}
Descripción: {descripcion_ref or '-'}
{ref_texto}"""})
                contenido.extend(ref_bloques)
                
                # Producto base (puede estar vacío en modo desde-cero)
                if producto_aportado:
                    contenido.append({"type": "text", "text": f"""=== PRODUCTO REAL A MODELAR ===
(Contenido base. Construye el producto SUPERIOR a partir de aquí.)
{prod_texto}
Descripción adicional: {descripcion_producto or '-'}"""})
                    contenido.extend(prod_bloques)
                else:
                    contenido.append({"type": "text", "text": """=== PRODUCTO BASE ===
NO hay producto base aportado. Debes DISEÑAR el producto desde cero usando:
- La inteligencia de cliente (ICAI OFFER_FEED) como fuente principal de obstáculos, dolores, deseos y lenguaje.
- La referencia de estilo únicamente como inspiración de formato/patrones.
Construye un producto superior que resuelva los obstáculos identificados con entregables prácticos e imprimibles."""})
                
                # Instrucción final adaptada al modo
                instruccion_final = (
                    "Ejecuta tu proceso interno completo (9 pasos) y entrega los 3 bloques con separadores exactos."
                    if producto_aportado
                    else "Ejecuta tu proceso interno completo (9 pasos). Como NO hay producto base, debes INVENTAR la arquitectura de entregables basándote en los obstáculos del cliente (ICAI) y los patrones de la referencia de estilo. Entrega los 3 bloques con separadores exactos."
                )
                contenido.append({"type": "text", "text": f"""DATOS DEL PROYECTO:
TIPO: {tipo_producto} | AVATAR: {avatar} | TRANSFORMACIÓN: {transformacion}
MODO: {'DISEÑO DESDE CERO (con ICAI)' if (tiene_icai and 'Crear desde cero' in modo_modelado) else 'REMODELADO (con producto base)'}

INSTRUCCIÓN: {instruccion_final}"""})

                try:
                    client = obs.cliente_observado(api_key, MODEL_ID)

                    st.markdown("##### Generando en vivo (texto en bruto; el workbook aparece abajo al terminar)")
                    with client.messages.stream(
                        model=MODEL_ID, max_tokens=20000,
                        system=OFFER_SYSTEM,
                        messages=[
                            {"role": "user", "content": contenido},
                            {"role": "assistant", "content": "{"}
                        ]
                    ) as stream:
                        def _generador_texto():
                            for chunk in stream.text_stream:
                                yield chunk
                        raw_text = st.write_stream(_generador_texto())
                        stream.get_final_message()

                    # Empezamos el texto con "{" porque ese carácter no viene incluido
                    # en la respuesta (se lo "regalamos" nosotros para forzar que
                    # Claude continúe directamente en formato JSON).
                    raw_output = "{" + raw_text

                    audit, html_part, roadmap = "", "", ""
                    datos = extraer_json(raw_output)
                    if datos is not None:
                        audit = (datos.get("audit") or "").strip()
                        html_part = (datos.get("workbook_html") or "").strip()
                        roadmap = (datos.get("roadmap") or "").strip()

                    if not html_part:
                        st.error("No se pudo interpretar la respuesta de la IA. "
                                 "Vuelve a intentarlo; si se repite, mira el detalle de abajo.",
                                 icon=":material/error:")
                        with st.expander("Ver respuesta en bruto", icon=":material/build:"):
                            st.code(raw_output[:5000])
                    else:
                        st.session_state['producto_audit'] = audit
                        st.session_state['producto_html'] = html_part
                        st.session_state['producto_roadmap'] = roadmap
                        st.success("Motor V1.0.1 completado: auditoría, workbook y roadmap generados.",
                                   icon=":material/check_circle:")
                        st.caption(obs.last_line())
                except Exception as e:
                    st.error(f"Error: {str(e)}", icon=":material/error:")

    # ══════════════════════════════════════════════════════════════
    # RESULTADOS
    # ═══════════════════════════════════════════════════════════════
    if st.session_state['producto_html']:
        if st.session_state['producto_audit']:
            with st.expander("Auditoría ingenieril (quality gates, DQS y decisiones)",
                             expanded=False, icon=":material/fact_check:"):
                st.markdown(st.session_state['producto_audit'])

        st.subheader("Vista previa del workbook", icon=":material/description:")
        _mostrar_workbook(st.session_state['producto_html'])

        c5, c6 = st.columns(2)
        with c5:
            pdf, error_pdf = _construir_pdf(st.session_state['producto_html'])
            if pdf:
                st.download_button("Descargar PDF del producto", data=pdf,
                                   file_name="producto_alto_valor.pdf",
                                   mime="application/pdf", width="stretch",
                                   icon=":material/picture_as_pdf:")
            else:
                st.error(f"No se pudo generar el PDF: {error_pdf}",
                         icon=":material/error:")
        with c6:
            if st.session_state['producto_roadmap']:
                st.subheader("Roadmap de carpetas", icon=":material/folder_open:")
                st.markdown(st.session_state['producto_roadmap'])

        if st.session_state['modo_seleccionado'] == 'completo':
            st.divider()
            st.subheader("¿El producto te convence? ¿Continuamos con la landing?",
                         icon=":material/help:")
            c7, c8 = st.columns(2)
            with c7:
                if st.button("Sí, crear la landing", width="stretch",
                             icon=":material/check_circle:"):
                    st.session_state['continuar_landing'] = True
                    st.rerun()
            with c8:
                if st.button("No, terminar aquí", width="stretch",
                             icon=":material/cancel:"):
                    st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False, 'modo_modelado': None})
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if not (st.session_state['modo_seleccionado'] == 'completo' and st.session_state['continuar_landing']):
        st.stop()

# ═══════════════════════════════════════════════════════════════
# FASE 2: MODELAR LANDING (SPCE)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] == 'landing' or st.session_state['continuar_landing']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("Fase 2: SPCE — brief de landing para Lovable",
                 icon=":material/rocket_launch:")

    if st.button("Volver al menú", key="v2", icon=":material/arrow_back:"):
        st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False, 'modo_modelado': None})
        st.rerun()

    feed2 = st.session_state.get('icai_spce_feed', '')
    if feed2:
        st.info("Inteligencia ICAI conectada: el SPCE usará el SPCE_FEED "
                "(mensajes por awareness, hooks, objeciones→FAQ).",
                icon=":material/psychology:")

    if st.session_state['continuar_landing'] and st.session_state['producto_html']:
        producto_ctx = re.sub(r'<[^>]+>', ' ', st.session_state['producto_html'])
        producto_ctx = re.sub(r'\s+', ' ', producto_ctx)[:6000]
    else:
        producto_ctx = st.text_area("Describe tu producto o pega aquí su contenido", height=150)

    c1, c2 = st.columns(2)
    with c1:
        precio = st.text_input("Precio", placeholder="Ej: $27 USD")
        garantia = st.text_input("Garantía", placeholder="Ej: 7 días sin preguntas")
    with c2:
        gancho = st.text_input("Gancho del Anuncio", placeholder="Ej: Deja de adivinar a dónde se va tu sueldo")

    if st.button("Generar brief de landing", type="primary", width="stretch",
                 icon=":material/rocket_launch:"):
        if not api_key:
            st.error("Introduce tu API Key", icon=":material/key_off:")
        elif not producto_ctx:
            st.error("Falta el producto (genera la Fase 1 o descríbelo)",
                     icon=":material/warning:")
        else:
            with st.spinner("Aplicando SPCE: arquitectura psicológica, copy y brief mobile-first…"):
                prompt = f"""PRODUCTO A VENDER (sistema/workbook real):
{producto_ctx}

PRECIO: {precio} | GARANTÍA: {garantia} | GANCHO DEL ANUNCIO: {gancho}
"""
                if feed2:
                    prompt += f"\n=== INTELIGENCIA ICAI (SPCE_FEED) ===\n{feed2}\n"
                prompt += """
Genera el Brief de Construcción completo para Lovable:
1) Sistema de Diseño (mobile-first, paleta, tipografía).
2) Bloques en orden: Hero → Problema/Agitación → Solución (módulos prácticos) → Demo visual (placeholder) → Oferta+Precio+Garantía → FAQ estratégico → CTA final. Copy EXACTO de cada bloque.
3) Instrucciones técnicas (placeholders sin stock, botones full-width, acordeón FAQ).
4) Auditoría CRO final (score 0-10, riesgos, próximos pasos)."""
                try:
                    client = obs.cliente_observado(api_key, MODEL_ID)
                    response = client.messages.create(
                        model=MODEL_ID, max_tokens=8000,
                        system=SPCE_SYSTEM,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.success("Brief de landing generado.", icon=":material/check_circle:")
                    st.caption(obs.last_line())
                    st.markdown(response.content[0].text)
                    st.download_button("Descargar el brief", data=response.content[0].text,
                                       file_name="brief_landing.txt", mime="text/plain",
                                       width="stretch", icon=":material/download:")
                except Exception as e:
                    st.error(f"Error: {str(e)}", icon=":material/error:")
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# MODO 4: DESIGN PACK (Canva / Gamma / Bing)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] == 'design':
    try:
        import design_pack
        design_pack.render(api_key, MODEL_ID, st.session_state.get('producto_html'))
    except Exception as e:
        st.error(f"Módulo Design Pack no disponible: {e}", icon=":material/error:")
        st.markdown("El archivo `design_pack.py` debe estar junto a `app.py` (y en la raíz del repo).")
        if st.button("Volver al menú", key="v4", icon=":material/arrow_back:"):
            st.session_state['modo_seleccionado'] = None
            st.rerun()
