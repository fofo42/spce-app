import observability as obs
import streamlit as st
import base64
import io
import re
import urllib.parse
from pypdf import PdfReader

from parsing import extraer_seccion

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


def render(api_key, model_id, producto_html=None):
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("Design Pack — prompts para Canva, Gamma y más",
                 icon=":material/palette:")

    if st.button("Volver al menú", key="v3", icon=":material/arrow_back:"):
        st.session_state['modo_seleccionado'] = None
        st.rerun()

    st.markdown("Sube **referencias de estilo** (capturas, imágenes, PDFs) para que el nuevo producto emule ese estilo visual.")
    style_files = st.file_uploader(
        "Referencias de estilo (PNG/JPG/PDF)",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        accept_multiple_files=True
    )
    formato = st.selectbox(
        "Formato del entregable a diseñar",
        ["Workbook PDF (A4)", "Presentación / Deck", "Checklist imprimible",
         "Tracker / Hoja de seguimiento", "Guía visual"]
    )

    if producto_html:
        st.info("Usando el producto modelado en Fase 1 como base.",
                icon=":material/check_circle:")
        base = producto_html
    else:
        base = st.text_area(
            "Describe el producto a diseñar (o genera antes la Fase 1)",
            height=120
        )

    # Inyectar DESIGN_FEED del ICAI si existe
    feed3 = st.session_state.get('icai_design_feed', '')
    if feed3:
        st.info("Inteligencia ICAI conectada: el Design Pack usará el DESIGN_FEED "
                "(tono, estilo, emoción por segmento).", icon=":material/psychology:")

    if st.button("Generar Design Pack", type="primary", width="stretch",
                 icon=":material/palette:"):
        if not api_key:
            st.error("Falta la API Key en la barra lateral", icon=":material/key_off:")
        else:
            with st.spinner("Analizando el estilo de las referencias y generando los prompts…"):
                contenido = []
                # Procesar archivos de estilo
                for f in (style_files or []):
                    if f.type in ["image/png", "image/jpeg"]:
                        contenido.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f.type,
                                "data": base64.b64encode(f.read()).decode()
                            }
                        })
                    elif f.type == "application/pdf":
                        try:
                            txt = "\n".join([p.extract_text() or "" for p in PdfReader(io.BytesIO(f.read())).pages])
                            contenido.append({
                                "type": "text",
                                "text": f"TEXTO DEL PDF DE ESTILO ({f.name}):\n{txt[:6000]}"
                            })
                        except Exception:
                            st.warning(f"PDF no legible: {f.name}",
                                       icon=":material/warning:")
                # Contenido base del producto
                base_limpia = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', base or ""))[:6000]
                contenido.append({
                    "type": "text",
                    "text": f"""PRODUCTO A DISEÑAR:
{base_limpia}

FORMATO OBJETIVO: {formato}

Genera los 4 bloques con sus separadores exactos."""
                })
                # Inyectar DESIGN_FEED si existe
                if feed3:
                    contenido.append({
                        "type": "text",
                        "text": f"=== INTELIGENCIA ICAI (DESIGN_FEED) ===\n{feed3}"
                    })
                try:
                    client = obs.cliente_observado(api_key, model_id)
                    resp = client.messages.create(
                        model=model_id,
                        max_tokens=4000,
                        system=DESIGN_SYSTEM,
                        messages=[{"role": "user", "content": contenido}]
                    )
                    st.session_state['design_pack'] = resp.content[0].text
                    st.success("Design Pack generado.", icon=":material/check_circle:")
                    st.caption(obs.last_line())
                except Exception as e:
                    st.error(f"Error: {e}", icon=":material/error:")

    # Mostrar resultados
    if st.session_state.get('design_pack'):
        out = st.session_state['design_pack']
        marcadores = ["=== STYLE ===", "=== CANVA ===", "=== GAMMA ===", "=== BING ==="]
        style, canva, gamma, bing = (extraer_seccion(out, m, marcadores) for m in marcadores)

        st.subheader("Guía de estilo detectada", icon=":material/palette:")
        st.markdown(style or "(sin guía de estilo)")

        # Se usan elementos nativos: st.code ya trae su propio botón de copiar
        # y st.link_button abre la plataforma. Antes esto era un <button> con
        # JavaScript inyectado vía st.components.v1.html (obsoleto), donde
        # TODOS los botones compartían id="ocbtn": al pasar a HTML inline en
        # lugar de iframes separados, todos habrían copiado el prompt de Canva.
        st.subheader("Canva — Magic Design", icon=":material/brush:")
        st.code(canva, language=None)
        st.link_button("Abrir Canva", PLATFORMS["Canva (Magic Design)"],
                       width="stretch", icon=":material/open_in_new:")
        st.caption("Dentro de Canva: nuevo diseño → Magic Design → pega con Ctrl+V.")

        st.subheader("Gamma — Docs / presentaciones", icon=":material/slideshow:")
        st.code(gamma, language=None)
        st.link_button("Abrir Gamma", PLATFORMS["Gamma (Docs y Presentaciones)"],
                       width="stretch", icon=":material/open_in_new:")

        st.subheader("Bing Image Creator — Portada / mockup", icon=":material/image:")
        st.caption("Este enlace es el único que lleva el prompt ya escrito dentro.")
        st.link_button("Abrir Bing con el prompt cargado",
                       "https://www.bing.com/images/create?q=" + urllib.parse.quote(bing),
                       width="stretch", icon=":material/open_in_new:")
        st.code(bing, language=None)

        st.subheader("Otras plataformas", icon=":material/extension:")
        otras = st.multiselect(
            "Elige plataformas extra",
            [p for p in PLATFORMS if p not in ("Canva (Magic Design)", "Gamma (Docs y Presentaciones)")]
        )
        for p in otras:
            st.markdown(f"**{p}**")
            st.code(canva, language=None)
            st.link_button(f"Abrir {p}", PLATFORMS[p],
                           width="stretch", icon=":material/open_in_new:")

    st.markdown('</div>', unsafe_allow_html=True)