"""Tests del saneador de HTML.

Se pueden ejecutar de dos formas:

    python tests/test_sanitize.py     # sin dependencias
    pytest tests/                     # si tienes pytest

Cada test comprueba un vector de ataque concreto o una garantía de que el
contenido legítimo del workbook sobrevive.
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sanitize import limpiar_html  # noqa: E402

# ── Eliminación de ejecución de código ───────────────────────────────────

def test_script_se_elimina_con_su_contenido():
    assert limpiar_html("<script>alert(1)</script>") == ""

def test_script_dentro_de_texto_no_sobrevive():
    salida = limpiar_html("<p>antes</p><script>alert(1)</script><p>despues</p>")
    assert "<script" not in salida
    assert "alert" not in salida
    assert "antes" in salida and "despues" in salida

def test_script_mayusculas_y_espacios():
    for carga in ("<SCRIPT>alert(1)</SCRIPT>",
                  "<script >alert(1)</script >",
                  "<ScRiPt>alert(1)</ScRiPt>"):
        salida = limpiar_html(carga)
        assert "script" not in salida.lower()
        assert "alert" not in salida

def test_img_onerror():
    salida = limpiar_html('<img src=x onerror="alert(1)">')
    assert "onerror" not in salida
    assert "alert" not in salida
    assert "img" not in salida.lower()

def test_img_no_se_come_el_resto_del_documento():
    """img es 'void': no debe activar el descarte de contenido."""
    salida = limpiar_html('<img src=x onerror=alert(1)><p>contenido posterior</p>')
    assert "contenido posterior" in salida

def test_iframe_se_elimina_con_su_contenido():
    salida = limpiar_html('<iframe src="https://malo.example"></iframe>')
    assert "iframe" not in salida.lower()
    assert "malo.example" not in salida

def test_svg_con_script_anidado():
    salida = limpiar_html("<svg><script>alert(1)</script></svg>")
    assert "script" not in salida.lower()
    assert "alert" not in salida
    assert "svg" not in salida.lower()

def test_style_se_elimina():
    salida = limpiar_html("<style>body{background:url('javascript:alert(1)')}</style>")
    assert "<style" not in salida.lower()

def test_manejadores_de_eventos_fuera():
    for atributo in ("onclick", "onmouseover", "onload", "onfocus", "ONERROR"):
        salida = limpiar_html(f'<p {atributo}="alert(1)">texto</p>')
        assert atributo.lower() not in salida.lower()
        assert "alert" not in salida
        assert "texto" in salida

def test_href_javascript_se_descarta():
    for malo in ('javascript:alert(1)', 'JaVaScRiPt:alert(1)',
                 'vbscript:msgbox(1)', 'data:text/html;base64,PHNjcmlwdD4='):
        salida = limpiar_html(f'<a href="{malo}">enlace</a>')
        assert "href" not in salida.lower(), f"paso {malo!r}"
        assert "enlace" in salida

def test_href_seguro_se_conserva():
    salida = limpiar_html('<a href="https://ejemplo.com">enlace</a>')
    assert 'href="https://ejemplo.com"' in salida

def test_comentarios_se_descartan():
    salida = limpiar_html("<!-- <script>alert(1)</script> --><p>ok</p>")
    assert "script" not in salida.lower()
    assert "ok" in salida

def test_etiqueta_desconocida_se_desenvuelve():
    salida = limpiar_html("<foo>contenido</foo>")
    assert salida == "contenido"

def test_no_queda_script_ni_con_payloads_compuestos():
    payloads = [
        "<div><script>alert(1)</script></div>",
        '<p onclick="x">a</p>',
        "<object data=x></object>",
        "<embed src=x>",
        "<template><script>alert(1)</script></template>",
        "<math><mtext></mtext></math>",
        '<a href="javascript:void(0)" onclick="alert(1)">x</a>',
        "<iframe srcdoc='<script>alert(1)</script>'></iframe>",
    ]
    for carga in payloads:
        salida = limpiar_html(carga)
        bajo = salida.lower()
        for prohibido in ("<script", "onclick", "onerror", "javascript:", "alert(1)"):
            assert prohibido not in bajo, f"{prohibido!r} sobrevivio en {carga!r} -> {salida!r}"

# ── Saneado de CSS ───────────────────────────────────────────────────────

def test_estilo_seguro_se_conserva():
    salida = limpiar_html('<td style="text-align:center;border:1px solid #ccc">x</td>')
    assert "text-align:center" in salida
    assert "border:1px solid #ccc" in salida

def test_estilo_con_url_se_descarta():
    for malo in ("background:url(javascript:alert(1))",
                 "background-image:url('https://malo/x.png')",
                 "width:expression(alert(1))",
                 "behavior:url(x.htc)",
                 "background:url(data:text/html,x)"):
        salida = limpiar_html(f'<p style="{malo}">texto</p>')
        assert "url(" not in salida.lower(), f"paso {malo!r}"
        assert "expression" not in salida.lower()
        assert "texto" in salida

def test_estilo_propiedad_no_permitida_se_descarta():
    salida = limpiar_html('<p style="position:fixed;top:0;text-align:left">x</p>')
    assert "position" not in salida
    assert "text-align:left" in salida

def test_estilo_rgb_permitido_otras_funciones_no():
    assert "rgb(0,0,0)" in limpiar_html('<p style="color:rgb(0,0,0)">x</p>')
    assert "attr(" not in limpiar_html('<p style="color:attr(title)">x</p>')

def test_estilo_no_puede_escaparse_del_atributo():
    salida = limpiar_html('<p style=\'color:red" onload="alert(1)\'>x</p>')
    assert "onload" not in salida.lower()
    assert "alert" not in salida

# ── Contenido legítimo del workbook ──────────────────────────────────────

def test_estructura_de_tabla_se_conserva():
    html = ("<table><thead><tr><th>Pilar</th><th>Entregable</th></tr></thead>"
            "<tbody><tr><td>P01</td><td>Checklist</td></tr></tbody></table>")
    salida = limpiar_html(html)
    for fragmento in ("<table>", "<thead>", "<th>Pilar</th>", "<tbody>",
                      "<td>P01</td>", "</table>"):
        assert fragmento in salida, f"falta {fragmento!r} en {salida!r}"

def test_casilla_de_verificacion_sobrevive():
    """El workbook usa &#9744; para las casillas imprimibles."""
    salida = limpiar_html("<p>&#9744; Paso uno</p>")
    assert "☐" in salida
    assert "Paso uno" in salida

