import observability as obs
import streamlit as st
import anthropic
import io
import json
import os
import re
import base64
from xhtml2pdf import pisa

# ═══════════════════════════════════════════════════════════════
# MEMORIA LOCAL (API KEY + MODELO)
# ══════════════════════════════════════════════════════════════
CONFIG_FILE = "local_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(api_key, model_id):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"api_key": api_key, "model_id": model_id}, f)

def delete_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

config = load_config()
saved_api_key = config.get("api_key", "")
saved_model = config.get("model_id", "claude-sonnet-4-5")

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
                st.warning(f"⚠️ PDF no legible: {f.name}")
        elif f.type in ["image/png", "image/jpeg"]:
            bloques.append({"type": "text", "text": f"[IMAGEN — {etiqueta}: {f.name}]"})
            bloques.append({"type": "image", "source": {"type": "base64",
                "media_type": f.type, "data": base64.b64encode(f.read()).decode()}})
    return texto, bloques

# ═══════════════════════════════════════════════════════════════
# TEMA OSCURO
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="Ecosistema Unificado", page_icon="🧠", layout="wide")

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
</style>
""", unsafe_allow_html=True)

st.title("🧠 ECOSISTEMA UNIFICADO: ICAI + Offer Engine + SPCE")
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
    st.header("⚙️ Configuración")
    if saved_api_key:
        st.success("✅ API Key cargada automáticamente")
        api_key = st.text_input("API Key de Anthropic", value=saved_api_key, type="password")
        if api_key != saved_api_key:
            save_config(api_key, saved_model)
        if st.button("🗑️ Borrar API Key guardada", use_container_width=True):
            delete_config()
            st.rerun()
    else:
        api_key_input = st.text_input("API Key de Anthropic", type="password")
        api_key = api_key_input.strip() if api_key_input else ""
        if api_key and st.checkbox("💾 Recordar para futuras sesiones"):
            save_config(api_key, saved_model)
            st.rerun()

    st.markdown("---")
    nombres = list(MODELOS.keys())
    idx = 0
    for i, k in enumerate(nombres):
        if MODELOS[k] == saved_model:
            idx = i
    modelo_sel = st.selectbox("Modelo de IA", nombres, index=idx)
    MODEL_ID = MODELOS[modelo_sel]
    if MODEL_ID != saved_model:
        save_config(api_key if api_key else saved_api_key, MODEL_ID)
    st.markdown("---")
    st.info("💡 Key gratis: [console.anthropic.com](https://console.anthropic.com)")

    # Indicador de ICAI disponible
    if st.session_state.get('icai_ready'):
        st.success(" ICAI activo en sesión")
    else:
        st.warning("⚠️ Sin ICAI en sesión")

    obs.render_sidebar()

# ═══════════════════════════════════════════════════════════════
# ESTADO DE SESIÓN
# ═══════════════════════════════════════════════════════════════
for k, v in {"modo_seleccionado": None, "producto_html": None,
             "producto_audit": None, "producto_roadmap": None,
             "continuar_landing": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════
# PROMPTS MAESTROS — CEREBRO PROFUNDO V1.0.1
# ═══════════════════════════════════════════════════════════════
OFFER_SYSTEM = """Eres el OFFER MODELING & ENGINEERING ENGINE V1.0.1 — sistema completo de 12 módulos.

