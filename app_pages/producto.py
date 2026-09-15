"""Fase 1 · Offer Engine V1.0.1 — modelar el producto.

Script directo. El título lo pone el punto de entrada desde `st.Page`.
"""

import streamlit as st

import observability as obs
from archivos import procesar_archivos
from parsing import extraer_json
from prompts import OFFER_SYSTEM
from workbook import construir_pdf, mostrar_workbook

api_key = st.session_state.get("api_key", "")
model_id = st.session_state.get("model_id", "")

MODO_CERO = "Crear desde cero (con la inteligencia ICAI)"
MODO_REMODELAR = "Remodelar un producto existente"

# ── ¿Hay inteligencia de cliente del Paso 0? ─────────────────────────────
feed0 = st.session_state.get("icai_offer_feed", "")
tiene_icai = bool(feed0)

if tiene_icai:
    st.success("Inteligencia ICAI detectada y disponible.", icon=":material/psychology:")
    # `or MODO_CERO` protege el caso en que el usuario deselecciona la opción
    # activa: segmented_control devuelve None al hacer clic sobre lo ya elegido.
    modo_modelado = st.segmented_control(
        "¿Cómo quieres modelar el producto?",
        [MODO_CERO, MODO_REMODELAR],
        default=MODO_CERO,
        key="modo_modelado",
    ) or MODO_CERO
else:
    st.warning("No hay análisis ICAI disponible: se remodelará un producto que subas.",
               icon=":material/warning:")
    modo_modelado = MODO_REMODELAR

diseno_desde_cero = tiene_icai and modo_modelado == MODO_CERO

# ── Bloque A: referencia de estilo ───────────────────────────────────────
st.markdown("#### A) Referencia de estilo y modelado *(cómo debe quedar)*")
c1, c2 = st.columns(2)
with c1:
    referencia_url = st.text_input("URL de referencia (opcional)", key="referencia_url")
    uploaded_ref = st.file_uploader("Archivos de referencia (PDF/PNG/JPG)",
                                    type=["pdf", "png", "jpg", "jpeg"],
                                    accept_multiple_files=True, key="ref_files")
with c2:
    descripcion_ref = st.text_area("Descripción de la referencia (opcional)",
                                   height=90, key="descripcion_ref")
    tipo_producto = st.selectbox("Tipo de producto",
        ["Ebook/Guía", "Plantilla de Notion", "Curso Online", "Libro de Recetas",
         "Software/SaaS", "Servicio", "Otro"], key="tipo_producto")

# ── Bloque B: producto base ──────────────────────────────────────────────
st.markdown("#### B) Producto base")

if diseno_desde_cero:
    st.info("Modo: crear desde cero usando la inteligencia ICAI. "
            "No necesitas subir producto base.", icon=":material/lightbulb:")
    st.markdown("*El Offer Engine diseñará el producto a partir de la inteligencia de "
                "cliente del Paso 0 y de la referencia de estilo.*")
    uploaded_producto = None
    descripcion_producto = ""
else:
    uploaded_producto = st.file_uploader("Sube TU producto (PDF/PNG/JPG)",
                                         type=["pdf", "png", "jpg", "jpeg"],
                                         accept_multiple_files=True, key="prod_files")
    descripcion_producto = st.text_area("O describe tu producto si no tienes archivos",
                                        height=90, key="desc_prod")

c3, c4 = st.columns(2)
with c3:
    avatar = st.text_input("Avatar / público objetivo",
                           placeholder="Ej: mujeres sin tiempo para cocinar",
                           key="avatar")
with c4:
    transformacion = st.text_input("Transformación deseada",
                                   placeholder="Ej: cocinar 2 veces/semana y tener comida para 7 días",
                                   key="transformacion")

# ── Ejecución ────────────────────────────────────────────────────────────
producto_aportado = bool(uploaded_producto) or bool(descripcion_producto.strip())

