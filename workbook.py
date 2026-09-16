"""Vista previa saneada y conversión a PDF del workbook generado por el modelo."""

from __future__ import annotations

import io
import re

import streamlit as st
from xhtml2pdf import pisa

from sanitize import limpiar_html

__all__ = ["CSS_IMPRESION", "documento_pdf", "construir_pdf", "mostrar_workbook",
           "texto_plano"]

# Caracteres de contexto que se reenvían a las fases siguientes cuando se
# reutiliza el workbook (landing, design pack).
LIMITE_CONTEXTO = 6000


def texto_plano(html: str | None) -> str:
    """Convierte el workbook HTML en texto plano para reutilizarlo como contexto.

    La landing y el Design Pack no necesitan el marcado: solo el contenido.
    """
    if not html:
        return ""
    sin_etiquetas = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", sin_etiquetas).strip()[:LIMITE_CONTEXTO]

# Hoja de estilo con la que se imprime el workbook. El CSS que emite el modelo
# se descarta en el saneado, así que la maquetación de impresión la pone la app
# (incluida la clase .page-break que pide el prompt).
CSS_IMPRESION = (
    "<style>"
    "body{font-family:Helvetica;color:#222;padding:40px;line-height:1.5;}"
    "h1{color:#004466;border-bottom:3px solid #004466;padding-bottom:10px;}"
    "h2{color:#006699;margin-top:25px;}"
    "table{width:100%;border-collapse:collapse;margin:15px 0;}"
    "th,td{border:1px solid #ccc;padding:10px;text-align:left;}"
    "th{background:#f0f4f8;}"
    "hr{border:none;border-top:1px solid #ddd;}"
    "@page{size:A4;margin:2cm;}"
    ".page-break{page-break-before:always;}"
    "</style>"
)


def documento_pdf(cuerpo: str) -> str:
    """Envuelve el cuerpo ya saneado en un documento con la hoja de impresión."""
    return f"<html><head>{CSS_IMPRESION}</head><body>{cuerpo}</body></html>"


@st.cache_data(show_spinner="Generando el PDF…", max_entries=4)
def construir_pdf(html_raw: str) -> tuple[bytes | None, str]:
    """Convierte el workbook a PDF y devuelve ``(bytes, mensaje de error)``.

    Se sanea ANTES de convertir, igual que la vista previa, por dos motivos:

    * xhtml2pdf resuelve las referencias ``url(...)`` del CSS y puede llegar a
      descargar recursos remotos desde el servidor (SSRF) a partir de HTML
      generado por el modelo.
    * su parser de CSS lanza CSSParseError con entradas hostiles, así que el
      PDF fallaba directamente.

    Se cachea porque xhtml2pdf es lento y bloqueante y el HTML solo cambia al
    regenerar el workbook.
    """
    cuerpo = limpiar_html(html_raw)
    if not cuerpo.strip():
        return None, "el HTML quedó vacío tras el saneado de seguridad."

    buffer = io.BytesIO()
    try:
        resultado = pisa.CreatePDF(io.StringIO(documento_pdf(cuerpo)), dest=buffer)
    except Exception as e:  # xhtml2pdf puede lanzar con HTML degenerado
        return None, f"{type(e).__name__}: {e}"

    if resultado.err:
        return None, f"xhtml2pdf reportó {resultado.err} error(es) al maquetar el HTML."

    pdf = buffer.getvalue()
    if not pdf:
        return None, "el PDF resultante está vacío."
    return pdf, ""


def mostrar_workbook(html_raw: str) -> None:
    """Renderiza el workbook saneado, avisando si el saneado lo dejó vacío."""
    limpio = limpiar_html(html_raw)
    if limpio.strip():
        st.markdown(f'<div class="workbook-preview">{limpio}</div>',
                    unsafe_allow_html=True)
    else:
        st.warning("La vista previa quedó vacía tras el saneado de seguridad: "
                   "el HTML generado solo contenía etiquetas descartadas.",
                   icon=":material/gpp_maybe:")
