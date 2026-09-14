import streamlit as st
import anthropic
import base64
import io
from pypdf import PdfReader

ICAI_SYSTEM = """Eres el ICAI-ENGINE (Ideal Customer & Avatar Intelligence Engine) V1.1.
No generas avatares demográficos: modelas el SISTEMA DE DECISIÓN del cliente.

CONTRATO DE INPUTS: NICHE y PRODUCT obligatorios; EVIDENCIA DE CLIENTE opcional.
Jerarquía: USER_PROVIDED > DOCUMENTED > EXTERNALLY_VERIFIED > INFERENCE > HYPOTHESIS > UNKNOWN.

CONTRATO EPISTÉMICO (siempre activo):
- Etiqueta toda afirmación: [FACT] [EVIDENCE] [INFERENCE] [HYPOTHESIS] [UNKNOWN] + confianza (VERY LOW→VERY HIGH).
- Lenguaje: REAL (cita con fuente) / DERIVED (paráfrasis con fuente) / SIMULATED (hipótesis, nunca como cita real).
  El lenguaje del producto/anuncio/landing es PRODUCT_MARKET_LANGUAGE, nunca voz del cliente.
- UNKNOWN es válido: no rellenes con invención. Correlación ≠ causación.
- Prohibido: fabricar reviews, testimonios, métricas, comportamiento, urgencia o escasez; manipulación; miedo artificial.

CADENA DE DECISIÓN: SITUACIÓN → PROBLEMA → DOLOR → DESEO → MOTIVACIÓN → BÚSQUEDA → EVALUACIÓN → ELECCIÓN → DECISIÓN → COMPRA → IMPLEMENTACIÓN → RESULTADO → RETENCIÓN → EXPANSIÓN → APRENDIZAJE.

PROCESO INTERNO (no omitas): contexto y cliente; segmentación conductual (no demográfica) con SEGMENT_PRIORITY (0-1) y bandas (≥0.80 PRIMARY / 0.65-0.79 HIGH / 0.50-0.64 SECONDARY / 0.35-0.49 LOW / <0.35 DEPRIORITIZED); regla PRIORITY ≠ CONFIDENCE (prioridad alta + confianza baja = EXPERIMENTAL SEGMENT); 5+ dolores distintos (trigger, frecuencia, severidad, coste, lenguaje); deseos surface→funcional→emocional→identidad; intentos fallidos y creencias; objeciones (tipo, pregunta interna, riesgo, qué la resolvería; "es caro" se descompone); awareness (UNAWARE→MOST AWARE) y readiness (LOW→IMMEDIATE) por segmento; triggers reales y PURCHASE WINDOW por segmento (CLOSED/DISTANT/APPROACHING/OPEN/PEAK/CLOSING) detectando urgencia artificial; búsqueda e information gaps; alternativas incluyendo DIY, gratis y STATUS QUO; motivaciones y drivers emocionales sin sobreinterpretar.

CARDINALIDADES: exactamente 6 ángulos de venta (2 money saving, 2 income generation, 2 time/stress/simplicity; si un eje no encaja, marca AXIS_MISMATCH y manténlo como HYPOTHESIS "no usar sin validar"); exactamente 3 promesas con tiempo + transformación + resultado concreto + believability + riesgo + evidencia requerida; PROMISE SAFETY: bloquea promesas que excedan la evidencia.

SALIDA EXACTA CON ESTOS SEPARADORES:
=== DOSSIER ===
(Customer Intelligence Dossier: A contexto/perfil; B matriz de segmentos con priority; C mapa problemas/dolores; D deseos/motivaciones; E intentos fallidos/creencias; F mapa objeciones; G language bank con estado y tipo de fuente; H awareness×readiness; I triggers y purchase windows; J alternativas y criterios incluido status quo; K 6 ángulos; L 3 promesas con promise safety; M bonus opportunities con función; N upsell opportunities y qué NO debe ser upsell; O mapa evidencia/confianza + UNKNOWNs + qué recolectar; P resumen estratégico + Master Opportunity Map; Q search & discovery queries por etapa.)
=== OFFER_FEED ===
(Máx. 12 líneas: para el Offer Engine: obstáculo principal → 6 pilares sugeridos con formatos de entregable (CHECKLIST/WORKSHEET/TRACKER/TEMPLATE/SCORECARD/DECISION TOOL/PROTOCOL/ROUTINE/QUICK REFERENCE; GUIDE último recurso); bonus map con función; medición; lenguaje del cliente a preservar; segmentos prioritarios.)
=== SPCE_FEED ===
(Máx. 12 líneas: para la landing: mensaje por estado de awareness; hooks desde lenguaje real; objeciones → FAQ; lenguaje a usar/evitar; CTA por readiness; pruebas requeridas; promesa segura principal.)
=== DESIGN_FEED ===
(Máx. 12 líneas: para el Design Pack: tono, estilo visual, emoción por segmento, iconografía, qué evitar visualmente.)
No escribas nada fuera de esos 4 bloques."""


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


