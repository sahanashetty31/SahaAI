"""
SahaAI CFO – standalone app with UI.
Serves the CFO API under /api and a dashboard UI at /.

Run:  uvicorn main_cfo:app --reload --port 8001
Open: http://127.0.0.1:8001/
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

from cfo_api import app as cfo_app

app = FastAPI(title="SahaAI AI CFO", description="Receipt, statement, fraud, goals & score")

# Mount CFO API under /api (so /api/analyze-receipt, /api/health, etc.)
app.mount("/api", cfo_app)

# Serve CFO dashboard UI at /
_static_cfo = Path(__file__).parent / "static_cfo"
_index = _static_cfo / "index.html"


@app.get("/")
def serve_cfo_ui():
    if _index.is_file():
        return FileResponse(_index)
    return {"message": "CFO UI not found. Add static_cfo/index.html", "api": "/api/docs"}


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)
