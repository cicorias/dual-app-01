"""App A — static site + server-side proxy to App B.

The browser only talks to App A (same origin, no CORS). App A's backend forwards
/api/* requests to App B, authenticating with App A's service principal OAuth
token. Direct browser -> App B calls are blocked (302 to login), which is why
this proxy exists.
"""
import os
import logging

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from databricks.sdk import WorkspaceClient

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app-a")

APP_B_URL = os.environ.get("APP_B_URL", "").rstrip("/")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="App A — frontend + proxy")

# Service-principal client for minting tokens to call App B.
_w = WorkspaceClient()


def _b_headers() -> dict:
    """OAuth headers for the app's service principal (accepted by App B)."""
    return _w.config.authenticate()


@app.get("/healthz")
def healthz():
    return {"status": "ok", "app_b_url": APP_B_URL or None}


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):
    """Forward /api/* to App B server-side using the SP token."""
    if not APP_B_URL:
        raise HTTPException(status_code=500, detail="APP_B_URL not configured")
    url = f"{APP_B_URL}/api/{path}"
    body = await request.body()
    headers = _b_headers()
    if request.headers.get("content-type"):
        headers["content-type"] = request.headers["content-type"]
    try:
        async with httpx.AsyncClient(timeout=110) as client:
            resp = await client.request(
                request.method, url, content=body, headers=headers,
                params=dict(request.query_params),
            )
    except httpx.HTTPError as e:
        log.exception("proxy to App B failed")
        raise HTTPException(status_code=502, detail=f"App B unreachable: {e}")
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        return JSONResponse(status_code=resp.status_code, content=resp.json())
    return JSONResponse(
        status_code=resp.status_code,
        content={"status_code": resp.status_code, "body": resp.text[:2000]},
    )


# Static site is mounted last so /api and /healthz take precedence.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
