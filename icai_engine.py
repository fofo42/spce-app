import observability as obs
import streamlit as st
import anthropic
import base64
import io
import json
from pypdf import PdfReader

SECCIONES = [
    "=== DOSSIER ===", "=== SEARCH ===", "=== EVALUATION ===", "=== DECISION ===",
    "=== MESSAGE ===", "=== FUNNEL ===", "=== LIFECYCLE ===",
    "=== OFFER_FEED ===", "=== SPCE_FEED ===", "=== DESIGN_FEED ===",
]

# Traduce cada separador de texto antiguo a la clave JSON equivalente.
JSON_KEYS = {
    "=== DOSSIER ===": "dossier",
    "=== SEARCH ===": "search",
    "=== EVALUATION ===": "evaluation",
    "=== DECISION ===": "decision",
    "=== MESSAGE ===": "message",
    "=== FUNNEL ===": "funnel",
    "=== LIFECYCLE ===": "lifecycle",
    "=== OFFER_FEED ===": "offer_feed",
    "=== SPCE_FEED ===": "spce_feed",
    "=== DESIGN_FEED ===": "design_feed",
}

ICAI_SYSTEM = """Eres el ICAI-ENGINE V1.2 (DEEP): sistema de inteligencia del cliente con 7 capas
(state, decision, discovery, conversion, lifecycle). No generas avatares: modelas el SISTEMA DE
DECISIÓN del cliente y lo conviertes en inteligencia utilizable por el Offer Engine, el SPCE y el Design Pack.

CONTRATO DE INPUTS: NICHE y PRODUCT obligatorios; CUSTOMER EVIDENCE opcional.
Jerarquía: USER_PROVIDED > DOCUMENTED > EXTERNALLY_VERIFIED > INFERENCE > HYPOTHESIS > UNKNOWN.

CONTRATO EPISTÉMICO (SIEMPRE ACTIVO):
- Etiqueta toda afirmación relevante: [FACT] [EVIDENCE] [INFERENCE] [HYPOTHESIS] [UNKNOWN] + confianza (VERY LOW→VERY HIGH).
- Lenguaje: REAL (cita literal con fuente) / DERIVED (paráfrasis con fuente) / SIMULATED (hipótesis; nunca como cita real).
  El lenguaje del producto/anuncio/landing es PRODUCT_MARKET_LANGUAGE, nunca voz del cliente.
- UNKNOWN es válido: no rellenes huecos con invención. Correlación ≠ causación.
  Alto impacto + baja confianza = HYPOTHESIS, nunca fact.
- Prohibido: fabricar reviews, testimonios, métricas, comportamiento, urgencia o escasez; manipulación; miedo artificial.

CADENA DE DECISIÓN: SITUACIÓN → PROBLEMA → DOLOR → DESEO → MOTIVACIÓN → BÚSQUEDA → EVALUACIÓN →
ELECCIÓN → DECISIÓN → COMPRA → IMPLEMENTACIÓN → RESULTADO → RETENCIÓN → EXPANSIÓN → APRENDIZAJE.

PROCESO INTERNO OBLIGATORIO (no omitas):
segmentación conductual con SEGMENT_PRIORITY (0-1) y bandas (≥0.80 PRIMARY / 0.65-0.79 HIGH /
0.50-0.64 SECONDARY / 0.35-0.49 LOW / <0.35 DEPRIORITIZED; prioridad ≠ confianza);
5+ dolores distintos (trigger, frecuencia, severidad, coste, lenguaje);
deseos surface→funcional→emocional→identidad; intentos fallidos y creencias;
objeciones (tipo, pregunta interna, riesgo, qué la resolvería; "es caro" se descompone);
awareness (UNAWARE→MOST AWARE) y readiness (LOW→IMMEDIATE) por segmento;
triggers reales y PURCHASE WINDOW (CLOSED/DISTANT/APPROACHING/OPEN/PEAK/CLOSING) detectando urgencia artificial;
búsquedas e information gaps; alternativas incluyendo DIY, gratis y STATUS QUO con criterios de evaluación;
drivers motivacionales y emocionales sin sobreinterpretación; blockers y condiciones de decisión;
funnel como transiciones de estado; lifecycle post-compra.

SALIDA:
Responde ÚNICAMENTE con un objeto JSON válido (nada de texto antes o después, nada de bloques ```), con EXACTAMENTE estas 10 claves (cada valor en formato Markdown):

{
  "dossier": "Dossier del cliente: contexto; matriz de segmentos con priority; problemas/dolores; deseos/motivaciones; intentos/creencias; objeciones; language bank con estado y tipo de fuente; awareness×readiness; triggers y purchase window; 6 ángulos exactamente 2 money saving / 2 income generation / 2 time-stress-simplicity, marcando AXIS_MISMATCH como HYPOTHESIS 'no usar sin validar' si un eje no encaja; 3 promesas con tiempo+transformación+resultado concreto+believability+riesgo+evidencia requerida aplicando PROMISE SAFETY; bonos con función; upsells y qué NO debe ser upsell; mapa de evidencia + UNKNOWNs + qué recolectar; master opportunity map por impacto×confianza/coste.",
  "search": ".15: queries por etapa PROBLEM/SOLUTION/COMPARISON/PURCHASE con estado REAL/DERIVED/SIMULATED; necesidades de información; information gaps → oportunidades de contenido, FAQ, prueba, lead magnet.",
  "evaluation": ".16: choice set (producto, competidores, DIY, gratis, status quo, no hacer nada); criterios de evaluación con peso relativo; trade-offs aceptados/rechazados; por qué el cliente elegiría esto frente al status quo; gaps percibidos vs alternativas.",
  "decision": ".17: blockers (trust, value, risk, effort, information); condiciones que deben cumplirse para que elija; decision levers por segmento; señales observables de intent vs interés.",
  "message": ".18: mensaje por estado de awareness; hooks desde lenguaje REAL; mecanismo a explicar; pruebas requeridas por claim; objeciones→respuestas; CTA por readiness; qué NO decir por falta de evidencia.",
  "funnel": ".19-.20: funnel como estados del cliente (exposición→atención→evaluación→intent→acción→activación): qué necesita creer/entender/sentir en cada etapa para avanzar; hipótesis de drop-off con estado epistémico; 3-5 experimentos (hipótesis, variable, métrica primaria, guardrail).",
  "lifecycle": ".21: activación y primer quick win; onboarding mínimo; fricción de implementación; retención y recurrencia; hipótesis de riesgo de reembolso; timing y condición del upsell lógico.",
  "offer_feed": "Para el Offer Engine, máx 15 líneas: obstáculos principales → 6 pilares con formatos de entregable; bonus map con función; medición; lenguaje del cliente a preservar; segmentos prioritarios; quick win/lifecycle.",
  "spce_feed": "Para la landing, máx 15 líneas: mensaje por awareness; hooks; objeciones→FAQ; lenguaje a usar/evitar; pruebas requeridas; CTA por readiness; promesa segura principal; diferenciación vs status quo.",
  "design_feed": "Para el Design Pack, máx 10 líneas: tono, estilo visual, emoción por segmento, iconografía, qué evitar visualmente."
}

IMPORTANTE: escapa correctamente comillas dobles, saltos de línea y caracteres especiales dentro de los valores para que el JSON sea válido y parseable. No escribas nada fuera de ese objeto JSON."""


