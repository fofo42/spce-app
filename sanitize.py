"""Saneado del HTML generado por el modelo antes de renderizarlo en la app.

Por qué existe
--------------
`app.py` renderiza el workbook que devuelve Claude con
`st.markdown(..., unsafe_allow_html=True)`. Ese HTML procede de una cadena
LLM -> PDF/imagen subida por el usuario -> prompt -> HTML, así que es una
entrada no confiable: un PDF manipulado puede inducir al modelo a emitir
`<script>` y ejecutar JavaScript en el navegador de quien usa la app
(robo de la sesión, del workbook o de la clave que haya en la barra lateral).

Enfoque
-------
Allowlist estricta, sin dependencias externas:

* Etiquetas de estructura/maquetación: se conservan con atributos filtrados.
* Etiquetas peligrosas (`script`, `style`, `iframe`, `svg`, ...): se eliminan
  junto con su contenido.
* Cualquier otra etiqueta: se "desenvuelve" (se quitan las etiquetas y se
  conserva el texto).
* Atributos: se descartan todos los `on*` y todo lo que no esté en la lista.
* `style`: solo propiedades y valores de una allowlist; se rechaza `url(`,
  `expression(`, `javascript:`, `@import`, barras invertidas y comentarios CSS.
* `href`: solo `https://`, `http://`, `mailto:`, `tel:` o anclas `#`.
* Los comentarios y el doctype se descartan.
"""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

__all__ = ["limpiar_html", "ETIQUETAS_PERMITIDAS", "ETIQUETAS_DESCARTADAS"]

# ── Etiquetas ────────────────────────────────────────────────────────────
# Se conservan (con atributos filtrados).
ETIQUETAS_PERMITIDAS = frozenset({
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "div", "span", "section", "article", "header", "footer", "main",
    "blockquote", "pre", "code", "small", "sub", "sup", "mark",
    "strong", "b", "em", "i", "u", "s", "del", "ins", "abbr",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption", "colgroup", "col",
    "a", "br", "hr",
})

# Se eliminan junto con TODO su contenido. Ojo: aquí solo van etiquetas cuyo
# contenido no debe verse nunca. Las de estructura (html, body) NO van aquí:
# se desenvuelven más abajo, porque descartarlas borraría el documento entero.
ETIQUETAS_DESCARTADAS = frozenset({
    # ejecución de código
    "script", "style", "iframe", "frame", "frameset", "object", "embed",
    "applet", "param", "noscript", "template", "svg", "math", "canvas",
    # formularios (no aportan nada al workbook y permiten inyección)
    "form", "input", "button", "select", "option", "textarea", "label",
    "fieldset", "legend",
    # metadatos y recursos externos
    "link", "meta", "base", "head", "title",
    # multimedia
    "img", "picture", "map", "area", "audio", "video", "source", "track",
})

# Etiquetas sin cierre ("void elements" de HTML). Es importante que estén
# TODAS: una etiqueta prohibida que además sea void (img, input, link, meta,
# embed, ...) no debe activar el descarte de contenido, porque nunca aparece
# su cierre y se tragaría el resto del documento.
ETIQUETAS_VACIAS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

ATRIBUTOS_PERMITIDOS = frozenset({
    "class", "style", "colspan", "rowspan", "scope", "headers", "title",
    "align", "valign", "href", "width", "height", "start", "type", "value",
})

_PROPIEDADES_CSS = frozenset({
    # texto
    "text-align", "vertical-align", "font-weight", "font-style", "font-size",
    "font-family", "line-height", "letter-spacing", "text-decoration",
    "text-transform", "white-space", "text-indent", "color",
    # cajas
    "background-color", "border", "border-top", "border-bottom", "border-left",
    "border-right", "border-collapse", "border-color", "border-style",
    "border-width", "border-spacing", "border-radius",
    "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
    "margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
    "width", "min-width", "max-width", "height", "min-height", "display",
    # impresión / paginación
    "page-break-before", "page-break-after", "page-break-inside",
    "break-before", "break-after", "break-inside",
    # listas
    "list-style", "list-style-type", "list-style-position",
})

_VALOR_CSS_PELIGROSO = re.compile(
    r"url\s*\(|expression\s*\(|javascript\s*:|vbscript\s*:|@import|\\|/\*|"
    r"behavior\s*:|-moz-binding|&#",
    re.IGNORECASE,
)
_FUNCION_CSS_SEGURA = re.compile(r"^(rgb|rgba|hsl|hsla)\([0-9.,%\s]+\)$")
_CARACTERES_PELIGROSOS = re.compile(r"[<>\"'`]")
_CLASE_VALIDA = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_URL_SEGURA = re.compile(r"^(https?://|mailto:|tel:|#)", re.IGNORECASE)