def render(api_key, model_id):
    st.markdown('<div class="phase-container">', unsafe_allow_html=True)
    st.subheader("🧭 PASO 0: ICAI — Inteligencia de Cliente")
    st.markdown("Modela al cliente y su decisión. Sus puentes alimentan automáticamente al Offer Engine, al SPCE y al Design Pack.")

    if st.button("⬅️ Volver al menú", key="v5"):
        st.session_state['modo_seleccionado'] = None
        st.rerun()

    niche = st.text_input("NICHE (obligatorio)", placeholder="Ej: cocina económica para personas sin tiempo")
    prod_files = st.file_uploader("PRODUCTO (PDF/PNG/JPG)", type=['pdf', 'png', 'jpg', 'jpeg'],
                                  accept_multiple_files=True, key="icai_prod")
    prod_desc = st.text_area("O describe el producto", height=90)
    ev_files = st.file_uploader("EVIDENCIA DE CLIENTE opcional (reviews, comentarios, encuestas...)",
                                type=['pdf', 'png', 'jpg', 'jpeg'], accept_multiple_files=True, key="icai_ev")
    ev_text = st.text_area("O pega aquí evidencia textual (reviews, comentarios, preguntas de soporte...)", height=120)

    if st.button("🧭 Ejecutar ICAI (Dossier + Puentes)", type="primary", use_container_width=True):
        if not api_key:
            st.error("⚠️ Introduce tu API Key en la barra lateral")
        elif not niche.strip():
            st.error("⚠️ El NICHE es obligatorio.")
        elif not prod_files and not prod_desc.strip():
            st.error("⚠️ Falta el PRODUCTO: sube archivos o descríbelo.")
        else:
            with st.spinner("🧭 Modelando cliente, decisión, lenguaje y oportunidades..."):
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
                    "Ejecuta el dossier completo y los 3 puentes con los separadores exactos."})
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    resp = client.messages.create(model=model_id, max_tokens=16000,
                        system=ICAI_SYSTEM, messages=[{"role": "user", "content": contenido}])
                    out = resp.content[0].text
                    st.session_state['icai_dossier'] = out

                    def bloque(marker):
                        if marker not in out:
                            return ""
                        tail = out.split(marker, 1)[1]
                        for m in ["=== DOSSIER ===", "=== OFFER_FEED ===", "=== SPCE_FEED ===", "=== DESIGN_FEED ==="]:
                            tail = tail.split(m)[0]
                        return tail.strip()

                    st.session_state['icai_offer_feed'] = bloque("=== OFFER_FEED ===")
                    st.session_state['icai_spce_feed'] = bloque("=== SPCE_FEED ===")
                    st.session_state['icai_design_feed'] = bloque("=== DESIGN_FEED ===")
                    st.success("✅ Dossier generado y puentes conectados.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

    if st.session_state.get('icai_dossier'):
        with st.expander("📋 Customer Intelligence Dossier (completo)", expanded=False):
            st.markdown(st.session_state['icai_dossier'])
        st.markdown("### 🔌 Puentes conectados")
        for nombre, key in [("OFFER_FEED → Offer Engine", "icai_offer_feed"),
                            ("SPCE_FEED → Landing", "icai_spce_feed"),
                            ("DESIGN_FEED → Design Pack", "icai_design_feed")]:
            with st.expander(nombre):
                st.markdown(st.session_state.get(key, '') or "(vacío)")
        st.info("✅ A partir de ahora, la Fase 1, la Fase 2 y el Design Pack usarán automáticamente esta inteligencia.")
    st.markdown('</div>', unsafe_allow_html=True)