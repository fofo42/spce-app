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
# ═══════════════════════════════════════════════════════════════
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
            delete_config(); st.rerun()
    else:
        api_key_input = st.text_input("API Key de Anthropic", type="password")
        api_key = api_key_input.strip() if api_key_input else ""
        if api_key and st.checkbox("💾 Recordar para futuras sesiones"):
            save_config(api_key, saved_model); st.rerun()

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

SALIDA EXACTA EN 3 BLOQUES CON ESTOS SEPARADORES:
=== FIN_AUDIT ===
(AUDITORÍA INGENIERIL breve en español: Transformation Map en 3 líneas; tabla de pilares [Pilar|Insight|Need|Deliverable|Formato]; Deliverable Matrix [ID|Nombre|Formato|Problema que resuelve|DQS|Decisión]; entregables RECHAZADOS o FUSIONADOS con su motivo; UNKNOWNs y warnings.)
(Después, HTML COMPLETO del WORKBOOK: <html><head><style> para A4 </style></head><body> con portada centrada (nombre + promesa DE→A + qué incluye) y una sección <h1> por pilar con sus entregables APROBADOS: tablas con bordes, casillas &#9744;, espacios de escritura, cajas de consejo/advertencia, saltos class="page-break". Cero relleno.)
=== FIN_DEL_PDF ===
(ROADMAP: estructura de carpetas OFFER/01_CORE_TRANSFORMATION…07_BONUSES indicando qué entregable va en cada una; qué crear con Claude, qué con Gamma, qué con hoja de cálculo; orden de creación y dependencias; instrucciones de maquetación.)
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
        if st.button("🧭 ICAI (Paso 0)", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'icai'; st.rerun()
    with c2:
        if st.button("📦 Modelar Producto", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'producto'; st.rerun()
    with c3:
        if st.button("🚀 Modelar Landing", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'landing'; st.rerun()
    with c4:
        if st.button("🔄 Flujo Completo", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'completo'; st.rerun()
    with c5:
        if st.button("🎨 Design Pack", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'design'; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    - **🧭 ICAI (Paso 0)**: modela al cliente y su decisión; genera los puentes OFFER_FEED / SPCE_FEED / DESIGN_FEED.
    - **📦 Modelar Producto**: Offer Engine V1.0.1: auditoría con DQS + Workbook PDF + Roadmap de carpetas.
    - **🚀 Modelar Landing**: brief de página de ventas para Lovable.
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
# FASE 1: MODELAR PRODUCTO (OFFER ENGINE V1.0.1)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] in ['producto', 'completo']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("📦 FASE 1: Offer Engine V1.0.1 — Modelar Nuevo Producto")

    if st.button("⬅️ Volver al menú", key="v1"):
        st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False})
        st.rerun()

    feed0 = st.session_state.get('icai_offer_feed', '')
    if feed0:
        st.info("🧠 Inteligencia ICAI conectada: el Offer Engine usará el OFFER_FEED del dossier de cliente.")

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

    st.markdown("#### 📄 B) TU PRODUCTO a modelar *(el contenido real)*")
    uploaded_producto = st.file_uploader("Sube TU producto (PDF/PNG/JPG)",
        type=['pdf', 'png', 'jpg', 'jpeg'], accept_multiple_files=True, key="prod_files")
    descripcion_producto = st.text_area("O describe tu producto si no tienes archivos", height=90)

    c3, c4 = st.columns(2)
    with c3:
        avatar = st.text_input("Avatar/Público Objetivo", placeholder="Ej: mujeres sin tiempo para cocinar")
    with c4:
        transformacion = st.text_input("Transformación deseada", placeholder="Ej: cocinar 2 veces/semana y tener comida para 7 días")

    if st.button("🧠 Ejecutar Motor V1.0.1 (Auditoría + Workbook + Roadmap)", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Introduce tu API Key en la barra lateral")
        elif not uploaded_producto and not descripcion_producto.strip():
            st.error("⚠️ Falta TU PRODUCTO: sube archivos en el Bloque B o descríbelo.")
        else:
            with st.spinner("🧠 Ejecutando State Machine: extracción → pilares → gaps → DQS → arquitectura → validación..."):
                ref_texto, ref_bloques = procesar_archivos(uploaded_ref, "REFERENCIA DE ESTILO")
                prod_texto, prod_bloques = procesar_archivos(uploaded_producto, "PRODUCTO A MODELAR")

                contenido = []
                if feed0:
                    contenido.append({"type": "text", "text":
                        f"=== INTELIGENCIA ICAI (OFFER_FEED) ===\nContexto prioritario de cliente:\n{feed0}"})
                contenido.append({"type": "text", "text": f"""=== REFERENCIA DE ESTILO/MODELADO ===
(Úsala SOLO para estilo/patrones/técnicas. NO copies su contenido.)
URL: {referencia_url or '-'}
Descripción: {descripcion_ref or '-'}
{ref_texto}"""})
                contenido.extend(ref_bloques)
                contenido.append({"type": "text", "text": f"""=== PRODUCTO REAL A MODELAR ===
(Contenido base. Construye el producto SUPERIOR a partir de aquí.)
{prod_texto}
Descripción adicional: {descripcion_producto or '-'}"""})
                contenido.extend(prod_bloques)
                contenido.append({"type": "text", "text": f"""DATOS DEL PROYECTO:
TIPO: {tipo_producto} | AVATAR: {avatar} | TRANSFORMACIÓN: {transformacion}

INSTRUCCIÓN: Ejecuta tu proceso interno completo (9 pasos) y entrega los 3 bloques con separadores exactos."""})

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
                    st.success("✅ Motor V1.0.1 completado: auditoría, workbook y roadmap generados.")
                    st.caption(obs.last_line())
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    if st.session_state['producto_html']:
        if st.session_state['producto_audit']:
            with st.expander("🧾 Auditoría Ingenieril (Quality Gates, DQS y decisiones)", expanded=False):
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
                st.markdown("### 🗂️ Roadmap de Carpetas y Creación con IA")
                st.markdown(st.session_state['producto_roadmap'])

        if st.session_state['modo_seleccionado'] == 'completo':
            st.markdown("---")
            st.subheader("¿El producto te convence? ¿Continuamos con la Landing?")
            c7, c8 = st.columns(2)
            with c7:
                if st.button("✅ Sí, crear Landing", use_container_width=True):
                    st.session_state['continuar_landing'] = True; st.rerun()
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
        st.info("🧠 Inteligencia ICAI conectada: el SPCE usará el SPCE_FEED (mensajes por awareness, hooks, objeciones→FAQ).")

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
            st.error("⚠️ Introduce tu API Key")
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
        st.error(f"⚠️ Módulo Design Pack no disponible: {e}")
        st.markdown("El archivo `design_pack.py` debe estar junto a `app.py` (y en la raíz del repo).")
        if st.button("⬅️ Volver al menú", key="v4"):
            st.session_state['modo_seleccionado'] = None
            st.rerun()