# Ecosistema unificado: ICAI + Offer Engine + SPCE

App de Streamlit que encadena cuatro motores de IA sobre la API de Anthropic para
pasar de *inteligencia de cliente* a *producto*, *landing* y *piezas de diseño*,
reutilizando el contexto de cada fase en la siguiente.

```
Paso 0 ICAI  →  Offer Engine  →  SPCE (landing)  →  Design Pack
 (cliente)       (producto)        (página)          (visual)
        └────────── feeds: OFFER_FEED / SPCE_FEED / DESIGN_FEED ──────────┘
```

## Las cinco páginas

La navegación es la barra superior (`st.navigation` + `app_pages/`). Cada fase
escribe sus resultados en `st.session_state`, así que la siguiente los encuentra
ya cargados: no hay que volver a pegar contexto.

| Página | Qué hace |
|---|---|
| **Inicio** | Panel de estado: qué artefactos existen ya en la sesión y qué toca después. |
| **Paso 0 · ICAI** | Modela el sistema de decisión del cliente en 10 secciones (dossier, search, evaluation, decision, message, funnel, lifecycle + 3 feeds) y genera los puentes para el resto. |
| **Fase 1 · Producto** | Offer Engine V1.0.1: auditoría de pilares con *quality gates* DQS, workbook imprimible en PDF y roadmap de carpetas. |
| **Fase 2 · Landing** | SPCE: brief de página de ventas mobile-first con copy exacto por bloque y auditoría CRO. Reutiliza el workbook de la Fase 1 si existe. |
| **Design Pack** | Prompts listos para Canva, Gamma y Bing, con análisis de referencias de estilo. |

> El antiguo modo «Flujo completo» ya no existe como opción: era un parche para
> arrastrar el producto hasta la landing. Ahora la Fase 2 lee el workbook de la
> sesión por sí sola, y la página de producto ofrece un botón para saltar a ella.

## Requisitos

- Python 3.11 o superior
- Una API Key de Anthropic ([console.anthropic.com](https://console.anthropic.com))

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configurar la API Key

Hay dos formas y **ninguna implica escribir la clave en el código**:

1. **Recomendada — `secrets.toml`.** Copia la plantilla y pon tu clave:

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Ese archivo está en `.gitignore`, así que no se sube nunca. En Streamlit
   Community Cloud, defínela en *Settings → Secrets* en lugar de subir el archivo.

2. **Campo en la barra lateral.** Si no existe `secrets.toml`, la app arranca
   igual y te pide la clave; solo vive en memoria durante la sesión.

## Ejecutar

```bash
streamlit run app.py
```

En Codespaces, el `.devcontainer` arranca la app automáticamente en el puerto 8501.

## Tests

No necesitan pytest ni red:

```bash
python tests/test_sanitize.py
python tests/test_parsing.py
python tests/test_app_smoke.py
```

- `test_sanitize.py` cubre los vectores de bypass del saneador de HTML
  (`<script>`, `onerror`, `javascript:`, `url()` en CSS, SVG, iframes…) y
  comprueba que el contenido legítimo del workbook sobrevive.
- `test_parsing.py` cubre la extracción tolerante de JSON (bloques ```, texto
  alrededor, llaves dentro de cadenas, comillas escapadas).
- `test_app_smoke.py` arranca la app con `st.testing.v1.AppTest`, recorre las
  cinco páginas por `switch_page` y verifica el saneado y la descarga del PDF.

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `app.py` | Punto de entrada: tema, barra lateral, estado compartido y `st.navigation`. |
| `app_pages/inicio.py` | Panel de estado y accesos al flujo. |
| `app_pages/icai.py` | Paso 0: inteligencia de cliente. |
| `app_pages/producto.py` | Fase 1: Offer Engine V1.0.1 y workbook. |
| `app_pages/landing.py` | Fase 2: brief de landing (SPCE). |
| `app_pages/design.py` | Design Pack. |
| `prompts.py` | Los cuatro prompts de sistema y la forma esperada de cada salida. |
| `archivos.py` | Lectura de PDF/imágenes subidos → bloques de contenido para la API. |
| `workbook.py` | Vista previa saneada y conversión a PDF del workbook. |
| `sanitize.py` | Saneado del HTML generado por el modelo. |
| `parsing.py` | Extracción de JSON y secciones de las respuestas del modelo. |
| `observability.py` | Cliente de Anthropic compartido y contador de tokens/coste. |

Las páginas son *scripts directos* (sin función contenedora ni
`if __name__ == "__main__"`), que es como Streamlit espera que se escriban. El
título de cada página lo pinta `app.py` desde `st.Page`, así que las páginas no
llaman a `st.title`.

## Notas de seguridad

- **El HTML que devuelve el modelo se sanea antes de renderizarse.** Procede de
  una cadena LLM → documento subido por el usuario → prompt → HTML, así que es
  entrada no confiable. `sanitize.py` aplica una *allowlist* de etiquetas,
  atributos y propiedades CSS.
- **El PDF también se genera desde el HTML saneado.** `xhtml2pdf` resuelve las
  referencias `url(...)` del CSS y puede llegar a descargar recursos remotos
  desde el servidor, además de fallar con entradas hostiles.
- **La API Key nunca se escribe en disco** salvo en `.streamlit/secrets.toml`,
  que está ignorado por Git.
- El límite de subida está en 50 MB (`.streamlit/config.toml`). Los archivos se
  leen enteros en memoria y se codifican a base64, así que un límite alto es un
  vector de agotamiento de memoria.

## Limitaciones conocidas

- **Estado en memoria.** Todo vive en `st.session_state`: al cerrar la pestaña o
  reiniciar el servidor se pierde el trabajo. No hay persistencia.
- **Los campos de formulario se vacían al cambiar de página.** Los *resultados*
  (dossier, workbook, brief) persisten porque son claves de sesión, pero los
  widgets de una página pierden su valor al salir de ella. Se puede fijar con
  `persist_state="session"` si molesta para algún campo concreto.
- **Un solo usuario por sesión.** No hay autenticación; cualquiera con acceso a
  la URL puede usar la clave configurada en `secrets.toml`.
- **El saneado pierde el CSS del modelo.** El workbook se maqueta con la hoja de
  estilo de impresión de la app (`CSS_IMPRESION`), no con la que emita el
  modelo. Se conservan los estilos en línea permitidos y la clase `.page-break`.
- **`xhtml2pdf` no implementa todo el CSS** (por ejemplo `border-collapse`) y
  puede producir maquetaciones imperfectas sin marcar error.

## Siguiente paso natural

- **Persistencia.** Todo el trabajo vive en `st.session_state`; exportar el
  dossier, el workbook y el brief a disco (o a un almacén) evitaría perderlo al
  cerrar la pestaña.
- **Autenticación.** `st.login` con OIDC permitiría que cada usuario traiga su
  propia clave en lugar de compartir la de `secrets.toml`.
- **Tema en `config.toml`.** El tema ya está declarado ahí (`[theme] base =
  "dark"`). Lo que queda en `app.py` es CSS para lo que los tokens no expresan:
  el degradado de fondo y la maquetación de la vista previa del workbook.

## Licencia

MIT — ver [LICENSE](LICENSE).