=== V1.0.1.00 SYSTEM CONTRACT ===
INVARIANTES (SIEMPRE ACTIVOS):
INV-01 NO INVENTION: nunca inventes resultados, testimonios, credenciales, estudios, garantías, precios ni datos.
INV-02 TRANSFORMATION FIRST: la oferta se construye alrededor de la transformación, no del volumen de contenido.
INV-03 EVIDENCE ≠ INFERENCE ≠ HYPOTHESIS: separa siempre. Si falta información: UNKNOWN.
INV-04 PRACTICALITY > CONTENT VOLUME: prioriza CHECKLIST, WORKSHEET, TRACKER, TEMPLATE, SCORECARD, DECISION TOOL, PROTOCOL, ROUTINE, QUICK REFERENCE. GUIDE solo como último recurso justificado.
INV-05 BEGINNER-FIRST: comprensible sin conocimientos previos, sin jerga.
INV-06 PRINTABILITY: espacios de escritura, casillas &#9744;, tablas, campos, instrucciones cortas.
INV-07 REDUNDANCY CONTROL: dos entregables que resuelven el mismo problema → MERGE o REMOVE.
INV-08 CORE ≠ BONUS: si un componente es necesario para la transformación, es CORE, nunca bonus decorativo.
INV-09 BONUS RULE: todo bonus debe resolver un problema secundario, acelerar resultado, prevenir error o aumentar implementación. Si no: REJECT.
INV-10 ANTI-FILLER: nunca añadas activos solo para aumentar cantidad. 5 útiles > 30 genéricos.
INV-11 VALUE DENSITY: maximiza PRACTICAL_VALUE / USER_EFFORT.
INV-12 OFFER EFFICIENCY: TRANSFORMATION_COVERAGE / DELIVERABLE_COMPLEXITY.
INV-13 TRACEABILITY: todo entregable debe responder "¿Qué problema resuelve? ¿Qué pilar cubre? ¿Por qué este formato?".
INV-14 CLAIM CONTROL: toda afirmación sobre resultados/autoridad debe rastrearse o marcarse HYPOTHESIS.
INV-15 MODELING ≠ COPYING: modela la lógica, nunca copies nombres/textos/branding/testimonios.

=== V1.0.1.01 SKILL MASTER ===
Modo de pensar: CUSTOMER → DESIRED TRANSFORMATION → OBSTACLES → NEEDS → SOLUTIONS → DELIVERABLES → OFFER.
Nunca razonar desde "¿Qué PDF añadimos?". Siempre desde "¿Qué obstáculo sigue sin resolverse?".

=== V1.0.1.02 DEFINITIVE SCHEMAS ===
Schema canónico de entregable (11 campos):
ID | Nombre | Pilar (P01-P06) | Problema resuelto | Obstáculo eliminado | Etapa de transformación | Formato (D01-D15) | Target user (BEGINNER/INTERMEDIATE/ADVANCED) | Cuándo se usa | Cómo se usa | Resultado esperado
Formatos canónicos: D01 CHECKLIST | D02 WORKSHEET | D03 TRACKER | D04 TEMPLATE | D05 SCORECARD | D06 QUICK REFERENCE | D07 DECISION TOOL | D08 ACTION PLAN | D09 EXERCISE | D10 CALCULATOR | D11 DIAGNOSTIC | D12 ROUTINE | D13 PROTOCOL | D14 LOG | D15 GUIDE (último recurso).

=== V1.0.1.03 STATE MACHINE (9 pasos obligatorios) ===
S01 EXTRAER producto base (qué vende, a quién, qué promete, qué mecanismo usa).
S02 TRANSFORMATION MAP: CURRENT STATE → STAGES → DESIRED STATE (con criterios de éxito).
S03 CLIENTE Y OBSTÁCULOS: avatar real + obstáculos por categoría (knowledge/skill/decision/action/consistency/motivation/time/resources/confusion/fear/error/measurement/maintenance).
S04 SEIS PILARES: P01 Dificultad | P02 Velocidad | P03 Acompañamiento | P04 Prevención futura | P05 Puntos ciegos | P06 Medición.
S05 GAP ANALYSIS: PROMESA vs REQUISITOS REALES y ENTREGABLES EXISTENTES vs NECESIDADES. Prioridad = IMPACTO × FRECUENCIA × URGENCIA × RIESGO.
S06 ENGINEERING DE ENTREGABLES: GAP → ROOT PROBLEM → NEED → SOLUTION → FORMAT (IF/THEN) → DELIVERABLE.
S07 EVALUACIÓN DQS + GATES: cada entregable recibe DQS y pasa gates.
S08 ARQUITECTURA: CORE → SUPPORT → MEASUREMENT → PREVENTION → BONUSES.
S09 VALIDACIÓN FINAL: ¿Cubre transformación? ¿6 pilares? ¿Gaps críticos resueltos? ¿Práctico? ¿Simple? ¿Trazable?

=== V1.0.1.04–.05 TOOL CAPABILITY + ADAPTER ===
Tool-agnostic. No asumas herramienta concreta. Identifica CAPABILITY → ACTION → TOOL.
AI CREATION LAYER: para cada entregable indica qué crear con Claude (texto/estructura), qué con Gamma (visual/guía), qué con hoja de cálculo (tracker/calculator), qué con código (calculator avanzado).

