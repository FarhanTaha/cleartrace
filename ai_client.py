"""ai_client.py - decides HOW ClearTrace talks to Claude.

Three modes, picked automatically:
  "server"  - CLEARTRACE_SERVER is set: send requests to our Render server,
              which holds the API key. Normal users need no key.
  "local"   - ANTHROPIC_API_KEY is set (e.g. on your own laptop): call Claude directly.
  "offline" - neither: simple built-in rules, so the app still works.
"""
import json
import os
import time
import urllib.error
import urllib.request

# Settings live in the user's home folder, so they survive app updates
# (a packed .exe runs from a temporary folder that is wiped each time).
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".cleartrace")
ENV_PATH = os.path.join(CONFIG_DIR, ".env")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))  # developers
    load_dotenv(ENV_PATH)
except ImportError:
    pass

# Paste your Render URL here once deployed, e.g. "https://cleartrace-api.onrender.com".
# Every downloaded copy then uses it, so users need no API key.
DEFAULT_SERVER = "https://cleartrace-api-pc1k.onrender.com"

ROUTER_MODEL = os.getenv("CLEARTRACE_ROUTER_MODEL", "claude-haiku-5-5")
ADVISOR_MODEL = os.getenv("CLEARTRACE_ADVISOR_MODEL", "claude-opus-5-5")


def server_url():
    return (os.getenv("CLEARTRACE_SERVER") or DEFAULT_SERVER).rstrip("/")


_server_down_until = 0.0   # after a failed call, skip the server for a minute (no repeated waits)


def mode():
    # Your own key wins (you pay), then the ClearTrace server, then offline rules.
    if os.getenv("ANTHROPIC_API_KEY"):
        return "local"
    if server_url() and time.time() >= _server_down_until:
        return "server"
    return "offline"


def _mark_server_down():
    global _server_down_until
    _server_down_until = time.time() + 60




def check_key(key):
    """Return "" if the key works, otherwise a short error message."""
    import anthropic
    try:
        anthropic.Anthropic(api_key=key).models.list(limit=1)  # free, uses no tokens
        return ""
    except anthropic.AuthenticationError:
        return "That key isn't valid. Check you copied all of it."
    except anthropic.PermissionDeniedError:
        return "That key doesn't have permission to use Claude."
    except anthropic.APIConnectionError:
        return "Couldn't reach Anthropic. Check your internet connection."
    except anthropic.APIStatusError as e:
        return f"Anthropic returned an error ({e.status_code})."


def save_key(key):
    """Save the key to ~/.cleartrace/.env on THIS computer only, and use it straight away."""
    global _client
    from dotenv import set_key
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(ENV_PATH):
        open(ENV_PATH, "w").close()
    set_key(ENV_PATH, "ANTHROPIC_API_KEY", key)
    os.environ["ANTHROPIC_API_KEY"] = key
    _client = None


def remove_key():
    global _client
    from dotenv import unset_key
    if os.path.exists(ENV_PATH):
        unset_key(ENV_PATH, "ANTHROPIC_API_KEY")
    os.environ.pop("ANTHROPIC_API_KEY", None)
    _client = None


def warm_up():
    """Wake the Render server as soon as the app opens (the free tier sleeps when idle),
    so it's ready by the time the user asks something."""
    if mode() != "server":
        return
    try:
        urllib.request.urlopen(server_url() + "/", timeout=90).read()
    except Exception:
        _mark_server_down()


def post(endpoint, payload, timeout=45):
    """POST JSON to the ClearTrace server and return its JSON reply."""
    req = urllib.request.Request(
        server_url() + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError):
        _mark_server_down()   # unreachable: use built-in rules for the next minute
        raise


_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


def ask_json(model, system, user_text, schema, max_tokens=2000, effort="low", fallbacks=False):
    """One Claude call that must return JSON matching `schema`.

    Reads only text blocks (thinking blocks are ignored).
    """
    params = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_text}],
        output_config={"effort": effort,
                       "format": {"type": "json_schema", "schema": schema}},
    )
    if fallbacks:
        # If the main model declines (e.g. a safety false positive on a payslip),
        # the API retries on a fallback model inside the same call.
        response = client().beta.messages.create(
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params)
    else:
        response = client().messages.create(**params)
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request")
    text = "".join(b.text for b in response.content if b.type == "text")
    return json.loads(text)
