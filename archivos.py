"""Lectura de archivos subidos y conversión a bloques de contenido para la API."""

from __future__ import annotations

import base64
import io

import streamlit as st
from pypdf import PdfReader

__all__ = ["procesar_archivos", "LIMITE_TEXTO_PDF"]

# Caracteres de texto que se extraen de cada PDF. Un PDF largo puede tener
# cientos de miles de caracteres y no cabe (ni aporta) en el contexto.
LIMITE_TEXTO_PDF = 12000


def procesar_archivos(files, etiqueta: str) -> tuple[str, list[dict]]:
    """Convierte los archivos subidos en ``(texto, bloques)`` para Anthropic.

    Los PDF se extraen a texto recortado. Las imágenes se envían como bloques
    de imagen en base64, cada una precedida por una etiqueta textual para que
    el modelo sepa a qué input corresponde.
    """
    texto = ""
    bloques: list[dict] = []

    for f in files or []:
        if f.type == "application/pdf":
            try:
                paginas = PdfReader(io.BytesIO(f.read())).pages
                txt = "\n".join(p.extract_text() or "" for p in paginas)
                texto += f"\n--- {etiqueta} | {f.name} ---\n{txt[:LIMITE_TEXTO_PDF]}\n"
            except Exception:
                st.warning(f"PDF no legible: {f.name}", icon=":material/warning:")

        elif f.type in ("image/png", "image/jpeg"):
            bloques.append({"type": "text", "text": f"[IMAGEN — {etiqueta}: {f.name}]"})
            bloques.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": f.type,
                    "data": base64.b64encode(f.read()).decode(),
                },
            })

    return texto, bloques
