import time
import streamlit as st

# Precios públicos por millón de tokens: (input, output, cache_write, cache_read)
# Fuente: anthropic.com/pricing — ajústalos aquí si cambian.
PRICING = {
    "claude-sonnet-4-5":          (3.0, 15.0, 3.75, 0.30),
    "claude-sonnet-4-5-20250929": (3.0, 15.0, 3.75, 0.30),
    "claude-haiku-4-5":           (1.0,  5.0, 1.25, 0.10),
    "claude-opus-4-5":            (5.0, 25.0, 6.25, 0.50),
}
DEFAULT_PRICE = (3.0, 15.0, 3.75, 0.30)

def _init():
    if "obs" not in st.session_state:
        st.session_state.obs = {"calls": 0, "in": 0, "out": 0,
                                "cost": 0.0, "secs": 0.0, "last": None}

def record(model_id, usage, elapsed):
    _init()
    g = lambda n: (getattr(usage, n, 0) or 0)
    inp, out = g("input_tokens"), g("output_tokens")
    cw, cr = g("cache_creation_input_tokens"), g("cache_read_input_tokens")
    p_in, p_out, p_cw, p_cr = PRICING.get(model_id, DEFAULT_PRICE)
    cost = (inp * p_in + out * p_out + cw * p_cw + cr * p_cr) / 1_000_000
    o = st.session_state.obs
    o["calls"] += 1
    o["in"] += inp + cw + cr
    o["out"] += out
    o["cost"] += cost
    o["secs"] += elapsed
    o["last"] = (elapsed, inp, out, cost, model_id)
    return inp, out, cost

def last_line():
    _init()
    o = st.session_state.obs
    if not o["last"]:
        return ""
    el, inp, out, cost, model = o["last"]
    return (f"⏱️ {el:.1f} s · 🔢 {inp + out:,} tokens (↑{inp:,} entrada / ↓{out:,} salida) · "
            f" ≈ ${cost:.4f} · modelo: {model}")

class _Messages:
    def __init__(self, messages, model_id):
        self._m, self._model = messages, model_id
    def create(self, **kwargs):
        t0 = time.perf_counter()
        resp = self._m.create(**kwargs)
        record(self._model, getattr(resp, "usage", None), time.perf_counter() - t0)
        return resp
    def stream(self, **kwargs):
        return _StreamWrapper(self._m.stream(**kwargs), self._model)

class _StreamWrapper:
    """Envuelve el 'stream' de Anthropic para poder seguir contando
    coste/tokens (igual que con .create) también en modo 'en vivo'."""
    def __init__(self, stream_ctx, model_id):
        self._ctx = stream_ctx
        self._model = model_id
        self._t0 = None
        self._stream = None
    def __enter__(self):
        self._t0 = time.perf_counter()
        self._stream = self._ctx.__enter__()
        return self
    def __exit__(self, *args):
        return self._ctx.__exit__(*args)
    @property
    def text_stream(self):
        return self._stream.text_stream
    def get_final_message(self):
        msg = self._stream.get_final_message()
        record(self._model, getattr(msg, "usage", None), time.perf_counter() - self._t0)
        return msg

class _ClientProxy:
    def __init__(self, client, model_id):
        self._c = client
        self.messages = _Messages(client.messages, model_id)

def wrap_client(client, model_id):
    return _ClientProxy(client, model_id)


@st.cache_resource(show_spinner=False)
def cliente(api_key):
    """Cliente de Anthropic compartido.

    Antes se construía uno nuevo en cada llamada, lo que implica un pool de
    conexiones y un handshake TLS nuevos cada vez. cache_resource lo reutiliza
    entre reruns. La clave forma parte de la clave de caché, así que dos
    usuarios con claves distintas nunca comparten cliente.
    """
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def cliente_observado(api_key, model_id):
    """Cliente listo para usar, con el contador de tokens y coste conectado."""
    return wrap_client(cliente(api_key), model_id)


def render_sidebar():
    _init()
    o = st.session_state.obs
    st.markdown("---")
    st.subheader("Observabilidad", icon=":material/monitoring:")
    c1, c2 = st.columns(2)
    c1.metric("Operaciones", o["calls"])
    c2.metric("Tiempo total", f"{o['secs']:.0f} s")
    c1.metric("Tokens", f"{o['in'] + o['out']:,}")
    c2.metric("Coste est.", f"${o['cost']:.4f}")
    if st.button("Reiniciar contadores", width="stretch", icon=":material/restart_alt:"):
        st.session_state.obs = {"calls": 0, "in": 0, "out": 0,
                                "cost": 0.0, "secs": 0.0, "last": None}
        st.rerun()
