"""server/main.py - tiny FastAPI server that holds the Anthropic API key.

The ClearTrace app on each user's laptop sends short file summaries here;
this server asks Claude and sends the answer back. Users never see the key.

Run locally:   uvicorn server.main:app --reload        (from the repo root)
Deploy:        Render, using render.yaml in the repo root
"""
import os
import sys
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import advisor  # noqa: E402
import router   # noqa: E402

MAX_BODY_BYTES = 60 * 1024      # short summaries only, never whole files
RATE_LIMIT = 300                # requests per IP per hour (a whole venue can share one IP)
GLOBAL_LIMIT = 2000             # requests per hour from everyone, protects the $150
RATE_WINDOW = 3600
TOOLS = {"quick_scan", "sensitive", "duplicates", "search"}

app = FastAPI(title="ClearTrace API")
_hits = defaultdict(deque)
_all_hits = deque()


def _client_ip(request: Request):
    fwd = request.headers.get("x-forwarded-for")  # Render sits behind a proxy
    return fwd.split(",")[0].strip() if fwd else request.client.host


@app.middleware("http")
async def limits(request: Request, call_next):
    if request.method == "POST":
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        ip = _client_ip(request)
        now = time.time()
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        while _all_hits and now - _all_hits[0] > RATE_WINDOW:
            _all_hits.popleft()
        if len(q) >= RATE_LIMIT or len(_all_hits) >= GLOBAL_LIMIT:
            return JSONResponse({"detail": "Too many requests, try again later"}, status_code=429)
        q.append(now)
        _all_hits.append(now)
    return await call_next(request)


@app.get("/")
def health():
    return {"ok": True, "service": "ClearTrace API", "key_set": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/route")
async def route(request: Request):
    data = await request.json()
    message = str(data.get("message", ""))[:2000]
    if not message.strip():
        raise HTTPException(400, "message is required")
    try:
        return router.route_with_claude(message)
    except Exception as e:
        print(f"/route error: {e}")
        return router.route_with_rules(message)


@app.post("/explain")
async def explain(request: Request):
    data = await request.json()
    tool = data.get("tool")
    payload = data.get("payload") or {}
    if tool not in TOOLS:
        raise HTTPException(400, "unknown tool")
    for key in ("files", "groups", "matches"):
        if isinstance(payload.get(key), list) and len(payload[key]) > advisor.MAX_ITEMS:
            raise HTTPException(400, "too many files")
    message = str(data.get("message", ""))[:2000]
    try:
        return advisor.explain_with_claude(tool, payload, message)
    except Exception as e:
        print(f"/explain error: {e}")
        raise HTTPException(502, "AI unavailable")  # the app falls back to its own rules
