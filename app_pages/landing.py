"""Fase 2 · SPCE — brief de landing para Lovable.

Script directo. Reutiliza automáticamente el workbook de la Fase 1 si existe,
que es lo que antes hacía el modo "Flujo completo".
"""

import streamlit as st

import observability as obs
from prompts import SPCE_SYSTEM
from workbook import texto_plano

api_key = st.session_state.get("api_key", "")
model_id = st.session_state.get("model_id", "")

feed2 = st.session_state.get("icai_spce_feed", "")
if feed2:
    st.info("Inteligencia ICAI conectada: el SPCE usará el SPCE_FEED "
            "(mensajes por awareness, hooks, objeciones→FAQ).",
            icon=":material/psychology:")

producto_html = st.session_state.get("producto_html")

if producto_html:
    usar_workbook = st.toggle("Usar el workbook generado en la Fase 1 como producto",
                              value=True, key="usar_workbook")
else:
    usar_workbook = False
    st.caption("Todavía no hay workbook de la Fase 1: pega o describe el producto abajo.")

if usar_workbook:
    contexto = texto_plano(producto_html)
    st.caption(f"Contexto tomado del workbook ({len(contexto):,} caracteres).")
else:
    contexto = st.text_area("Describe tu producto o pega aquí su contenido",
                            height=150, key="producto_ctx")

c1, c2 = st.columns(2)
with c1:
    precio = st.text_input("Precio", placeholder="Ej: $27 USD", key="precio")
    garantia = st.text_input("Garantía", placeholder="Ej: 7 días sin preguntas",
                             key="garantia")
with c2:
    gancho = st.text_input("Gancho del anuncio",
                           placeholder="Ej: Deja de adivinar a dónde se va tu sueldo",
                           key="gancho")

if st.button("Generar brief de landing", type="primary", width="stretch",
             icon=":material/rocket_launch:"):
    if not api_key:
        st.error("Introduce tu API Key", icon=":material/key_off:")
    elif not contexto:
        st.error("Falta el producto (genera la Fase 1 o descríbelo)",
                 icon=":material/warning:")
    else:
        with st.spinner("Aplicando SPCE: arquitectura psicológica, copy y brief mobile-first…"):
            prompt = f"""PRODUCTO A VENDER (sistema/workbook real):
{contexto}

PRECIO: {precio} | GARANTÍA: {garantia} | GANCHO DEL ANUNCIO: {gancho}
"""
            if feed2:
                prompt += f"\n=== INTELIGENCIA ICAI (SPCE_FEED) ===\n{feed2}\n"
            prompt += """
Genera el Brief de Construcción completo para Lovable:
1) Sistema de Diseño (mobile-first, paleta, tipografía).
2) Bloques en orden: Hero → Problema/Agitación → Solución (módulos prácticos) → Demo visual (placeholder) → Oferta+Precio+Garantía → FAQ estratégico → CTA final. Copy EXACTO de cada bloque.
3) Instrucciones técnicas (placeholders sin stock, botones full-width, acordeón FAQ).
4) Auditoría CRO final (score 0-10, riesgos, próximos pasos)."""
            try:
                client = obs.cliente_observado(api_key, model_id)
                response = client.messages.create(
                    model=model_id, max_tokens=8000,
                    system=SPCE_SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                )
                # No se asume que el primer bloque sea texto: se recogen todos
                # los bloques de texto, que es lo único que se puede mostrar.
                partes = [b.text for b in response.content
                          if getattr(b, "type", "") == "text"]
                brief = "\n\n".join(partes).strip()

                if not brief:
                    st.error("La respuesta no contenía texto que mostrar.",
                             icon=":material/error:")
                else:
                    st.session_state["brief_landing"] = brief
                    st.success("Brief de landing generado.", icon=":material/check_circle:")
                    st.caption(obs.last_line())
            except Exception as e:
                st.error(f"Error: {e}", icon=":material/error:")

if st.session_state.get("brief_landing"):
    st.divider()
    st.subheader("Brief de construcción", icon=":material/description:")
    st.markdown(st.session_state["brief_landing"])
    st.download_button("Descargar el brief", data=st.session_state["brief_landing"],
                       file_name="brief_landing.txt", mime="text/plain",
                       width="stretch", icon=":material/download:")
