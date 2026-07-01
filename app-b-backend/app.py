"""App B — Databricks backend.

Talks to Databricks resources using the app's service principal (auto-injected
DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET). Exposes JSON endpoints that
App A calls server-to-server.
"""
import os
import base64
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks import sql

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app-b")

WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")
SECRET_SCOPE = os.environ.get("DEMO_SECRET_SCOPE", "dual-app-demo")
SECRET_KEY = os.environ.get("DEMO_SECRET_KEY", "greeting")

app = FastAPI(title="App B — Databricks backend")

# Service-principal auth is auto-configured from injected env vars.
_cfg = Config()
_w = WorkspaceClient(config=_cfg)


@app.get("/health")
def health():
    return {"status": "ok", "app": os.environ.get("DATABRICKS_APP_NAME", "app-b")}


@app.get("/api/secret")
def get_secret():
    """Read a secret via the SP. Requires READ on the secret scope."""
    try:
        resp = _w.secrets.get_secret(scope=SECRET_SCOPE, key=SECRET_KEY)
        value = base64.b64decode(resp.value).decode("utf-8")
        # Do not return the raw secret in a real app; masked here for the demo.
        return {"scope": SECRET_SCOPE, "key": SECRET_KEY, "value": value}
    except Exception as e:  # noqa: BLE001
        log.exception("secret read failed")
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    sql: str = "SELECT current_catalog() AS catalog, current_date() AS today"


@app.post("/api/query")
def run_query(req: QueryRequest):
    """Run a SQL statement on the configured warehouse."""
    if not WAREHOUSE_ID:
        raise HTTPException(status_code=500, detail="DATABRICKS_WAREHOUSE_ID not set")
    try:
        with sql.connect(
            server_hostname=_cfg.host.replace("https://", ""),
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            credentials_provider=lambda: _cfg.authenticate,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(req.sql)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = [dict(zip(cols, r)) for r in cur.fetchmany(50)]
        return {"columns": cols, "rows": rows}
    except Exception as e:  # noqa: BLE001
        log.exception("query failed")
        raise HTTPException(status_code=500, detail=str(e))


class GenieRequest(BaseModel):
    question: str = "How many rows are in the dataset?"


@app.post("/api/genie")
def ask_genie(req: GenieRequest):
    """Ask a natural-language question against the configured Genie space."""
    if not GENIE_SPACE_ID:
        raise HTTPException(status_code=500, detail="GENIE_SPACE_ID not set")
    try:
        msg = _w.genie.start_conversation_and_wait(GENIE_SPACE_ID, req.question)
        answer = None
        query_text = None
        for att in (msg.attachments or []):
            if att.text and att.text.content:
                answer = att.text.content
            if att.query and att.query.query:
                query_text = att.query.query
        return {
            "question": req.question,
            "answer": answer,
            "generated_sql": query_text,
            "conversation_id": msg.conversation_id,
        }
    except Exception as e:  # noqa: BLE001
        log.exception("genie failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
