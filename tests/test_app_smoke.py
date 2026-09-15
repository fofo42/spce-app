"""Smoke test de la app completa con st.testing.v1.AppTest.

Se ejecuta sin navegador ni red y sin llamar a la API de Anthropic: solo
comprueba que la app arranca, que los cinco modos renderizan sin excepción y
que la vista previa del workbook sigue saneada.

    python tests/test_app_smoke.py
    pytest tests/
"""

import os
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP = RAIZ / "app.py"

os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ))

from streamlit.testing.v1 import AppTest  # noqa: E402

WORKBOOK = (
    "<html><head><style>body{color:red}</style></head><body>"
    "<h1>Workbook de prueba</h1>"
    "<script>alert(1)</script>"
    '<img src=x onerror="alert(1)">'
    '<p style="background:url(javascript:alert(1))">Parrafo legitimo</p>'
    "<table><tr><td>&#9744; Checklist</td></tr></table>"
    "</body></html>"
)

MODOS = [None, "icai", "producto", "landing", "completo", "design"]


def _app(**estado):
    at = AppTest.from_file(str(APP), default_timeout=120)
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    return at


def test_arranca_sin_secrets_toml():
    """Sin .streamlit/secrets.toml la app debe arrancar y pedir la clave."""
    at = _app()
    assert not at.exception, at.exception
    assert any("ANTHROPIC_API_KEY" in w.value for w in at.warning)


def test_los_cinco_modos_renderizan():
    for modo in MODOS:
        at = _app(modo_seleccionado=modo)
        assert not at.exception, f"modo {modo!r}: {at.exception}"


def test_flujo_icai_a_producto_no_revienta():
    """Regresion: 'Crear desde cero' in None lanzaba TypeError.

    Con el OFFER_FEED presente y modo_modelado sin elegir (None), la Fase 1
    caia con TypeError porque dict.get(clave, '') devuelve None cuando la
    clave existe con ese valor.
    """
    at = _app(modo_seleccionado="producto", icai_offer_feed="feed de prueba")
    assert not at.exception, at.exception


def test_vista_previa_sanea_el_html_del_modelo():
    for modo in ("producto", "completo"):
        at = _app(modo_seleccionado=modo, producto_html=WORKBOOK,
                  producto_audit="auditoria", producto_roadmap="roadmap",
                  modo_modelado="Remodelar producto existente")
        assert not at.exception, at.exception

        preview = [m.value for m in at.markdown
                   if m.value.startswith('<div class="workbook-preview">')]
        assert preview, "no se renderizo el bloque .workbook-preview"
        cuerpo = "\n".join(preview)

        for prohibido in ("<script", "onerror", "javascript:", "alert(", "<style", "<img"):
            assert prohibido not in cuerpo, f"{prohibido!r} sobrevivio al saneado"
        # ...y el contenido legitimo sigue ahi.
        assert "<table>" in cuerpo
        assert "☐" in cuerpo
        assert "Parrafo legitimo" in cuerpo


def test_se_ofrece_la_descarga_del_pdf():
    at = _app(modo_seleccionado="producto", producto_html=WORKBOOK,
              producto_audit="a", producto_roadmap="r",
              modo_modelado="Remodelar producto existente")
    assert not at.exception, at.exception
    assert [d.label for d in at.download_button], "no se ofrece el PDF"


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
    sys.stdout.flush()
    # os._exit evita el cleanup de tempfile, que en entornos con el directorio
    # temporal restringido falla al borrar y ensucia la salida.
    os._exit(1 if fallos else 0)
