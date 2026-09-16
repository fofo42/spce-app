"""Utilidades de parseo de las respuestas del modelo.

Originalmente cada motor de la app tenía su propia copia de la lógica de
"buscar una sección entre separadores" (en app.py, icai_engine.py y
design_pack.py). Aquí se centraliza, junto con la extracción tolerante de JSON.

Nota sobre el "Plan B" anterior: el prompt pide un objeto JSON puro, pero el
respaldo original buscaba marcadores de texto (`=== FIN_AUDIT ===`,
`=== DOSSIER ===`) que el prompt actual ya NO pide emitir. Ese respaldo no podía
funcionar. `extraer_json` cubre el caso real: el modelo envuelve el JSON en un
bloque ``` o antepone una línea.
"""

from __future__ import annotations

import json
import re

__all__ = ["extraer_json", "extraer_seccion"]

_BLOQUE_CODIGO = re.compile(r"```(?:json)?\s*(.+?)```", re.DOTALL)


def extraer_json(texto: str | None) -> dict | None:
    """Rescata el primer objeto JSON de una respuesta del modelo.

    Devuelve ``None`` si no hay ningún objeto parseable. Estrategia:

    1. `json.loads` directo (el caso que pide el prompt).
    2. Contenido de un bloque de código ```json ... ``` o ``` ... ```.
    3. Primer objeto balanceado del texto, respetando cadenas y escapes, para
       que un `{` dentro de una cadena no descuadre el recuento.
    """
    if not texto:
        return None

    candidatos: list[str] = [texto.strip()]
    candidatos.extend(m.group(1).strip() for m in _BLOQUE_CODIGO.finditer(texto))

    for candidato in candidatos:
        try:
            datos = json.loads(candidato)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(datos, dict):
            return datos

    for inicio in _posiciones_de(texto, "{"):
        objeto = _objeto_balanceado(texto, inicio)
        if objeto is None:
            continue
        try:
            datos = json.loads(objeto)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(datos, dict):
            return datos

    return None


def _posiciones_de(texto: str, caracter: str):
    indice = texto.find(caracter)
    while indice != -1:
        yield indice
        indice = texto.find(caracter, indice + 1)


def _objeto_balanceado(texto: str, inicio: int) -> str | None:
    """Devuelve el texto desde `inicio` hasta el `}` que cierra el objeto."""
    profundidad = 0
    en_cadena = False
    escapado = False
    for i in range(inicio, len(texto)):
        c = texto[i]
        if escapado:
            escapado = False
            continue
        if c == "\\":
            escapado = True
            continue
        if c == '"':
            en_cadena = not en_cadena
            continue
        if en_cadena:
            continue
        if c == "{":
            profundidad += 1
        elif c == "}":
            profundidad -= 1
            if profundidad == 0:
                return texto[inicio:i + 1]
    return None


def extraer_seccion(texto: str | None, marcador: str, marcadores) -> str:
    """Devuelve el contenido entre `marcador` y el siguiente separador.

    `marcadores` es la lista completa de separadores posibles, para cortar en
    el que aparezca antes.
    """
    if not texto or marcador not in texto:
        return ""
    cola = texto.split(marcador, 1)[1]
    for m in marcadores:
        cola = cola.split(m)[0]
    return cola.strip()