def test_encabezados_listas_y_saltos():
    salida = limpiar_html("<h1>T</h1><ul><li>a</li></ul><br><hr><p class='page-break'>x</p>")
    for fragmento in ("<h1>T</h1>", "<ul>", "<li>a</li>", "</ul>", "<br>", "<hr>"):
        assert fragmento in salida, f"falta {fragmento!r}"

def test_colspan_valido_se_conserva_e_invalido_se_descarta():
    assert 'colspan="2"' in limpiar_html('<td colspan="2">x</td>')
    assert "colspan" not in limpiar_html('<td colspan="dos">x</td>')
    assert "colspan" not in limpiar_html('<td colspan="2;color:red">x</td>')

def test_clase_se_limpia():
    """Un nombre de clase no ejecuta nada, pero no debe poder cerrar el atributo."""
    salida = limpiar_html('<p class="page-break alert(1);color:red">x</p>')
    clase = re.search(r'class="([^"]*)"', salida).group(1)
    assert "page-break" in clase
    assert re.fullmatch(r"[A-Za-z0-9_\- ]*", clase), clase
    assert "(" not in clase and ";" not in clase

def test_texto_con_angulos_se_escapa():
    salida = limpiar_html("<p>a &lt; b y 5 &gt; 3</p>")
    assert "&lt;" in salida and "&gt;" in salida
    assert "<p>a" in salida

def test_etiquetas_sin_cerrar_se_cierran():
    salida = limpiar_html("<div><p>texto")
    assert salida.count("<div>") == salida.count("</div>")
    assert salida.count("<p>") == salida.count("</p>")
    assert "texto" in salida

def test_cierre_desordenado_no_rompe():
    salida = limpiar_html("<div><p>a</div>")
    assert "a" in salida
    assert salida.count("<div>") == salida.count("</div>")

def test_entrada_vacia_o_none():
    assert limpiar_html("") == ""
    assert limpiar_html(None) == ""

def test_documento_completo_no_conserva_head_ni_doctype():
    salida = limpiar_html("<!DOCTYPE html><html><head><title>t</title></head>"
                          "<body><h1>Titulo</h1></body></html>")
    assert "doctype" not in salida.lower()
    assert "<head" not in salida.lower()
    assert "<title" not in salida.lower()
    assert "<h1>Titulo</h1>" in salida

def test_html_y_body_se_desenvuelven_no_se_descartan():
    """Regresion: descartar <html> borraba TODO el documento.

    El prompt del Offer Engine pide explicitamente un HTML completo con
    <html><head><style>...</style></head><body>...</body></html>, asi que
    tratar <html> como etiqueta de contenido descartado dejaba la vista
    previa en blanco.
    """
    salida = limpiar_html("<html><body><p>contenido real</p></body></html>")
    assert "contenido real" in salida
    assert "<p>contenido real</p>" in salida
    assert "<html" not in salida.lower()
    assert "<body" not in salida.lower()


# ── Ejecución directa ────────────────────────────────────────────────────

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pruebas = [(n, f) for n, f in sorted(globals().items())
               if n.startswith("test_") and callable(f)]
    fallos = []
    for nombre, fn in pruebas:
        try:
            fn()
            print(f"  ok    {nombre}")
        except AssertionError as e:
            fallos.append((nombre, e))
            print(f"  FALLO {nombre}: {e}")
        except Exception as e:  # noqa: BLE001
            fallos.append((nombre, e))
            print(f"  ERROR {nombre}: {type(e).__name__}: {e}")
    print(f"\n{len(pruebas) - len(fallos)}/{len(pruebas)} tests correctos")
    sys.exit(1 if fallos else 0)
