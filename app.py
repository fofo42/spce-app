import streamlit as st
import anthropic
import io
import json
import os
from xhtml2pdf import pisa

# ═══════════════════════════════════════════════════════════════
# SISTEMA DE MEMORIA LOCAL PARA LA API KEY
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

def save_config(api_key):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"api_key": api_key}, f)

def delete_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)

# Cargar configuración al inicio
config = load_config()
saved_api_key = config.get("api_key", "")

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA PÁGINA Y TEMA OSCURO
# ═══════════════════════════════════════════════════════════════
st.set_page_config(page_title="Ecosistema Unificado", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); }
    h1, h2, h3 { color: #00d4ff !important; text-shadow: 0 0 10px rgba(0, 212, 255, 0.3); }
    p, label, div { color: #e0e0e0 !important; }
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
st.markdown("*Modela productos de alto valor y crea landings de alta conversión*")

# ═══════════════════════════════════════════════════════════════
# SIDEBAR CON GESTIÓN INTELIGENTE DE LA API KEY
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Configuración")
    
    if saved_api_key:
        st.success("✅ API Key cargada automáticamente")
        api_key = st.text_input("API Key de Anthropic", value=saved_api_key, type="password")
        
        # Si el usuario la modifica, la actualizamos al instante
        if api_key != saved_api_key:
            save_config(api_key)
            st.success("✅ API Key actualizada y guardada")
            
        if st.button("🗑️ Borrar API Key guardada", use_container_width=True):
            delete_config()
            st.rerun()
    else:
        api_key = st.text_input("API Key de Anthropic", type="password")
        if api_key:
            if st.checkbox("💾 Recordar para futuras sesiones"):
                save_config(api_key)
                st.success("✅ Guardada localmente")
                st.rerun()
                
        st.markdown("---")
    modelos_disponibles = {
        "Claude Sonnet 4.5 (recomendado)": "claude-sonnet-4-5",
        "Claude Sonnet 4.5 (versión fija)": "claude-sonnet-4-5-20250929",
        "Claude Haiku 4.5 (rápido y barato)": "claude-haiku-4-5",
        "Claude Opus 4.5 (máxima potencia)": "claude-opus-4-5",
    }
    modelo_elegido = st.selectbox("Modelo de IA", list(modelos_disponibles.keys()))
    MODEL_ID = modelos_disponibles[modelo_elegido]

# ═══════════════════════════════════════════════════════════════
# GESTIÓN DE ESTADO DE LA APP (Menú secuencial)
# ═══════════════════════════════════════════════════════════════
if 'modo_seleccionado' not in st.session_state:
    st.session_state['modo_seleccionado'] = None

if 'producto_modelado' not in st.session_state:
    st.session_state['producto_modelado'] = False

# ═══════════════════════════════════════════════════════════════
# MENÚ INICIAL DE SELECCIÓN
# ═══════════════════════════════════════════════════════════════
if st.session_state['modo_seleccionado'] is None:
    st.markdown('<div class="menu-card">', unsafe_allow_html=True)
    st.subheader("¿Qué quieres hacer hoy?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📦 1. Modelar Producto", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'producto'
            st.rerun()
    
    with col2:
        if st.button("🚀 2. Modelar Landing", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'landing'
            st.rerun()
    
    with col3:
        if st.button("🔄 Flujo Completo", use_container_width=True):
            st.session_state['modo_seleccionado'] = 'completo'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 📋 Descripción de modos:
    - **📦 Modelar Producto**: Analiza una referencia y crea un producto superior (PDF con entregables prácticos).
    - **🚀 Modelar Landing**: Crea una página de ventas de alta conversión para un producto ya definido.
    - **🔄 Flujo Completo**: Primero modela el producto. Si te gusta el resultado, te preguntará si quieres crear la landing page.
    """)

# ═══════════════════════════════════════════════════════════════
# FASE 1: MODELAR PRODUCTO (OFFER ENGINE)
# ═══════════════════════════════════════════════════════════════
elif st.session_state['modo_seleccionado'] in ['producto', 'completo']:
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("📦 FASE 1: Modelar Nuevo Producto")
    st.markdown("Sube una referencia. La IA aplicará los 6 Pilares y diseñará un Producto Práctico de Alto Valor (Workbooks, Trackers, Checklists).")
    
    if st.button("⬅️ Volver al menú", key="volver_producto"):
        st.session_state['modo_seleccionado'] = None
        st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        referencia_url = st.text_input("URL de la referencia (opcional)")
        uploaded_ref = st.file_uploader("O sube captura/documento de referencia", type=['pdf', 'png', 'jpg', 'jpeg'])
    with col2:
        tipo_producto = st.selectbox("Tipo de producto", ["Ebook/Guía", "Plantilla de Notion", "Curso Online", "Libro de Recetas", "Software/SaaS", "Servicio", "Otro"])
        avatar = st.text_input("Avatar/Público Objetivo", placeholder="Ej: Freelancers creativos")
        transformacion = st.text_input("Transformación deseada", placeholder="Ej: Control total de sus finanzas en 10 min/día")
    
    if st.button("🧠 Analizar y Generar Producto", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Introduce tu API Key en la barra lateral")
        else:
            with st.spinner("🔍 Aplicando Offer Engine: 6 Pilares, Detección de Gaps y Diseño de Entregables..."):
                prompt_sistema = """Eres el OFFER MODELING & ENGINEERING ENGINE.
                REGLAS ABSOLUTAS:
                1. TRANSFORMATION FIRST: Crea SOLUCIONES PRÁCTICAS, no contenido teórico.
                2. 6 PILARES: Cubre Dificultad, Velocidad, Acompañamiento, Problemas Futuros, Puntos Ciegos, Medición.
                3. FORMATOS PRÁCTICOS: Usa Checklists, Trackers (tablas), Worksheets (espacios para escribir).
                4. SALIDA DUAL: 
                   - PARTE A: Código HTML estricto para PDF (usa <table>, <input type="checkbox"> o &#9744;, mucho espacio).
                   - PARTE B: Instrucciones exactas para maquetar esto en Gamma/Canva/Notion.
                5. SEPARADOR: Usa EXACTAMENTE `=== FIN_DEL_PDF ===` para separar la Parte A de la Parte B."""
                
                prompt_usuario = f"""
                REFERENCIA: {referencia_url if referencia_url else "Archivo adjunto"}
                TIPO DE PRODUCTO: {tipo_producto}
                AVATAR: {avatar}
                TRANSFORMACIÓN: {transformacion}
                
                INSTRUCCIÓN: Analiza la referencia, detecta sus gaps y diseña un NUEVO PRODUCTO SUPERIOR.
                Genera la PARTE A (HTML del Workbook) y la PARTE B (Instrucciones para Gamma/Canva).
                """
                
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(
                        model=MODEL_ID, max_tokens=6000,
                        system=prompt_sistema, messages=[{"role": "user", "content": prompt_usuario}]
                    )
                    full_output = response.content[0].text
                    
                    if "=== FIN_DEL_PDF ===" in full_output:
                        html_content, instructions = full_output.split("=== FIN_DEL_PDF ===", 1)
                    else:
                        html_content = full_output
                        instructions = "No se generaron instrucciones separadas."
                    
                    st.session_state['producto_html'] = html_content
                    st.session_state['instrucciones_ia'] = instructions
                    st.session_state['producto_modelado'] = True
                    st.success("✅ ¡Producto de Alto Valor diseñado!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Mostrar resultados de la Fase 1
    if 'producto_html' in st.session_state:
        st.markdown("### 📄 Vista Previa del Producto Modelado:")
        st.markdown(st.session_state['producto_html'], unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            if st.button("📥 Descargar PDF", use_container_width=True):
                css = """
                <style>
                body { font-family: Helvetica, Arial, sans-serif; color: #222; padding: 40px; line-height: 1.5; }
                h1 { color: #004466; border-bottom: 3px solid #004466; padding-bottom: 10px; font-size: 24px; }
                h2 { color: #006699; margin-top: 30px; font-size: 18px; border-left: 5px solid #006699; padding-left: 10px; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
                th { background-color: #f0f4f8; font-weight: bold; }
                </style>
                """
                full_html = f"<html><head>{css}</head><body>{st.session_state['producto_html']}</body></html>"
                buffer = io.BytesIO()
                pisa.CreatePDF(io.StringIO(full_html), dest=buffer)
                buffer.seek(0)
                st.download_button("⬇️ Guardar PDF Ahora", data=buffer, file_name="producto_alto_valor.pdf", mime="application/pdf")
        
        with col4:
            st.markdown("### 🎨 Instrucciones para Gamma/Canva")
            st.markdown(st.session_state['instrucciones_ia'])
        
        # Puerta de decisión para continuar con Landing
        if st.session_state['modo_seleccionado'] == 'completo':
            st.markdown("---")
            st.subheader("¿Continuar con la Landing Page?")
            st.markdown("Si el producto modelado te convence, podemos crear la página de ventas.")
            
            col5, col6 = st.columns(2)
            with col5:
                if st.button("✅ Sí, crear Landing", use_container_width=True):
                    st.session_state['continuar_landing'] = True
                    st.rerun()
            with col6:
                if st.button("❌ No, estoy satisfecho", use_container_width=True):
                    st.session_state['modo_seleccionado'] = None
                    st.session_state['producto_modelado'] = False
                    st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# FASE 2: MODELAR LANDING (SPCE)
# ═══════════════════════════════════════════════════════════════
elif st.session_state['modo_seleccionado'] == 'landing' or (st.session_state['modo_seleccionado'] == 'completo' and st.session_state.get('continuar_landing')):
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("🚀 FASE 2: Modelar Landing Page (Lovable)")
    
    if st.button("⬅️ Volver al menú", key="volver_landing"):
        st.session_state['modo_seleccionado'] = None
        st.session_state['continuar_landing'] = False
        st.rerun()
    
    # Si venimos del flujo completo, usamos el producto modelado
    if st.session_state.get('continuar_landing') and 'producto_html' in st.session_state:
        st.info("✅ Usando el producto modelado en la Fase 1 como base")
        producto_contexto = st.session_state['producto_html'][:1500]
    else:
        producto_contexto = st.text_area("Describe tu producto (o pega el contenido aquí)", height=150)
    
    col1, col2 = st.columns(2)
    with col1:
        precio = st.text_input("Precio", placeholder="Ej: $27 USD")
        garantia = st.text_input("Garantía", placeholder="Ej: 7 días sin preguntas")
    with col2:
        gancho = st.text_input("Gancho del Anuncio", placeholder="Ej: Deja de adivinar a dónde se va tu sueldo")
    
    if st.button("🚀 Generar Brief de Landing", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Introduce tu API Key")
        else:
            with st.spinner("🔍 Aplicando SPCE: Arquitectura psicológica, copy y brief para Lovable..."):
                prompt_sistema = """Eres el SALES PAGE CONVERSION ENGINE (SPCE).
                REGLAS: Mobile-First, Anti-Invención, Message Match.
                Tu objetivo es vender el producto descrito. Destaca su valor práctico."""
                
                prompt_usuario = f"""
                PRODUCTO A VENDER: {producto_contexto}
                PRECIO: {precio} | GARANTÍA: {garantia} | GANCHO: {gancho}
                
                INSTRUCCIÓN: Genera el Brief de Construcción para Lovable.
                Estructura: Hero, Problema, Solución, Oferta + Precio, FAQ.
                Entrégame el copy exacto y las instrucciones técnicas."""
                
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    response = client.messages.create(
                        model=MODEL_ID, max_tokens=4000,
                        system=prompt_sistema, messages=[{"role": "user", "content": prompt_usuario}]
                    )
                    st.success("✅ ¡Brief de Landing generado!")
                    st.markdown(response.content[0].text)
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
