"""Tests del parseo tolerante de respuestas del modelo."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from parsing import extraer_json, extraer_seccion  # noqa: E402

# ── extraer_json ─────────────────────────────────────────────────────────

def test_json_directo():
    assert extraer_json('{"a": 1}') == {"a": 1}

def test_json_con_espacios_alrededor():
    assert extraer_json('  \n {"a": 1} \n ') == {"a": 1}

def test_json_con_texto_antes_y_despues():
    """El modelo incumple a veces "nada de texto antes o despues"."""
    texto = 'Aqui tienes el resultado:\n{"audit": "x", "roadmap": "y"}\nEspero que sirva.'
    assert extraer_json(texto) == {"audit": "x", "roadmap": "y"}

def test_json_en_bloque_de_codigo_json():
    texto = 'Claro:\n```json\n{"a": 1, "b": "dos"}\n```\n'
    assert extraer_json(texto) == {"a": 1, "b": "dos"}

def test_json_en_bloque_de_codigo_sin_etiqueta():
    assert extraer_json('```\n{"a": 1}\n```') == {"a": 1}

def test_llaves_dentro_de_cadenas_no_descuadran():
    """El caso que rompe un recuento ingenuo de llaves."""
    texto = 'antes {"audit": "usa { y } literalmente", "n": 2} despues'
    assert extraer_json(texto) == {"audit": "usa { y } literalmente", "n": 2}

def test_llaves_anidadas():
    texto = 'x {"a": {"b": {"c": 3}}, "d": 4} y'
    assert extraer_json(texto) == {"a": {"b": {"c": 3}}, "d": 4}

def test_comillas_escapadas_dentro_de_cadenas():
    texto = r'{"workbook_html": "<h1>dice \"hola\"</h1>", "n": 1}'
    assert extraer_json(texto) == {"workbook_html": '<h1>dice "hola"</h1>', "n": 1}

def test_html_escapado_como_en_el_prompt_real():
    """El prompt pide HTML completo escapado dentro de una cadena JSON."""
    import json
    original = {"audit": "ok", "workbook_html": '<html><head><style>h1{color:#0af}</style></head>'
                                                 '<body><table><tr><td>a</td></tr></table></body></html>',
                "roadmap": "OFFER/01_CORE"}
    texto = json.dumps(original)
    assert extraer_json(texto) == original

def test_objeto_con_llave_inicial_rota_luego_uno_valido():
    """El primer `{` puede no abrir un JSON valido; hay que seguir buscando."""
    texto = '{ esto no es json } y luego {"a": 1}'
    assert extraer_json(texto) == {"a": 1}

def test_objeto_incompleto_devuelve_none():
    assert extraer_json('{"a": 1, "b": ') is None

def test_no_json_devuelve_none():
    assert extraer_json("solo texto plano, sin nada") is None

def test_lista_json_se_desenvuelve_al_primer_objeto():
    """Licencia deliberada: si el modelo envuelve el objeto en un array.

    El prompt pide un objeto, pero devolver el workbook rescatado es mejor
    que fallar por un envoltorio inesperado.
    """
    assert extraer_json('[{"a": 1}]') == {"a": 1}

def test_lista_de_escalares_devuelve_none():
    assert extraer_json("[1, 2, 3]") is None

def test_entrada_vacia_o_none():
    assert extraer_json("") is None
    assert extraer_json(None) is None

def test_claves_con_acentos_y_simbolos():
    texto = '{"auditoría": "ñ á é", "promesa_de→a": "ok"}'
    assert extraer_json(texto) == {"auditoría": "ñ á é", "promesa_de→a": "ok"}

# ── extraer_seccion ──────────────────────────────────────────────────────

MARCADORES = ["=== STYLE ===", "=== CANVA ===", "=== GAMMA ===", "=== BING ==="]

def test_seccion_basica():
    texto = "=== STYLE ===\npaleta\n=== CANVA ===\nprompt canva\n=== BING ===\nbing"
    assert extraer_seccion(texto, "=== CANVA ===", MARCADORES) == "prompt canva"

def test_seccion_ultima_no_se_corta():
    texto = "=== STYLE ===\na\n=== BING ===\nprompt bing"
    assert extraer_seccion(texto, "=== BING ===", MARCADORES) == "prompt bing"

def test_seccion_inexistente_devuelve_vacio():
    assert extraer_seccion("=== STYLE ===\nx", "=== CANVA ===", MARCADORES) == ""

def test_seccion_recorta_espacios():
    assert extraer_seccion("=== STYLE ===\n\n  hola  \n\n", "=== STYLE ===", MARCADORES) == "hola"

def test_seccion_texto_vacio_o_none():
    assert extraer_seccion("", "=== STYLE ===", MARCADORES) == ""
    assert extraer_seccion(None, "=== STYLE ===", MARCADORES) == ""


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
            fallos.append(nombre)
            print(f"  FALLO {nombre}: {e}")
        except Exception as e:  # noqa: BLE001
            fallos.append(nombre)
            print(f"  ERROR {nombre}: {type(e).__name__}: {e}")
    print(f"\n{len(pruebas) - len(fallos)}/{len(pruebas)} tests correctos")
    sys.exit(1 if fallos else 0)