if st.button("Ejecutar motor V1.0.1 (auditoría + workbook + roadmap)", type="primary",
             width="stretch", icon=":material/psychology:"):
    if not api_key:
        st.error("Introduce tu API Key en la barra lateral", icon=":material/key_off:")
    elif not diseno_desde_cero and not producto_aportado:
        st.error("Falta TU PRODUCTO: sube archivos en el Bloque B o descríbelo "
                 "(o ejecuta primero el Paso 0 ICAI).", icon=":material/warning:")
    else:
        modo_texto = "diseño desde cero con ICAI" if diseno_desde_cero else "remodelado de producto base"
        with st.spinner(f"Ejecutando la state machine ({modo_texto}): extracción → "
                        "pilares → gaps → DQS → arquitectura → validación…"):
            ref_texto, ref_bloques = procesar_archivos(uploaded_ref, "REFERENCIA DE ESTILO")
            prod_texto, prod_bloques = (
                procesar_archivos(uploaded_producto, "PRODUCTO A MODELAR")
                if uploaded_producto else ("", [])
            )

            contenido = []

            if feed0:
                contenido.append({"type": "text", "text":
                    f"=== INTELIGENCIA ICAI (OFFER_FEED) ===\n"
                    f"Contexto prioritario de cliente:\n{feed0}"})

            contenido.append({"type": "text", "text": f"""=== REFERENCIA DE ESTILO/MODELADO ===
(Úsala SOLO para estilo/patrones/técnicas. NO copies su contenido.)
URL: {referencia_url or '-'}
Descripción: {descripcion_ref or '-'}
{ref_texto}"""})
            contenido.extend(ref_bloques)

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

            # El prompt de sistema exige JSON con 3 claves exactas; la
            # instrucción tiene que pedir lo mismo.
            instruccion_final = (
                "Ejecuta tu proceso interno completo (9 pasos) y entrega el objeto JSON "
                "con las 3 claves exactas."
                if producto_aportado
                else "Ejecuta tu proceso interno completo (9 pasos). Como NO hay producto "
                     "base, debes DISEÑAR la arquitectura de entregables a partir de los "
                     "obstáculos del cliente (ICAI) y de los patrones de la referencia de "
                     "estilo. Entrega el objeto JSON con las 3 claves exactas."
            )
            contenido.append({"type": "text", "text": f"""DATOS DEL PROYECTO:
TIPO: {tipo_producto} | AVATAR: {avatar} | TRANSFORMACIÓN: {transformacion}
MODO: {'DISEÑO DESDE CERO (con ICAI)' if diseno_desde_cero else 'REMODELADO (con producto base)'}

INSTRUCCIÓN: {instruccion_final}"""})

            try:
                client = obs.cliente_observado(api_key, model_id)

                st.markdown("##### Generando en vivo (texto en bruto; el workbook "
                            "aparece abajo al terminar)")
                with client.messages.stream(
                    model=model_id, max_tokens=20000,
                    system=OFFER_SYSTEM,
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
                    st.session_state["producto_audit"] = audit
                    st.session_state["producto_html"] = html_part
                    st.session_state["producto_roadmap"] = roadmap
                    st.success("Motor V1.0.1 completado: auditoría, workbook y roadmap generados.",
                               icon=":material/check_circle:")
                    st.caption(obs.last_line())
            except Exception as e:
                st.error(f"Error: {e}", icon=":material/error:")

# ── Resultados guardados en la sesión ────────────────────────────────────
if st.session_state.get("producto_html"):
    if st.session_state.get("producto_audit"):
        with st.expander("Auditoría ingenieril (quality gates, DQS y decisiones)",
                         expanded=False, icon=":material/fact_check:"):
            st.markdown(st.session_state["producto_audit"])

    st.subheader("Vista previa del workbook", icon=":material/description:")
    mostrar_workbook(st.session_state["producto_html"])

    c5, c6 = st.columns(2)
    with c5:
        pdf, error_pdf = construir_pdf(st.session_state["producto_html"])
        if pdf:
            st.download_button("Descargar PDF del producto", data=pdf,
                               file_name="producto_alto_valor.pdf",
                               mime="application/pdf", width="stretch",
                               icon=":material/picture_as_pdf:")
        else:
            st.error(f"No se pudo generar el PDF: {error_pdf}", icon=":material/error:")
    with c6:
        if st.session_state.get("producto_roadmap"):
            st.subheader("Roadmap de carpetas", icon=":material/folder_open:")
            st.markdown(st.session_state["producto_roadmap"])

    st.divider()
    st.subheader("Siguiente paso", icon=":material/arrow_forward:")
    st.markdown("La landing reutilizará este workbook automáticamente: no hace falta "
                "volver a pegar el contenido.")
    if st.button("Crear la landing a partir de este producto", type="primary",
                 width="stretch", icon=":material/rocket_launch:"):
        st.switch_page("app_pages/landing.py")
