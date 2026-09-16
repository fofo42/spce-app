"""Portada: estado del proyecto y accesos al flujo.

Script directo. Sirve de panel para saber qué artefactos existen ya en la
sesión y cuál es el siguiente paso.
"""

import streamlit as st

st.markdown("Encadena cuatro motores sobre la inteligencia de cliente. Cada fase "
            "reutiliza automáticamente lo que produjo la anterior, así que no hay que "
            "volver a pegar contexto.")

icai_listo = bool(st.session_state.get("icai_offer_feed"))
producto_listo = bool(st.session_state.get("producto_html"))
landing_lista = bool(st.session_state.get("brief_landing"))
design_listo = bool(st.session_state.get("design_pack"))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Paso 0 · ICAI", "listo" if icai_listo else "pendiente")
c2.metric("Fase 1 · Producto", "listo" if producto_listo else "pendiente")
c3.metric("Fase 2 · Landing", "listo" if landing_lista else "pendiente")
c4.metric("Design Pack", "listo" if design_listo else "pendiente")

st.divider()

st.subheader("El flujo", icon=":material/route:")
st.markdown("""
1. **Paso 0 · ICAI** — modela el sistema de decisión del cliente y genera los puentes
   `OFFER_FEED`, `SPCE_FEED` y `DESIGN_FEED` que consumen las fases siguientes.
2. **Fase 1 · Producto** — Offer Engine V1.0.1: auditoría con DQS, workbook imprimible
   en PDF y roadmap de carpetas.
3. **Fase 2 · Landing** — brief de página de ventas mobile-first para Lovable.
4. **Design Pack** — prompts listos para Canva, Gamma y Bing.
""")

st.info("El orden recomendado es empezar por el Paso 0: sin él, la Fase 1 funciona "
        "igual pero remodela un producto que tengas que subir tú.",
        icon=":material/lightbulb:")

st.divider()

st.subheader("Empezar", icon=":material/play_arrow:")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Paso 0 · ICAI", width="stretch", type="primary",
                 icon=":material/explore:"):
        st.switch_page("app_pages/icai.py")
with c2:
    if st.button("Fase 1 · Producto", width="stretch", icon=":material/inventory_2:"):
        st.switch_page("app_pages/producto.py")
with c3:
    if st.button("Design Pack", width="stretch", icon=":material/palette:"):
        st.switch_page("app_pages/design.py")
