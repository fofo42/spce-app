"""Paso 0 · ICAI — inteligencia de cliente.

Script directo (sin función contenedora): Streamlit ejecuta el archivo entero
en cada interacción. El título de la página lo pone el punto de entrada desde
la definición de `st.Page`, así que aquí no se usa `st.title`.
"""

import streamlit as st

import observability as obs
from archivos import procesar_archivos
from parsing import extraer_json, extraer_seccion
from prompts import ICAI_CLAVES, ICAI_SECCIONES, ICAI_SECCIONES_UI, ICAI_SYSTEM

api_key = st.session_state.get("api_key", "")
model_id = st.session_state.get("model_id", "")

st.markdown("Modela al cliente y su decisión: descubrimiento, evaluación, elección, "
            "mensaje, funnel y lifecycle.")

niche = st.text_input("NICHE (obligatorio)",
                      placeholder="Ej: cocina económica para personas sin tiempo")
prod_files = st.file_uploader("PRODUCTO (PDF/PNG/JPG)", type=["pdf", "png", "jpg", "jpeg"],
                              accept_multiple_files=True, key="icai_prod")
prod_desc = st.text_area("O describe el producto", height=90)
ev_files = st.file_uploader("EVIDENCIA DE CLIENTE opcional (reviews, comentarios, encuestas...)",
                            type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True,
                            key="icai_ev")
ev_text = st.text_area("O pega aquí evidencia textual", height=100)

if st.button("Ejecutar ICAI DEEP (dossier + 6 capas + puentes)", type="primary",
             width="stretch", icon=":material/explore:"):
    if not api_key:
        st.error("Introduce tu API Key en la barra lateral", icon=":material/key_off:")
    elif not niche.strip():
        st.error("El NICHE es obligatorio.", icon=":material/warning:")
    elif not prod_files and not prod_desc.strip():
        st.error("Falta el PRODUCTO: sube archivos o descríbelo.",
                 icon=":material/warning:")
    else:
        with st.spinner("Modelando el cliente: estado → decisión → descubrimiento → "
                        "conversión → lifecycle…"):
            contenido = []
            pt, pb = procesar_archivos(prod_files, "PRODUCTO")
            et, eb = procesar_archivos(ev_files, "EVIDENCIA DE CLIENTE")
            contenido.append({"type": "text", "text":
                f"NICHE: {niche}\n\nPRODUCTO (contenido documental):\n{pt}\n"
                f"Descripción del producto: {prod_desc or '-'}"})
            contenido.extend(pb)
            contenido.append({"type": "text", "text":
                f"EVIDENCIA DE CLIENTE:\n{et}\n{ev_text or '-'}"})
            contenido.extend(eb)
            contenido.append({"type": "text", "text":
                "Ejecuta el proceso completo y entrega todas las secciones "
                "con sus separadores exactos."})
            try:
                client = obs.cliente_observado(api_key, model_id)

                st.markdown("##### Generando en vivo (texto en bruto; el dossier "
                            "aparece abajo al terminar)")
                with client.messages.stream(
                    model=model_id, max_tokens=20000,
                    system=ICAI_SYSTEM,
                    messages=[
                        {"role": "user", "content": contenido},
                        {"role": "assistant", "content": "{"},
                    ],
                ) as stream:
                    def _generador_texto():
                        for chunk in stream.text_stream:
                            yield chunk

                    raw_text = st.write_stream(_generador_texto())
                    stream.get_final_message()

                # Empezamos el texto con "{" porque ese carácter no viene
                # incluido en la respuesta: se lo "regalamos" nosotros para
                # forzar que Claude continúe directamente en formato JSON.
                raw_output = "{" + raw_text

                datos = extraer_json(raw_output)
                if datos is None:
                    # Rescate de último recurso: el prompt exige JSON puro,
                    # pero si el modelo ignoró el contrato y respondió con los
                    # separadores de texto, aún se puede aprovechar.
                    st.warning("No se pudo interpretar la respuesta como JSON. "
                               "Se muestran los separadores de texto si existen.",
                               icon=":material/warning:")
                    with st.expander("Ver respuesta en bruto", icon=":material/build:"):
                        st.code(raw_output[:5000])
                    secciones = {m: extraer_seccion(raw_output, m, ICAI_SECCIONES)
                                 for m in ICAI_SECCIONES}
                    out = raw_output
                else:
                    secciones = {marcador: (datos.get(clave) or "").strip()
                                 for marcador, clave in ICAI_CLAVES.items()}
                    out = "\n\n".join(f"{m}\n{secciones[m]}"
                                      for m in ICAI_SECCIONES if secciones[m])

                st.session_state["icai_dossier"] = out
                st.session_state["icai_sections"] = secciones

                # Los tres puentes que consumen las fases siguientes.
                st.session_state["icai_offer_feed"] = secciones.get("=== OFFER_FEED ===", "")
                st.session_state["icai_spce_feed"] = secciones.get("=== SPCE_FEED ===", "")
                st.session_state["icai_design_feed"] = secciones.get("=== DESIGN_FEED ===", "")

                if not secciones.get("=== OFFER_FEED ==="):
                    st.warning("No se pudo extraer el OFFER_FEED de la respuesta. "
                               "Revisa el resultado en bruto antes de pasar a la Fase 1.",
                               icon=":material/warning:")
                    with st.expander("Ver respuesta en bruto", icon=":material/build:"):
                        st.code(raw_output[:5000])
                else:
                    st.success("ICAI DEEP completado: dossier + 6 capas + puentes conectados.",
                               icon=":material/check_circle:")
                st.caption(obs.last_line())
            except Exception as e:
                st.error(f"Error: {e}", icon=":material/error:")

# ── Resultados guardados en la sesión ────────────────────────────────────
if st.session_state.get("icai_sections"):
    secs = st.session_state["icai_sections"]

    for marcador in ICAI_SECCIONES:
        if secs.get(marcador):
            titulo, icono = ICAI_SECCIONES_UI[marcador]
            with st.expander(titulo, icon=icono,
                             expanded=(marcador in ("=== OFFER_FEED ===", "=== SPCE_FEED ==="))):
                st.markdown(secs[marcador])

    st.download_button("Descargar dossier DEEP completo",
                       data=st.session_state["icai_dossier"],
                       file_name="icai_dossier_deep.md", mime="text/markdown",
                       width="stretch", icon=":material/download:")

    offer_len = len(st.session_state.get("icai_offer_feed", ""))
    st.caption(f"OFFER_FEED listo: {offer_len} caracteres | "
               f"SPCE_FEED: {len(st.session_state.get('icai_spce_feed', ''))} | "
               f"DESIGN_FEED: {len(st.session_state.get('icai_design_feed', ''))}")

    st.info("Puentes conectados: las fases de producto, landing y diseño usarán "
            "esta inteligencia automáticamente.", icon=":material/check_circle:")

    st.divider()
    st.subheader("¿Qué quieres hacer ahora?", icon=":material/rocket_launch:")
    tc1, tc2 = st.columns(2)
    with tc1:
        if st.button("Modelar el producto (fase 1)", width="stretch", type="primary",
                     icon=":material/inventory_2:"):
            st.switch_page("app_pages/producto.py")
    with tc2:
        if st.button("Design Pack", width="stretch", icon=":material/palette:"):
            st.switch_page("app_pages/design.py")
