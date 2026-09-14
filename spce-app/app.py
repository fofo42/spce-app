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
# TEMA OSCURO
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="Ecosistema Unificado", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); }
    h1, h2, h3 { color: #00d4ff !important; text-shadow: 0 0 10px rgba(0, 212, 255, 0.3); }
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

st.title("🧠 ECOSISTEMA UNIFICADO: Offer Engine + SPCE")
st.markdown("*Modela productos de alto valor (Workbook PDF) y crea landings de alta conversión.*")

# ═══════════════════════════════════════════════════════════════
# SIDEBAR: API KEY + SELECTOR DE MODELO
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

# ═══════════════════════════════════════════════════════════════
# ESTADO DE SESIÓN
# ═══════════════════════════════════════════════════════════════
for k, v in {"modo_seleccionado": None, "producto_html": None,
             "instrucciones_ia": None, "continuar_landing": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ═══════════════════════════════════════════════════════════════
# PROMPTS MAESTROS
# ═══════════════════════════════════════════════════════════════
OFFER_SYSTEM = """Eres el OFFER MODELING & ENGINEERING ENGINE (V1.0.1).

PRINCIPIOS INVARIABLES:
- TRANSFORMATION FIRST: la oferta se construye alrededor de la transformación, no de la cantidad de contenido.
- PROBLEM TO DELIVERABLE: cada problema relevante se convierte en un entregable.
- ACTION OVER INFORMATION: prioriza CHECKLIST, WORKSHEET, TRACKER, TEMPLATE, SCORECARD, PROTOCOL, ROUTINE y DECISION TOOL. GUIDE solo como último recurso.
- SIMPLICITY: comprensible para principiantes absolutos.
- PRINTABILITY: todo entregable debe poder imprimirse y rellenarse (casillas, tablas, espacios de escritura).
- NO FILLER: ningún entregable de relleno. Cantidad ≠ valor.
- NO INVENTION: nunca inventes resultados, testimonios, credenciales, garantías ni datos. Si falta información: UNKNOWN.

LOS 6 PILARES OBLIGATORIOS (cada uno produce INSIGHT → NEED → SOLUTION → DELIVERABLE):
P01 TRANSFORMATION DIFFICULTY: lo más difícil para lograr la transformación.
P02 SPEED TO RESULT: cómo llegar más rápido al resultado.
P03 PROCESS SUPPORT: qué acompaña al usuario durante el proceso.
P04 FUTURE PROBLEM PREVENTION: problemas futuros que pueden prevenirse.
P05 BLIND SPOTS: problemas que el cliente aún no sabe que tendrá.
P06 PROCESS MEASUREMENT: cómo medir el progreso.

OBJETIVO: Minimum Viable Transformation System. La menor arquitectura capaz de cubrir los obstáculos esenciales, con alto valor percibido y baja fricción. NO copies la referencia: modélala y supérala.

FORMATO DE SALIDA OBLIGATORIO:
PARTE A: Documento HTML completo y autocontenido (incluye <html>, <head> con <style> para A4, y <body>) tipo WORKBOOK profesional:
- Portada centrada: nombre del producto + promesa (DE: estado actual → A: estado deseado) + lista de qué incluye.
- Una sección <h1> por cada uno de los 6 PILARES con sus entregables prácticos: tablas con bordes, casillas &#9744;, espacios de escritura (div con borde inferior), cajas de consejo/advertencia y saltos de página (class="page-break").
- Cero texto de relleno. Todo accionable.
PARTE B (tras el separador): instrucciones paso a paso para maquetar este contenido en Gamma / Canva / Notion + estructura de carpetas recomendada (01_CORE_TRANSFORMATION, 02_SPEED, 03_SUPPORT, 04_PREVENTION, 05_BLIND_SPOTS, 06_MEASUREMENT, 07_BONUSES).
SEPARADOR EXACTO entre Parte A y Parte B: === FIN_DEL_PDF ===
No escribas nada fuera de esas dos partes."""

SPCE_SYSTEM = """Eres el SALES PAGE CONVERSION ENGINE (SPCE).
REGLAS: Mobile-First, Anti-Invención, Message Match, Beneficios > Características, CTA en primera persona repetido 3+ veces.
Vendes el WORKBOOK/SISTEMA generado (destaca su valor práctico, no teórico). Nunca inventes testimonios, cifras ni escasez."""

# ═══════════════════════════════════════════════════════════════
# MENÚ INICIAL
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] is None:
    st.markdown('<div class="menu-card">', unsafe_allow_html=True)
    st.subheader("¿Qué quieres hacer hoy?")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📦 Modelar Producto", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'producto'; st.rerun()
    with c2:
        if st.button("🚀 Modelar Landing", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'landing'; st.rerun()
    with c3:
        if st.button("🔄 Flujo Completo", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'completo'; st.rerun()
    with c4:
        if st.button("🎨 Design Pack", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'design'; st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    - **📦 Modelar Producto**: sube una referencia (PDF/captura/URL) y crea un producto superior en formato Workbook PDF.
    - **🚀 Modelar Landing**: genera el brief de página de ventas para Lovable.
    - **🔄 Flujo Completo**: primero el producto; si te convence, pasas a la landing. Si no, te ahorras el proceso.
    """)
    st.stop()

# ═══════════════════════════════════════════════════════════════
# FASE 1: MODELAR PRODUCTO (OFFER ENGINE)
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] in ['producto', 'completo']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("📦 FASE 1: Offer Engine — Modelar Nuevo Producto")

    if st.button("⬅️ Volver al menú", key="v1"):
        st.session_state.update({'modo_seleccionado': None, 'continuar_landing': False})
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        referencia_url = st.text_input("URL de la referencia (opcional)")
        uploaded_ref = st.file_uploader("Sube referencia (PDF / PNG / JPG)", type=['pdf', 'png', 'jpg', 'jpeg'])
        descripcion_ref = st.text_area("Descripción de la referencia (opcional)", height=90)
    with c2:
        tipo_producto = st.selectbox("Tipo de producto",
            ["Ebook/Guía", "Plantilla de Notion", "Curso Online", "Libro de Recetas",
             "Software/SaaS", "Servicio", "Otro"])
        avatar = st.text_input("Avatar/Público Objetivo", placeholder="Ej: mujeres sin tiempo para cocinar")
        transformacion = st.text_input("Transformación deseada", placeholder="Ej: cocinar 2 veces/semana y tener comida para 7 días")

    if st.button("🧠 Analizar y Generar Producto de Alto Valor", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Introduce tu API Key en la barra lateral")
        else:
            with st.spinner("🔍 Aplicando 6 Pilares, detectando gaps y diseñando entregables prácticos..."):
                # Contexto de la referencia
                contexto = ""
                if referencia_url:
                    contexto += f"URL: {referencia_url}\n"
                if descripcion_ref:
                    contexto += f"Descripción: {descripcion_ref}\n"

                contenido_mensaje = []
                if uploaded_ref is not None:
                    if uploaded_ref.type == "application/pdf":
                        try:
                            from pypdf import PdfReader
                            reader = PdfReader(io.BytesIO(uploaded_ref.read()))
                            texto_pdf = "\n".join([p.extract_text() or "" for p in reader.pages])
                            contexto += f"TEXTO EXTRAÍDO DEL PDF:\n{texto_pdf[:12000]}\n"
                        except Exception as e:
                            st.warning(f"⚠️ No se pudo leer el PDF: {e}")
                    elif uploaded_ref.type in ["image/png", "image/jpeg"]:
                        contenido_mensaje.append({
                            "type": "image",
                            "source": {"type": "base64",
                                       "media_type": uploaded_ref.type,
                                       "data": base64.b64encode(uploaded_ref.read()).decode('utf-8')}
                        })

                prompt_usuario = f"""REFERENCIA A MODELAR (no copiar, superar):
{contexto if contexto else '(sin referencia textual; analiza la imagen adjunta si existe)'}

TIPO DE PRODUCTO: {tipo_producto}
AVATAR: {avatar}
TRANSFORMACIÓN DESEADA: {transformacion}

Diseña el NUEVO PRODUCTO SUPERIOR completo siguiendo tus 6 pilares y formato de salida obligatorio."""

                contenido_mensaje.append({"type": "text", "text": prompt_usuario})

                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(
                        model=MODEL_ID,
                        max_tokens=16000,
                        system=OFFER_SYSTEM,
                        messages=[{"role": "user", "content": contenido_mensaje}]
                    )
                    full_output = response.content[0].text

                    if "=== FIN_DEL_PDF ===" in full_output:
                        html_part, instr_part = full_output.split("=== FIN_DEL_PDF ===", 1)
                    else:
                        html_part, instr_part = full_output, "(sin instrucciones separadas)"

                    st.session_state['producto_html'] = html_part.strip()
                    st.session_state['instrucciones_ia'] = instr_part.strip()
                    st.success("✅ ¡Producto de Alto Valor diseñado!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    # ── Resultados Fase 1 ──
    if st.session_state['producto_html']:
        st.markdown("### 📄 Vista Previa del Workbook:")
        st.markdown(st.session_state['producto_html'], unsafe_allow_html=True)

        c3, c4 = st.columns(2)
        with c3:
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
        with c4:
            st.markdown("### 🎨 Instrucciones Gamma/Canva/Notion")
            st.markdown(st.session_state['instrucciones_ia'])

        # Puerta de decisión (Flujo Completo)
        if st.session_state['modo_seleccionado'] == 'completo':
            st.markdown("---")
            st.subheader("¿El producto te convence? ¿Continuamos con la Landing?")
            c5, c6 = st.columns(2)
            with c5:
                if st.button("✅ Sí, crear Landing", use_container_width=True):
                    st.session_state['continuar_landing'] = True; st.rerun()
            with c6:
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

    if st.session_state['continuar_landing'] and st.session_state['producto_html']:
        st.info("✅ Usando el producto modelado en la Fase 1 como base")
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

Genera el Brief de Construcción completo para Lovable:
1) Sistema de Diseño (mobile-first, paleta, tipografía).
2) Bloques en orden: Hero → Problema/Agitación → Solución (módulos prácticos del producto) → Demo visual (placeholder) → Oferta+Precio+Garantía → FAQ estratégico → CTA final. Copy EXACTO de cada bloque.
3) Instrucciones técnicas (placeholders sin stock, botones full-width, acordeón FAQ).
4) Auditoría CRO final (score 0-10, riesgos, próximos pasos)."""
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(
                        model=MODEL_ID,
                        max_tokens=8000,
                        system=SPCE_SYSTEM,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.success("✅ ¡Brief de Landing generado!")
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
        st.error(f"⚠️ Módulo Design Pack no disponible: {e}. Sube design_pack.py al repositorio.")