def _sanear_estilo(valor: str) -> str:
    """Conserva solo declaraciones CSS de la allowlist y con valores seguros."""
    salida: list[str] = []
    for declaracion in valor.split(";"):
        if ":" not in declaracion:
            continue
        prop, _, val = declaracion.partition(":")
        prop = prop.strip().lower()
        val = " ".join(val.split())
        if prop not in _PROPIEDADES_CSS or not val:
            continue
        if _VALOR_CSS_PELIGROSO.search(val) or _CARACTERES_PELIGROSOS.search(val):
            continue
        if "(" in val and not _FUNCION_CSS_SEGURA.match(val):
            continue
        salida.append(f"{prop}:{val}")
    return ";".join(salida)


def _filtrar_atributos(attrs: list[tuple[str, str | None]]) -> str:
    partes: list[str] = []
    for nombre, valor in attrs:
        nombre = nombre.lower()
        # Todo manejador de eventos (onclick, onerror, onload, ...) fuera.
        if nombre.startswith("on") or nombre not in ATRIBUTOS_PERMITIDOS:
            continue
        valor = valor or ""

        if nombre == "style":
            valor = _sanear_estilo(valor)
            if not valor:
                continue
        elif nombre == "class":
            valor = " ".join(_CLASE_VALIDA.findall(valor))
            if not valor:
                continue
        elif nombre in ("colspan", "rowspan", "start"):
            if not valor.strip().isdigit():
                continue
            valor = valor.strip()
        elif nombre in ("width", "height"):
            if not re.fullmatch(r"\d{1,4}(px|%)?", valor.strip()):
                continue
            valor = valor.strip()
        elif nombre in ("align", "valign"):
            if valor.strip().lower() not in ("left", "right", "center", "justify", "top", "middle", "bottom"):
                continue
            valor = valor.strip().lower()
        elif nombre == "href":
            if not _URL_SEGURA.match(valor.strip()):
                continue
            valor = valor.strip()
        elif nombre in ("scope", "type"):
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,20}", valor.strip()):
                continue
            valor = valor.strip()

        partes.append(f' {nombre}="{escape(valor, quote=True)}"')
    return "".join(partes)


class _Saneador(HTMLParser):
    """Reconstruye el HTML dejando pasar solo lo permitido."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._salida: list[str] = []
        self._abiertas: list[str] = []
        self._descartando: str | None = None

    # -- API ---------------------------------------------------------------
    def resultado(self) -> str:
        while self._abiertas:
            self._salida.append(f"</{self._abiertas.pop()}>")
        return "".join(self._salida)

    # -- HTMLParser --------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self._descartando is not None:
            return
        if tag in ETIQUETAS_DESCARTADAS:
            # Solo se descarta el contenido si la etiqueta tiene cierre; las
            # "void" (img, input, link, meta, embed...) no lo tienen y
            # activarlo se tragaría el resto del documento.
            if tag not in ETIQUETAS_VACIAS:
                self._descartando = tag
            return
        if tag not in ETIQUETAS_PERMITIDAS:
            return  # se desenvuelve: el contenido se conserva
        self._salida.append(f"<{tag}{_filtrar_atributos(attrs)}>")
        if tag not in ETIQUETAS_VACIAS:
            self._abiertas.append(tag)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if self._descartando is not None:
            return
        if tag in ETIQUETAS_DESCARTADAS or tag not in ETIQUETAS_PERMITIDAS:
            return
        atributos = _filtrar_atributos(attrs)
        if tag in ETIQUETAS_VACIAS:
            # <br/>, <hr/>
            self._salida.append(f"<{tag}{atributos}>")
        else:
            # El modelo cierra a veces celdas como <td/>; se emite vacía.
            self._salida.append(f"<{tag}{atributos}></{tag}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._descartando is not None:
            if tag == self._descartando:
                self._descartando = None
            return
        if tag in ETIQUETAS_VACIAS or tag not in ETIQUETAS_PERMITIDAS:
            return
        if tag not in self._abiertas:
            return
        # Cierre tolerante: cierra lo que quede abierto por encima.
        while self._abiertas:
            abierta = self._abiertas.pop()
            self._salida.append(f"</{abierta}>")
            if abierta == tag:
                break

    def handle_data(self, data):
        if self._descartando is None:
            self._salida.append(escape(data, quote=False))

    def handle_comment(self, data):  # noqa: ARG002 - los comentarios se descartan
        return

    def handle_decl(self, decl):
        return

    def handle_pi(self, data):
        return

    def unknown_decl(self, data):
        return


def limpiar_html(html: str | None) -> str:
    """Devuelve una versión segura de `html` para renderizar en la app.

    Conserva la estructura útil del workbook (tablas, encabezados, listas,
    casillas) y elimina todo lo que pueda ejecutar código.
    """
    if not html:
        return ""
    parser = _Saneador()
    parser.feed(html)
    parser.close()
    return parser.resultado()
