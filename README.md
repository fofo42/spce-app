# Ecosistema unificado: ICAI + Offer Engine + SPCE

App de Streamlit que encadena cuatro motores de IA sobre la API de Anthropic para
pasar de *inteligencia de cliente* a *producto*, *landing* y *piezas de diseño*,
reutilizando el contexto de cada fase en la siguiente.

```
Paso 0 ICAI  →  Offer Engine  →  SPCE (landing)  →  Design Pack
 (cliente)       (producto)        (página)          (visual)
        └────────── feeds: OFFER_FEED / SPCE_FEED / DESIGN_FEED ──────────┘
```

## Los cinco modos

| Modo | Qué hace |
|---|---|
| **ICAI (Paso 0)** | Modela el sistema de decisión del cliente en 10 secciones (dossier, search, evaluation, decision, message, funnel, lifecycle + 3 feeds) y genera los puentes para el resto de fases. |
| **Modelar producto** | Offer Engine V1.0.1: auditoría de pilares con *quality gates* DQS, workbook imprimible en HTML y roadmap de carpetas. |
| **Modelar landing** | SPCE: brief de página de ventas mobile-first con copy exacto por bloque y auditoría CRO. |
| **Flujo completo** | Primero el producto; si te convence, continúa a la landing sin volver a introducir contexto. |
| **Design Pack** | Prompts listos para Canva, Gamma y Bing, con análisis de referencias de estilo. |

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
```

- `test_sanitize.py` cubre los vectores de bypass del saneador de HTML
  (`<script>`, `onerror`, `javascript:`, `url()` en CSS, SVG, iframes…) y
  comprueba que el contenido legítimo del workbook sobrevive.
- `test_parsing.py` cubre la extracción tolerante de JSON (bloques ```, texto
  alrededor, llaves dentro de cadenas, comillas escapadas).

## Estructura

| Archivo | Responsabilidad |
|---|---|
| `app.py` | Menú, Offer Engine V1.0.1, SPCE, tema y utilidades del workbook. |
| `icai_engine.py` | Paso 0: inteligencia de cliente. |
| `design_pack.py` | Prompts de diseño por plataforma. |
| `sanitize.py` | Saneado del HTML generado por el modelo. |
| `parsing.py` | Extracción de JSON y secciones de las respuestas del modelo. |
| `observability.py` | Cliente de Anthropic compartido y contador de tokens/coste. |

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
- **Un solo usuario por sesión.** No hay autenticación; cualquiera con acceso a
  la URL puede usar la clave configurada en `secrets.toml`.
- **El saneado pierde el CSS del modelo.** El workbook se maqueta con la hoja de
  estilo de impresión de la app (`CSS_IMPRESION`), no con la que emita el
  modelo. Se conservan los estilos en línea permitidos y la clase `.page-break`.
- **`xhtml2pdf` no implementa todo el CSS** (por ejemplo `border-collapse`) y
  puede producir maquetaciones imperfectas sin marcar error.
- **Sin licencia.** El repositorio no incluye archivo `LICENSE`, así que por
  defecto queda como «todos los derechos reservados». Conviene elegir una antes
  de reutilizarlo.

## Siguiente paso natural

La navegación por `st.session_state['modo_seleccionado']` con `st.stop()` a mitad
de script funciona, pero el archivo `app.py` concentra los cinco modos. Migrar a
`st.navigation` + `st.Page` con una carpeta `app_pages/` repartiría cada modo en
su propio archivo y eliminaría los `st.stop()` intermedios.
