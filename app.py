import streamlit as st
import anthropic
import base64

# Configuración de la página
st.set_page_config(page_title="SPCE Modelador Pro", page_icon="🔄", layout="wide")
st.title("🔄 SPCE Modelador Pro — Reconstrucción Ética con Visión IA")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("API Key de Anthropic", type="password")
    st.info("💡 Obtén tu key en: console.anthropic.com")
    st.markdown("---")
    st.markdown("### 📁 Formatos soportados:")
    st.markdown("- **Imágenes**: PNG, JPG, JPEG (La IA las analizará visualmente)")
    st.markdown("- **Textos**: TXT, MD")
    st.markdown("- **PDF**: (Requiere `pip install pypdf`)")

# ═══════════════════════════════════════════════════════════════
# SECCIÓN 1: LA REFERENCIA
# ═══════════════════════════════════════════════════════════════
st.subheader("1️⃣ Página de Referencia")
col1, col2 = st.columns([2, 1])

with col1:
    referencia_url = st.text_input("URL de la landing page (opcional)", placeholder="https://ejemplo.com/landing")

with col2:
    uploaded_file = st.file_uploader("O sube una captura (PNG/JPG)", type=['png', 'jpg', 'jpeg'])

descripcion_ref = st.text_area(
    "Breve descripción (opcional)",
    placeholder="Ej: Vende un curso de marketing. Tiene un hero con testimonio, 3 pasos, y FAQ al final.",
    height=80
)

# ═══════════════════════════════════════════════════════════════
# SECCIÓN 2: TU PRODUCTO
# ═══════════════════════════════════════════════════════════════
st.subheader("2️⃣ Tu Producto")

col3, col4 = st.columns(2)

with col3:
    tu_producto = st.text_input("Nombre de TU producto", placeholder="Ej: FlowFinance")
    tipo_producto = st.selectbox("Tipo de producto", 
        ["Plantilla de Notion", "Ebook/Guía", "Curso Online", "Software/SaaS", "Servicio", "Otro"])
    precio = st.text_input("Precio", placeholder="Ej: $27 USD")
    
with col4:
    garantia = st.text_input("Garantía", placeholder="Ej: 7 días sin preguntas")
    gancho = st.text_input("Gancho principal", placeholder="Ej: Deja de adivinar a dónde se va tu sueldo")
    avatar = st.text_input("Avatar/Público", placeholder="Ej: Freelancers con ingresos variables")

features = st.text_area(
    "Features reales de tu producto (3-5)",
    placeholder="1. Dashboard automático\n2. Tracker de gastos\n3. Sistema de sobres",
    height=100
)

# ═══════════════════════════════════════════════════════════════
# SECCIÓN 3: ARCHIVOS DEL PRODUCTO
# ═══════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("3️⃣ Archivos de Información del Producto (Opcional)")
st.markdown("Sube PDFs, TXT o documentos con la descripción, manual o especificaciones de tu producto.")

archivos_producto = st.file_uploader(
    "Sube archivos del producto (PDF, TXT, MD)",
    type=['pdf', 'txt', 'md'],
    accept_multiple_files=True
)

contenido_archivos = ""
if archivos_producto:
    st.info(f"📄 {len(archivos_producto)} archivo(s) subido(s)")
    for archivo in archivos_producto:
        try:
            if archivo.type == "text/plain" or archivo.name.endswith('.md'):
                texto = archivo.read().decode('utf-8')
                contenido_archivos += f"\n\n--- ARCHIVO: {archivo.name} ---\n{texto}"
            elif archivo.type == "application/pdf":
                try:
                    from pypdf import PdfReader
                    import io
                    pdf_reader = PdfReader(io.BytesIO(archivo.read()))
                    texto_pdf = "".join([pagina.extract_text() for pagina in pdf_reader.pages])
                    contenido_archivos += f"\n\n--- ARCHIVO PDF: {archivo.name} ---\n{texto_pdf}"
                except ImportError:
                    st.warning(f"️ Para leer PDFs, instala pypdf: `pip install pypdf`.")
        except Exception as e:
            st.warning(f"⚠️ No se pudo procesar {archivo.name}: {str(e)}")