=== V1.0.1.06 I/O CONTRACTS ===
Input: NICHE + PRODUCT (obligatorios) + REFERENCIA ESTILO (opcional) + INTELIGENCIA ICAI (opcional).
Output: 3 bloques con separadores exactos (ver abajo).
Epistémico: I0 UNKNOWN | I1 USER_PROVIDED | I2 DOCUMENTED | I3 EXTERNALLY_VERIFIED | I4 SYSTEM_DERIVED | I5 HYPOTHESIS.

=== V1.0.1.07 QUALITY GATES ===
DQS = 0.20×Problem_Relevance + 0.20×Transformation_Impact + 0.15×Practicality + 0.15×Ease_of_Use + 0.10×Printability + 0.10×Perceived_Value + 0.10×Complementarity
Escala 0-100. Decisiones:
≥85 → ACCEPT | 70-84 → ACCEPT_WITH_IMPROVEMENT | 55-69 → IMPROVE | 40-54 → SIMPLIFY/REDESIGN | <40 → REJECT
HARD GATES (bloquean aceptación): no accionable → REJECT | sin relevancia de transformación → REJECT | redundante → MERGE | demasiado complejo para avatar → SIMPLIFY | no imprimible siendo práctico → REWORK | guía cuando existe formato práctico → REFORMAT.
BEGINNER GATE: ¿puede entenderlo, iniciarlo, completarlo y verificar resultado un principiante?
REDUNDANCY GATE: mismo propósito + mismo problema + misma acción → MERGE.

=== V1.0.1.08 ERROR & RECOVERY ===
Si un entregable falla gate: REWORK local (no reiniciar todo). Si falta información crítica: marcar UNKNOWN y continuar con confianza reducida. Si conflicto de fuentes: preservar ambos y marcar CONFLICT.

=== V1.0.1.09 PROJECT MEMORY ===
Si detectas patrones de ofertas similares a esta, menciónalos brevemente como "lecciones aplicadas".

=== V1.0.1.10–.12 TEST + AUTONOMY + INTEGRATION ===
Validación final: ¿Pasaría los 15 invariantes? ¿Trazabilidad completa? ¿Sin claims sin soporte? ¿Bonus realmente no-core?

=== SELECCIÓN DE FORMATO (IF/THEN) ===
IF necesita comprobar → CHECKLIST | completar → WORKSHEET | registrar → TRACKER/LOG | reutilizar → TEMPLATE | medir → SCORECARD | diagnosticar → DIAGNOSTIC | decidir → DECISION TOOL | ejecutar → PROTOCOL/ACTION PLAN | practicar → EXERCISE | consultar rápido → QUICK REFERENCE | calcular → CALCULATOR | rutinizar → ROUTINE | comprender antes de actuar → GUIDE (último recurso).

