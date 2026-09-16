"""Smoke test de la app completa con st.testing.v1.AppTest.

Se ejecuta sin navegador ni red y sin llamar a la API de Anthropic: solo
comprueba que la navegación funciona, que las cinco páginas renderizan sin
excepción y que la vista previa del workbook sigue saneada.

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

PAGINAS = [
    "app_pages/inicio.py",
    "app_pages/icai.py",
    "app_pages/producto.py",
    "app_pages/landing.py",
    "app_pages/design.py",
]

WORKBOOK = (
    "<html><head><style>body{color:red}</style></head><body>"
    "<h1>Workbook de prueba</h1>"
    "<script>alert(1)</script>"
    '<img src=x onerror="alert(1)">'
    '<p style="background:url(javascript:alert(1))">Parrafo legitimo</p>'
    "<table><tr><td>&#9744; Checklist</td></tr></table>"
    "</body></html>"
)


def _abrir(pagina=None, **estado):
    """Arranca la app, opcionalmente en una página concreta.

    switch_page necesita una ejecución previa para que st.navigation haya
    registrado las páginas, y no reejecuta por sí solo.
    """
    at = AppTest.from_file(str(APP), default_timeout=120)
    for clave, valor in estado.items():
        at.session_state[clave] = valor
    at.run()
    if pagina:
        at.switch_page(pagina).run()
    return at


def test_arranca_sin_secrets_toml():
    """Sin .streamlit/secrets.toml la app debe arrancar y pedir la clave."""
    at = _abrir()
    assert not at.exception, at.exception
    assert any("ANTHROPIC_API_KEY" in w.value for w in at.warning)


def test_la_navegacion_registra_las_cinco_paginas():
    at = _abrir()
    assert not at.exception, at.exception
    titulos = [t.value for t in at.title]
    assert titulos == ["Inicio"], titulos


def test_todas_las_paginas_renderizan():
    for pagina in PAGINAS:
        at = _abrir(pagina)
        assert not at.exception, f"{pagina}: {at.exception}"


def test_flujo_icai_a_producto_no_revienta():
    """Regresion: entrar en la Fase 1 con el OFFER_FEED presente reventaba."""
    at = _abrir("app_pages/producto.py", icai_offer_feed="feed de prueba")
    assert not at.exception, at.exception


def test_producto_sin_icai_pide_archivo():
    at = _abrir("app_pages/producto.py")
    assert not at.exception, at.exception
    assert any("ICAI" in w.value for w in at.warning)


def test_vista_previa_sanea_el_html_del_modelo():
    at = _abrir("app_pages/producto.py", producto_html=WORKBOOK,
                producto_audit="auditoria", producto_roadmap="roadmap")
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
    at = _abrir("app_pages/producto.py", producto_html=WORKBOOK,
                producto_audit="a", producto_roadmap="r")
    assert not at.exception, at.exception
    assert [d.label for d in at.download_button], "no se ofrece el PDF"


def test_landing_reutiliza_el_workbook_de_la_fase_1():
    """Lo que antes hacia el modo 'Flujo completo', ahora automatico."""
    at = _abrir("app_pages/landing.py", producto_html=WORKBOOK)
    assert not at.exception, at.exception
    etiquetas = [t.label for t in at.toggle]
    assert any("workbook" in e.lower() for e in etiquetas), etiquetas


def test_landing_sin_workbook_pide_texto():
    at = _abrir("app_pages/landing.py")
    assert not at.exception, at.exception
    assert not at.toggle, "no deberia ofrecer reutilizar un workbook inexistente"


def test_design_pack_muestra_prompts_por_plataforma():
    salida = ("=== STYLE ===\n#004466\n"
              "=== CANVA ===\nprompt canva\n"
              "=== GAMMA ===\nprompt gamma\n"
              "=== BING ===\nprompt bing")
    at = _abrir("app_pages/design.py", design_pack=salida)
    assert not at.exception, at.exception
    codigos = [c.value for c in at.code]
    assert "prompt canva" in "\n".join(codigos), codigos


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