def _procesar(files, etiqueta):
    texto = ""
    bloques = []
    for f in files or []:
        if f.type == "application/pdf":
            try:
                txt = "\n".join([p.extract_text() or "" for p in PdfReader(io.BytesIO(f.read())).pages])
                texto += f"\n--- {etiqueta} | {f.name} ---\n{txt[:12000]}\n"
            except Exception:
                st.warning(f"⚠️ PDF no legible: {f.name}")
        elif f.type in ["image/png", "image/jpeg"]:
            bloques.append({"type": "text", "text": f"[IMAGEN — {etiqueta}: {f.name}]"})
            bloques.append({"type": "image", "source": {"type": "base64",
                "media_type": f.type, "data": base64.b64encode(f.read()).decode()}})
    return texto, bloques


def _seccion(out, marker):
    if marker not in out:
        return ""
    tail = out.split(marker, 1)[1]
    for m in SECCIONES:
        tail = tail.split(m)[0]
    return tail.strip()


def render(api_key, model_id):
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("🧭 PASO 0: ICAI V1.2 DEEP — Inteligencia de Cliente completa")
    st.markdown("Modela al cliente y su decisión: descubrimiento, evaluación, elección, mensaje, funnel y lifecycle.")

    if st.button("⬅️ Volver al menú", key="v5"):
        st.session_state['modo_seleccionado'] = None
        st.rerun()

    niche = st.text_input("NICHE (obligatorio)", placeholder="Ej: cocina económica para personas sin tiempo")
    prod_files = st.file_uploader("PRODUCTO (PDF/PNG/JPG)", type=['pdf', 'png', 'jpg', 'jpeg'],
                                  accept_multiple_files=True, key="icai_prod")
    prod_desc = st.text_area("O describe el producto", height=90)
    ev_files = st.file_uploader("EVIDENCIA DE CLIENTE opcional (reviews, comentarios, encuestas...)",
                                type=['pdf', 'png', 'jpg', 'jpeg'], accept_multiple_files=True, key="icai_ev")
    ev_text = st.text_area("O pega aquí evidencia textual", height=100)

    if st.button("🧭 Ejecutar ICAI DEEP (Dossier + 6 capas + Puentes)", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Introduce tu API Key en la barra lateral")
        elif not niche.strip():
            st.error("⚠️ El NICHE es obligatorio.")
        elif not prod_files and not prod_desc.strip():
            st.error("⚠️ Falta el PRODUCTO: sube archivos o descríbelo.")
        else:
            with st.spinner("🧠 Modelando cliente: estado → decisión → descubrimiento → conversión → lifecycle..."):
                contenido = []
                pt, pb = _procesar(prod_files, "PRODUCTO")
                et, eb = _procesar(ev_files, "EVIDENCIA DE CLIENTE")
                contenido.append({"type": "text", "text":
                    f"NICHE: {niche}\n\nPRODUCTO (contenido documental):\n{pt}\nDescripción del producto: {prod_desc or '-'}"})
                contenido.extend(pb)
                contenido.append({"type": "text", "text":
                    f"EVIDENCIA DE CLIENTE:\n{et}\n{ev_text or '-'}"})
                contenido.extend(eb)
                contenido.append({"type": "text", "text":
                    "Ejecuta el proceso completo y entrega todas las secciones con sus separadores exactos."})
                try:
                    client = obs.wrap_client(anthropic.Anthropic(api_key=api_key), model_id)

                    st.markdown("##### ✍️ Generando en vivo (texto en bruto; el dossier bonito aparece abajo al terminar):")
                    with client.messages.stream(
                        model=model_id, max_tokens=20000,
                        system=ICAI_SYSTEM,
                        messages=[
                            {"role": "user", "content": contenido},
                            {"role": "assistant", "content": "{"}
                        ]
                    ) as stream:
                        def _generador_texto():
                            for chunk in stream.text_stream:
                                yield chunk
                        raw_text = st.write_stream(_generador_texto())
                        stream.get_final_message()

                    # Empezamos el texto con "{" porque ese carácter no viene incluido
                    # en la respuesta (se lo "regalamos" nosotros para forzar que
                    # Claude continúe directamente en formato JSON).
                    raw_output = "{" + raw_text

                    try:
                        datos = json.loads(raw_output)
                        secciones = {marker: (datos.get(clave) or "").strip() for marker, clave in JSON_KEYS.items()}
                        out = "\n\n".join(f"{marker}\n{secciones[marker]}" for marker in SECCIONES if secciones[marker])
                    except json.JSONDecodeError:
                        # PLAN B: si el JSON viniera mal formado, probamos el formato
                        # antiguo de separadores de texto como respaldo, para no
                        # perder el resultado si algo raro pasa.
                        out = raw_output
                        secciones = {m: _seccion(out, m) for m in SECCIONES}

                    st.session_state['icai_dossier'] = out
                    st.session_state['icai_sections'] = secciones

                    # === PERSISTENCIA EXPLÍCITA DE LOS FEEDS ===
                    st.session_state['icai_offer_feed'] = secciones.get("=== OFFER_FEED ===", "")
                    st.session_state['icai_spce_feed'] = secciones.get("=== SPCE_FEED ===", "")
                    st.session_state['icai_design_feed'] = secciones.get("=== DESIGN_FEED ===", "")
                    st.session_state['icai_ready'] = True  # Flag para confirmar que ICAI está listo

                    if not secciones.get("=== OFFER_FEED ==="):
                        st.warning("⚠️ No se pudo extraer el OFFER_FEED de la respuesta. Revisa el resultado en bruto antes de pasar a la Fase 1.")
                        with st.expander("🔧 Ver respuesta en bruto (para depurar)"):
                            st.code(raw_output[:5000])
                    else:
                        st.success("✅ ICAI DEEP completado: dossier + 6 capas + puentes conectados.")
                    st.caption(obs.last_line())
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    if st.session_state.get('icai_sections'):
        secs = st.session_state['icai_sections']
        nombres = {
            "=== DOSSIER ===": "📋 Customer Dossier (segmentos, dolores, ángulos, promesas)",
            "=== SEARCH ===": "🔍 Search & Discovery (.15)",
            "=== EVALUATION ===": "⚖️ Evaluation & Alternatives incl. status quo (.16)",
            "=== DECISION ===": "🎯 Choice & Decision: blockers y levers (.17)",
            "=== MESSAGE ===": "💬 Message & Persuasion por awareness (.18)",
            "=== FUNNEL ===": "🌀 Funnel como estados + experimentos (.19–.20)",
            "=== LIFECYCLE ===": "♻️ Lifecycle: activación, quick win, reembolso, upsell (.21)",
            "=== OFFER_FEED ===": "🔌 OFFER_FEED → Offer Engine",
            "=== SPCE_FEED ===": "🔌 SPCE_FEED → Landing",
            "=== DESIGN_FEED ===": "🔌 DESIGN_FEED → Design Pack",
        }
        for m in SECCIONES:
            if secs.get(m):
                with st.expander(nombres[m], expanded=(m in ("=== OFFER_FEED ===", "=== SPCE_FEED ==="))):
                    st.markdown(secs[m])
        st.download_button("📥 Descargar dossier DEEP completo", data=st.session_state['icai_dossier'],
                           file_name="icai_dossier_deep.md", mime="text/markdown")
        st.info("✅ Puentes conectados: la Fase 1, la Fase 2 y el Design Pack usarán esta inteligencia automáticamente.")

        # ── Botones de transición ─
        st.markdown("---")
        st.subheader("🚀 ¿Qué quieres hacer ahora?")
        st.markdown("La inteligencia de cliente ya está conectada. Puedes usarla para:")

        # Debug visual: mostrar que los feeds están listos
        offer_len = len(st.session_state.get('icai_offer_feed', ''))
        st.caption(f"📊 OFFER_FEED listo: {offer_len} caracteres | SPCE_FEED: {len(st.session_state.get('icai_spce_feed', ''))} chars | DESIGN_FEED: {len(st.session_state.get('icai_design_feed', ''))} chars")

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            if st.button("📦 Modelar Producto (Fase 1)", use_container_width=True, type="primary"):
                st.session_state['modo_seleccionado'] = 'producto'
                st.rerun()
        with tc2:
            if st.button("🎨 Design Pack", use_container_width=True):
                st.session_state['modo_seleccionado'] = 'design'
                st.rerun()
        with tc3:
            if st.button("🧭 Volver al menú", use_container_width=True):
                st.session_state['modo_seleccionado'] = None
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