=== SALIDA EXACTA EN 3 BLOQUES ===
=== FIN_AUDIT ===
(AUDITORÍA INGENIERIL completa en español:
1. Transformation Map en 3 líneas: CURRENT → STAGES → DESIRED.
2. Tabla de 6 pilares: [Pilar | Insight | Need | Deliverable | Formato | DQS | Decisión].
3. Deliverable Matrix completa: [ID | Nombre | Pilar | Problema | Formato | Target | DQS | Decisión].
4. Entregables RECHAZADOS con motivo (qué gate falló).
5. Entregables FUSIONADOS con motivo (qué duplicidad detectaste).
6. Entregables SIMPLIFICADOS con motivo.
7. UNKNOWNs explícitos y qué recolectar para resolverlos.
8. Warnings (claims sin soporte, bonus borderline, etc.).
9. Lecciones aplicadas de memoria si corresponde.)
(Después, HTML COMPLETO del WORKBOOK: <html><head><style> para A4 </style></head><body> con portada centrada (nombre + promesa DE→A + qué incluye) y una sección <h1> por pilar con sus entregables APROBADOS: tablas con bordes, casillas &#9744;, espacios de escritura, cajas de consejo/advertencia, saltos class="page-break". Cero relleno.)
=== FIN_DEL_PDF ===
(ROADMAP completo:
1. Estructura de carpetas OFFER/01_CORE_TRANSFORMATION/02_SPEED/03_SUPPORT/04_PREVENTION/05_BLIND_SPOTS/06_MEASUREMENT/07_BONUSES indicando qué entregable va en cada una.
2. AI CREATION LAYER: qué crear con Claude, qué con Gamma, qué con hoja de cálculo, qué con código.
3. Orden de creación y dependencias.
4. Instrucciones de maquetación para el PDF final.)
No escribas nada fuera de esos 3 bloques."""

SPCE_SYSTEM = """Eres el SALES PAGE CONVERSION ENGINE (SPCE).
REGLAS: Mobile-First, Anti-Invención, Message Match, Beneficios > Características, CTA en primera persona repetido 3+ veces.
Vendes el WORKBOOK/SISTEMA generado (destaca su valor práctico, no teórico). Nunca inventes testimonios, cifras ni escasez."""

# ═══════════════════════════════════════════════════════════════
# MENÚ INICIAL (5 MODOS)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] is None:
    st.markdown('<div class="menu-card">', unsafe_allow_html=True)
    st.subheader("¿Qué quieres hacer hoy?")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button(" ICAI (Paso 0)", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'icai'
            st.rerun()
    with c2:
        if st.button("📦 Modelar Producto", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'producto'
            st.rerun()
    with c3:
        if st.button("🚀 Modelar Landing", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'landing'
            st.rerun()
    with c4:
        if st.button(" Flujo Completo", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'completo'
            st.rerun()
    with c5:
        if st.button(" Design Pack", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'design'
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
- **🧭 ICAI (Paso 0)**: modela al cliente y su decisión; genera los puentes OFFER_FEED / SPCE_FEED / DESIGN_FEED.
- **📦 Modelar Producto**: Offer Engine V1.0.1 con cerebro profundo (12 módulos): auditoría con DQS real + Workbook PDF + Roadmap.
- ** Modelar Landing**: brief de página de ventas para Lovable.
- **🔄 Flujo Completo**: primero el producto; si te convence, pasas a la landing.
- **🎨 Design Pack**: prompts listos para Canva/Gamma/Bing con tu estilo visual.
    """)
    st.stop()

# ═══════════════════════════════════════════════════════════════
# MODO 0: ICAI (CAPA DE INTELIGENCIA DE CLIENTE)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] == 'icai':
    try:
        import icai_engine
        icai_engine.render(api_key, MODEL_ID)
    except Exception as e:
        st.error(f"⚠️ Módulo ICAI no disponible: {e}")
        st.markdown("El archivo `icai_engine.py` debe estar junto a `app.py` (y en la raíz del repo).")
        if st.button("⬅️ Volver al menú", key="v7"):
            st.session_state['modo_seleccionado'] = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════
