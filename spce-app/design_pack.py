import streamlit as st
import streamlit.components.v1 as components
import anthropic
import base64
import io
import re
import urllib.parse
from pypdf import PdfReader

PLATFORMS = {
    "Canva (Magic Design)": "https://www.canva.com/",
    "Gamma (Docs y Presentaciones)": "https://gamma.app/",
    "Adobe Express": "https://new.express.adobe.com/",
    "Microsoft Designer": "https://designer.microsoft.com/",
    "Piktochart": "https://piktochart.com/",
    "Visme": "https://www.visme.co/",
    "Kittl": "https://www.kittl.com/",
    "Recraft": "https://www.recraft.ai/",
}

DESIGN_SYSTEM = """Eres un DESIGN BRIEF GENERATOR para herramientas de diseño con IA.
REGLAS:
- Si hay referencias de estilo (imágenes), analízalas y extrae: paleta HEX, tipografías, tono, layout y elementos gráficos. Si no las hay, propón un estilo coherente con el avatar y márcalo [PROPUESTA].
- No inventes marcas, testimonios ni datos comerciales.
- No incluyas meta-instrucciones dentro de los prompts ("pega esto...", "usa este prompt...").
SALIDA EXACTA con estos separadores:
=== STYLE ===
(guía de estilo: paleta con HEX, tipografías, tono, layout, elementos)
=== CANVA ===
(prompt en español, máx 150 palabras, para Canva Magic Design: tipo de documento y formato, paleta hex, tipografías, estructura de secciones con títulos reales, estilo gráfico e iconos)
=== GAMMA ===
(prompt en español para Gamma.app: tipo de doc/deck, estructura narrativa por tarjetas, tono, paleta, estilo de visuales)
=== BING ===
(prompt en inglés, máx 60 palabras, para generar portada/mockup: estilo, colores dominantes, composición, iluminación; indica 'no text' salvo el título del producto)"""

def _one_click_button(label, prompt_text, url):
    seguro = prompt_text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    html = f"""
<button id="ocbtn" style="width:100%;padding:12px;border:none;border-radius:8px;
background:linear-gradient(90deg,#00d4ff,#0099cc);color:#fff;font-weight:600;cursor:pointer;font-size:14px;">
{label}</button>
<script>
document.getElementById('ocbtn').onclick = async function() {{
  var texto = `{seguro}`;
  try {{ await navigator.clipboard.writeText(texto); }}
  catch(e) {{
    var ta = document.createElement('textarea');
    ta.value = texto; document.body.appendChild(ta);
    ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
  }}
  window.open('{url}', '_blank');
  this.innerText = '✅ Prompt copiado — pégalo en la plataforma con Ctrl+V';
}};
</script>"""
    components.html(html, height=52)

def render(api_key, model_id, producto_html=None):
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("🎨 Design Pack — Prompts listos para Canva, Gamma y más")

    if st.button("⬅️ Volver al menú", key="v3"):
        st.session_state['modo_seleccionado'] = None
        st.rerun()

    st.markdown("Sube **referencias de estilo** (capturas, imágenes, PDFs) para que el nuevo producto emule ese estilo visual.")
    style_files = st.file_uploader("Referencias de estilo (PNG/JPG/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
    formato = st.selectbox("Formato del entregable a diseñar",
        ["Workbook PDF (A4)", "Presentación / Deck", "Checklist imprimible", "Tracker / Hoja de seguimiento", "Guía visual"])

    if producto_html:
        st.info("✅ Usando el producto modelado en Fase 1 como base.")
        base = producto_html
    else:
        base = st.text_area("Describe el producto a diseñar (o genera antes la Fase 1)", height=120)

    if st.button("🎨 Generar Design Pack", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Falta la API Key en la barra lateral")
        else:
            with st.spinner("🎨 Analizando estilo de referencias y generando prompts por plataforma..."):
                contenido = []
                for f in (style_files or []):
                    if f.type in ["image/png", "image/jpeg"]:
                        contenido.append({"type": "image", "source": {"type": "base64",
                            "media_type": f.type, "data": base64.b64encode(f.read()).decode()}})
                    elif f.type == "application/pdf":
                        try:
                            txt = "\n".join([p.extract_text() or "" for p in PdfReader(io.BytesIO(f.read())).pages])
                            contenido.append({"type": "text", "text": f"TEXTO DEL PDF DE ESTILO ({f.name}):\n{txt[:6000]}"})
                        except Exception:
                            st.warning(f"⚠️ PDF no legible: {f.name}")
                base_limpia = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', base or ""))[:6000]
                contenido.append({"type": "text", "text": f"""PRODUCTO A DISEÑAR:
{base_limpia}

FORMATO OBJETIVO: {formato}

Genera los 4 bloques con sus separadores exactos."""})
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    resp = client.messages.create(model=model_id, max_tokens=4000,
                        system=DESIGN_SYSTEM, messages=[{"role": "user", "content": contenido}])
                    st.session_state['design_pack'] = resp.content[0].text
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    if st.session_state.get('design_pack'):
        out = st.session_state['design_pack']
        def bloque(marker):
            if marker not in out: return ""
            tail = out.split(marker, 1)[1]
            for m in ["=== STYLE ===", "=== CANVA ===", "=== GAMMA ===", "=== BING ==="]:
                tail = tail.split(m)[0]
            return tail.strip()

        style, canva, gamma, bing = (bloque(m) for m in
            ["=== STYLE ===", "=== CANVA ===", "=== GAMMA ===", "=== BING ==="])

        st.markdown("### 🧬 Guía de estilo detectada")
        st.markdown(style or "(sin guía de estilo)")

        st.markdown("### 🖌️ CANVA — Magic Design")
        st.code(canva, language=None)
        _one_click_button("📋 Copiar prompt y abrir Canva (1 clic)", canva, PLATFORMS["Canva (Magic Design)"])
        st.caption("Dentro de Canva: nuevo diseño → Magic Design → pega con Ctrl+V.")

        st.markdown("### 📊 GAMMA — Docs / Presentaciones")
        st.code(gamma, language=None)
        _one_click_button("📋 Copiar prompt y abrir Gamma (1 clic)", gamma, PLATFORMS["Gamma (Docs y Presentaciones)"])

        st.markdown("### 🖼️ BING IMAGE CREATOR — Portada / Mockup")
        st.caption("Único enlace que lleva el prompt YA escrito dentro:")
        st.link_button("🔗 Abrir Bing con el prompt cargado",
            "https://www.bing.com/images/create?q=" + urllib.parse.quote(bing), use_container_width=True)
        st.code(bing, language=None)

        st.markdown("### 🧰 Otras plataformas")
        otras = st.multiselect("Elige plataformas extra",
            [p for p in PLATFORMS if p not in ("Canva (Magic Design)", "Gamma (Docs y Presentaciones)")])
        for p in otras:
            st.markdown(f"**{p}**")
            _one_click_button(f"📋 Copiar brief y abrir {p}", canva, PLATFORMS[p])

    st.markdown('</div>', unsafe_allow_html=True)