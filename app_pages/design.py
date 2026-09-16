"""Design Pack — prompts listos para Canva, Gamma y Bing.

Script directo. Reutiliza el workbook de la Fase 1 y el DESIGN_FEED del ICAI.
"""

import urllib.parse

import streamlit as st

import observability as obs
from archivos import procesar_archivos
from parsing import extraer_seccion
from prompts import DESIGN_SECCIONES, DESIGN_SYSTEM, PLATFORMS
from workbook import texto_plano

api_key = st.session_state.get("api_key", "")
model_id = st.session_state.get("model_id", "")

st.markdown("Sube **referencias de estilo** (capturas, imágenes, PDFs) para que el "
            "nuevo producto emule ese estilo visual.")

style_files = st.file_uploader("Referencias de estilo (PNG/JPG/PDF)",
                               type=["png", "jpg", "jpeg", "pdf"],
                               accept_multiple_files=True, key="style_files")
formato = st.selectbox("Formato del entregable a diseñar",
    ["Workbook PDF (A4)", "Presentación / Deck", "Checklist imprimible",
     "Tracker / Hoja de seguimiento", "Guía visual"], key="formato")

producto_html = st.session_state.get("producto_html")
if producto_html:
    st.info("Usando el producto modelado en la Fase 1 como base.",
            icon=":material/check_circle:")
    base = texto_plano(producto_html)
else:
    base = st.text_area("Describe el producto a diseñar (o genera antes la Fase 1)",
                        height=120, key="base_design")

feed3 = st.session_state.get("icai_design_feed", "")
if feed3:
    st.info("Inteligencia ICAI conectada: el Design Pack usará el DESIGN_FEED "
            "(tono, estilo, emoción por segmento).", icon=":material/psychology:")

if st.button("Generar Design Pack", type="primary", width="stretch",
             icon=":material/palette:"):
    if not api_key:
        st.error("Falta la API Key en la barra lateral", icon=":material/key_off:")
    else:
        with st.spinner("Analizando el estilo de las referencias y generando los prompts…"):
            texto_estilo, bloques_estilo = procesar_archivos(style_files, "REFERENCIA DE ESTILO")

            contenido = []
            if texto_estilo:
                contenido.append({"type": "text", "text":
                    f"TEXTO DE LAS REFERENCIAS DE ESTILO:\n{texto_estilo}"})
            contenido.extend(bloques_estilo)
            contenido.append({"type": "text", "text": f"""PRODUCTO A DISEÑAR:
{base}

FORMATO OBJETIVO: {formato}

Genera los 4 bloques con sus separadores exactos."""})
            if feed3:
                contenido.append({"type": "text", "text":
                    f"=== INTELIGENCIA ICAI (DESIGN_FEED) ===\n{feed3}"})

            try:
                client = obs.cliente_observado(api_key, model_id)
                resp = client.messages.create(
                    model=model_id, max_tokens=4000,
                    system=DESIGN_SYSTEM,
                    messages=[{"role": "user", "content": contenido}],
                )
                partes = [b.text for b in resp.content
                          if getattr(b, "type", "") == "text"]
                salida = "\n\n".join(partes).strip()

                if not salida:
                    st.error("La respuesta no contenía texto que mostrar.",
                             icon=":material/error:")
                else:
                    st.session_state["design_pack"] = salida
                    st.success("Design Pack generado.", icon=":material/check_circle:")
                    st.caption(obs.last_line())
            except Exception as e:
                st.error(f"Error: {e}", icon=":material/error:")

# ── Resultados guardados en la sesión ────────────────────────────────────
if st.session_state.get("design_pack"):
    out = st.session_state["design_pack"]
    style, canva, gamma, bing = (extraer_seccion(out, m, DESIGN_SECCIONES)
                                 for m in DESIGN_SECCIONES)

    st.subheader("Guía de estilo detectada", icon=":material/palette:")
    st.markdown(style or "(sin guía de estilo)")

    # Se usan elementos nativos: st.code ya trae su propio botón de copiar y
    # st.link_button abre la plataforma. Antes esto era un <button> con
    # JavaScript inyectado vía st.components.v1.html (obsoleto), donde TODOS
    # los botones compartían id="ocbtn": al pasar a HTML inline en lugar de
    # iframes separados, todos habrían copiado el prompt de Canva.
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
        [p for p in PLATFORMS
         if p not in ("Canva (Magic Design)", "Gamma (Docs y Presentaciones)")],
        key="otras_plataformas",
    )
    for p in otras:
        st.markdown(f"**{p}**")
        st.code(canva, language=None)
        st.link_button(f"Abrir {p}", PLATFORMS[p],
                       width="stretch", icon=":material/open_in_new:")