# FASE 1: MODELAR PRODUCTO (OFFER ENGINE V1.0.1 — CEREBRO PROFUNDO)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] in ['producto', 'completo']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader(" FASE 1: Offer Engine V1.0.1 — Cerebro Profundo (12 módulos)")

    if st.button("⬅️ Volver al menú", key="v1"):
        st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False})
        st.rerun()

    # === DETECCIÓN ROBUSTA DE ICAI ===
    feed0 = st.session_state.get('icai_offer_feed', '')
    icai_ready = st.session_state.get('icai_ready', False)
    tiene_icai = bool(feed0) and icai_ready

    if tiene_icai:
        st.success("🧠 Inteligencia ICAI conectada: el Offer Engine usará el OFFER_FEED del dossier de cliente.")
        with st.expander("️ Ver contenido del OFFER_FEED", expanded=False):
            st.text(feed0[:500] + ("..." if len(feed0) > 500 else ""))
    else:
        st.warning("⚠️ Sin ICAI en sesión. El Offer Engine funcionará en modo clásico (requiere producto base).")
        st.info("💡 Para activar el modo 'Diseñar desde cero', ejecuta primero el Paso 0 (ICAI).")
        if st.button("🧭 Ir al Paso 0 (ICAI)", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'icai'
            st.rerun()

    # ── Selector de modo ──
    st.markdown("#### 🔧 Modo de trabajo")
    if tiene_icai:
        modo = st.radio(
            "¿Cómo quieres construir el producto?",
            [
                " Diseñar desde cero (solo con inteligencia de cliente + referencia de estilo)",
                "♻️ Remodelar un producto existente (aportar producto base para superar)",
            ],
            index=0,
            horizontal=True,
        )
        desde_cero = modo.startswith("🆕")
    else:
        desde_cero = False

    # ── Bloque A: Referencia de estilo ──
    st.markdown("#### 🎯 A) Referencia de estilo y modelado *(cómo debe quedar)*")
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

    # ── Bloque B: Producto base (opcional en modo desde-cero) ──
    st.markdown("####  B) Producto base *(opcional en modo 'Diseñar desde cero')*")
    if desde_cero:
        st.markdown("*El Offer Engine diseñará el producto usando la inteligencia de cliente + la referencia de estilo. Si quieres aportar un producto base como inspiración adicional, puedes hacerlo aquí.*")
    uploaded_producto = st.file_uploader("Sube TU producto base (PDF/PNG/JPG) — opcional",
        type=['pdf', 'png', 'jpg', 'jpeg'], accept_multiple_files=True, key="prod_files")
    descripcion_producto = st.text_area("O describe brevemente el producto base (opcional)", height=90)

    c3, c4 = st.columns(2)
    with c3:
        avatar = st.text_input("Avatar/Público Objetivo", placeholder="Ej: mujeres sin tiempo para cocinar")
    with c4:
        transformacion = st.text_input("Transformación deseada", placeholder="Ej: cocinar 2 veces/semana y tener comida para 7 días")

    # ── Validación ──
    producto_aportado = bool(uploaded_producto) or bool(descripcion_producto.strip())
    if st.button("🧠 Ejecutar Motor V1.0.1 Profundo (State Machine + DQS + Quality Gates)", type="primary", use_container_width=True):
        if not api_key:
            st.error("️ Introduce tu API Key en la barra lateral")
        elif not desde_cero and not producto_aportado:
            st.error("⚠️ Falta TU PRODUCTO: sube archivos en el Bloque B o descríbelo (o activa el modo 'Diseñar desde cero').")
        else:
            modo_texto = "Diseño desde cero" if desde_cero else "Remodelado de producto base"
            with st.spinner(f"🧠 Ejecutando State Machine de 9 pasos ({modo_texto}): extracción → transformación → cliente → obstáculos → 6 pilares → gaps → DQS → arquitectura → validación..."):
                ref_texto, ref_bloques = procesar_archivos(uploaded_ref, "REFERENCIA DE ESTILO")
                prod_texto, prod_bloques = procesar_archivos(uploaded_producto, "PRODUCTO BASE")

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
                    contenido.append({"type": "text", "text": f"""=== PRODUCTO BASE A MODELAR ===
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
TIPO: {tipo_producto} | AVATAR: {avatar or '(inferir de ICAI)'} | TRANSFORMACIÓN: {transformacion or '(inferir de ICAI)'}
MODO: {'DISEÑO DESDE CERO (sin producto base)' if desde_cero else 'REMODELADO (con producto base)'}

INSTRUCCIÓN: {instruccion_final}"""})

                try:
                    client = obs.wrap_client(anthropic.Anthropic(api_key=api_key), MODEL_ID)
                    response = client.messages.create(
                        model=MODEL_ID, max_tokens=20000,
                        system=OFFER_SYSTEM,
                        messages=[{"role": "user", "content": contenido}]
                    )
                    full_output = response.content[0].text
                    audit, html_part, roadmap = "", full_output, ""
                    if "=== FIN_DEL_PDF ===" in full_output:
                        left, roadmap = full_output.split("=== FIN_DEL_PDF ===", 1)
                    else:
                        left = full_output
                    if "=== FIN_AUDIT ===" in left:
                        audit, html_part = left.split("=== FIN_AUDIT ===", 1)
                    st.session_state['producto_audit'] = audit.strip()
                    st.session_state['producto_html'] = html_part.strip()
                    st.session_state['producto_roadmap'] = roadmap.strip()
                    st.success("✅ Motor V1.0.1 Profundo completado: auditoría con DQS real, workbook y roadmap generados.")
                    st.caption(obs.last_line())
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    # ── Resultados ──
    if st.session_state['producto_html']:
        if st.session_state['producto_audit']:
            with st.expander("🧾 Auditoría Ingenieril (Quality Gates, DQS, entregables rechazados/fusionados)", expanded=False):
                st.markdown(st.session_state['producto_audit'])
        st.markdown("### 📄 Vista Previa del Workbook:")
        st.markdown(st.session_state['producto_html'], unsafe_allow_html=True)

        c5, c6 = st.columns(2)
        with c5:
            if st.button("📥 Descargar PDF del Producto", use_container_width=True):
                html_raw = st.session_state['producto_html']
                if "<html" in html_raw.lower():
                    full_html = html_raw
                else:
                    css = ("<style>body{font-family:Helvetica;color:#222;padding:40px;line-height:1.5;}"
                           "h1{color:#004466;border-bottom:3px solid #004466;padding-bottom:10px;}"
                           "h2{color:#006699;margin-top:25px;} table{width:100%;border-collapse:collapse;margin:15px 0;}"
                           "th,td{border:1px solid #ccc;padding:10px;text-align:left;} th{background:#f0f4f8;}</style>")
                    full_html = f"<html><head>{css}</head><body>{html_raw}</body></html>"
                buffer = io.BytesIO()
                pisa.CreatePDF(io.StringIO(full_html), dest=buffer)
                buffer.seek(0)
                st.download_button("⬇️ Guardar PDF Ahora", data=buffer,
                                   file_name="producto_alto_valor.pdf", mime="application/pdf")
        with c6:
            if st.session_state['producto_roadmap']:
                st.markdown("### 🗂️ Roadmap + AI Creation Layer")
                st.markdown(st.session_state['producto_roadmap'])

        if st.session_state['modo_seleccionado'] == 'completo':
            st.markdown("---")
            st.subheader("¿El producto te convence? ¿Continuamos con la Landing?")
            c7, c8 = st.columns(2)
            with c7:
                if st.button("✅ Sí, crear Landing", use_container_width=True):
                    st.session_state['continuar_landing'] = True
                    st.rerun()
            with c8:
                if st.button("❌ No, terminar aquí", use_container_width=True):
                    st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False})
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if not (st.session_state['modo_seleccionado'] == 'completo' and st.session_state['continuar_landing']):
        st.stop()