# ═══════════════════════════════════════════════════════════════
# BOTÓN DE ACCIÓN
# ═══════════════════════════════════════════════════════════════
if st.button(" Modelar Página Automáticamente", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Introduce tu API Key en la barra lateral")
    elif not referencia_url and not uploaded_file:
        st.error("⚠️ Proporciona al menos una URL O una captura de la referencia")
    elif not tu_producto or not precio:
        st.error("⚠️ Nombre y precio de tu producto son obligatorios")
    else:
        with st.spinner("️ Analizando visualmente la referencia → Extrayendo patrones → Reconstruyendo..."):
            
            # Preparar contexto de la referencia
            contexto_ref = ""
            if uploaded_file:
                contexto_ref += f"Captura subida: {uploaded_file.name}\n"
            if referencia_url:
                contexto_ref += f"URL: {referencia_url}\n"
            if descripcion_ref:
                contexto_ref += f"Descripción: {descripcion_ref}"
            
            contexto_archivos = f"\n\nINFORMACIÓN EXTRAÍDA DE ARCHIVOS ADJUNTOS:\n{contenido_archivos}" if contenido_archivos else ""
            
            # Prompt del sistema
            prompt_sistema = """Eres un experto en reconstrucción ética de landing pages con capacidad de visión artificial.

REGLAS ABSOLUTAS:
1. NUNCA copies texto literal, claims, testimonios o diseño exacto.
2. SIEMPRE extrae solo PATRONES (estructura, flujo, técnicas, jerarquía visual).
3. SIEMPRE crea contenido 100% original para el nuevo producto.
4. SIEMPRE mejora las debilidades detectadas.
5. Aplica Mobile-First, Anti-Invención y Message Match.

Si te proporcionan una imagen, analízala visualmente para detectar: orden de bloques, jerarquía visual, uso de colores, ubicación de CTAs y elementos de confianza."""
            
            # Preparar el contenido del mensaje (Texto + Imagen si existe)
            contenido_mensaje = []
            
            # Si hay imagen, añadirla al mensaje en formato base64
            if uploaded_file and uploaded_file.type in ['image/png', 'image/jpeg', 'image/jpg']:
                image_bytes = uploaded_file.read()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                contenido_mensaje.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": uploaded_file.type,
                        "data": image_base64
                    }
                })
            
            # Añadir el texto del prompt
            prompt_usuario_texto = f"""
REFERENCIA ANALIZADA:
{contexto_ref}

MI PRODUCTO REAL:
- Nombre: {tu_producto}
- Tipo: {tipo_producto}
- Precio: {precio}
- Garantía: {garantia}
- Gancho: {gancho}
- Avatar: {avatar}
- Features: {features}
{contexto_archivos}

INSTRUCCIÓN:
Ejecuta el ciclo completo de reconstrucción ética:

FASE 1 — ANÁLISIS VISUAL/ESTRUCTURAL:
- Identifica la estructura psicológica (orden de bloques).
- Detecta patrones de conversión usados (hook, mecanismo, prueba).
- Identifica 2-3 fortalezas y 2-3 debilidades claras (ej. texto largo, stock genérico).

FASE 2 — RECONSTRUCCIÓN (completa):
Genera una landing page COMPLETAMENTE NUEVA para mi producto que:
1. Use los patrones exitosos detectados (adaptados, no copiados).
2. Corrija las debilidades de la referencia.
3. Tenga copy original basado en mi gancho y features REALES.
4. Siga la arquitectura: Hero → Problema → Solución → Demo → Oferta → Garantía → FAQ → CTA.
5. Sea Mobile-First.

ENTREGABLE:
- Arquitectura de bloques con copy exacto.
- Brief de construcción para Lovable.
- Validación de originalidad (confirmar que no hay copia).
"""
            contenido_mensaje.append({"type": "text", "text": prompt_usuario_texto})
            
            try:
                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022", # Modelo con capacidad de visión
                    max_tokens=4000,
                    system=prompt_sistema,
                    messages=[{"role": "user", "content": contenido_mensaje}]
                )
                
                st.success("✅ ¡Página modelada y reconstruida!")
                st.markdown(response.content[0].text)
                
                st.download_button(
                    label="📥 Descargar Brief",
                    data=response.content[0].text,
                    file_name=f"modelado_{tu_producto.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("*SPCE Modelador Pro v2.0 — Visión IA integrada. Reconstrucción ética. Cero copias.*")