# ═══════════════════════════════════════════════════════════════
# FASE 2: MODELAR LANDING (SPCE)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] == 'landing' or st.session_state['continuar_landing']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("🚀 FASE 2: SPCE — Brief de Landing para Lovable")

    if st.button("⬅️ Volver al menú", key="v2"):
        st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False})
        st.rerun()

    feed2 = st.session_state.get('icai_spce_feed', '')
    if feed2:
        st.info(" Inteligencia ICAI conectada: el SPCE usará el SPCE_FEED (mensajes por awareness, hooks, objeciones→FAQ).")

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

    if st.button("🚀 Generar Brief de Landing", type="primary", use_container_width=True):
        if not api_key:
            st.error("️ Introduce tu API Key")
        elif not producto_ctx:
            st.error("⚠️ Falta el producto (genera la Fase 1 o descríbelo)")
        else:
            with st.spinner("🔍 Aplicando SPCE: arquitectura psicológica, copy y brief Mobile-First..."):
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
                    client = obs.wrap_client(anthropic.Anthropic(api_key=api_key), MODEL_ID)
                    response = client.messages.create(
                        model=MODEL_ID, max_tokens=8000,
                        system=SPCE_SYSTEM,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.success("✅ ¡Brief de Landing generado!")
                    st.caption(obs.last_line())
                    st.markdown(response.content[0].text)
                    st.download_button("📥 Descargar Brief", data=response.content[0].text,
                                       file_name="brief_landing.txt", mime="text/plain")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# MODO 4: DESIGN PACK (Canva / Gamma / Bing)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] == 'design':
    try:
        import design_pack
        design_pack.render(api_key, MODEL_ID, st.session_state.get('producto_html'))
    except Exception as e:
        st.error(f"️ Módulo Design Pack no disponible: {e}")
        st.markdown("El archivo `design_pack.py` debe estar junto a `app.py` (y en la raíz del repo).")
        if st.button("️ Volver al menú", key="v4"):
            st.session_state['modo_seleccionado'] = None
            st.rerun()