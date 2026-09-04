from __future__ import annotations

import asyncio
import csv
import io
import json
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from threading import Timer
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tracefox.ollama_client import analyze_results, list_models
from tracefox.scanner import ScanConfig, load_sites, normalize_username, scan_username, summarize_counts

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
HISTORY = DATA / "history"
CACHE = DATA / "wmn-data.json"
STATIC = ROOT / "static"
HISTORY.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TraceFox", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

jobs: dict[str, dict[str, Any]] = {}


class ScanRequest(BaseModel):
    username: str
    concurrency: int = Field(default=30, ge=1, le=80)
    max_sites: int | None = Field(default=None, ge=1, le=2000)
    refresh_sites: bool = False


class AnalyzeRequest(BaseModel):
    job_id: str
    model: str


def persist(job: dict[str, Any]) -> None:
    safe = {k: v for k, v in job.items() if k != "task"}
    (HISTORY / f"{job['id']}.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")


async def run_job(job_id: str, request: ScanRequest) -> None:
    job = jobs[job_id]
    try:
        sites, source = await load_sites(CACHE, refresh=request.refresh_sites)
        job["site_source"] = source
        job["total"] = min(len(sites), request.max_sites) if request.max_sites else len(sites)
        job["state"] = "running"

        async def progress(done: int, total: int, result: dict[str, Any]) -> None:
            job["done"] = done
            job["total"] = total
            if result.get("status") == "found":
                job.setdefault("live_found", []).append(result)

        results = await scan_username(
            request.username,
            sites,
            ScanConfig(concurrency=request.concurrency, max_sites=request.max_sites),
            progress,
        )
        job["results"] = results
        job["counts"] = summarize_counts(results)
        job["state"] = "complete"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        persist(job)
    except Exception as exc:
        job["state"] = "failed"
        job["error"] = str(exc)
        persist(job)


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/models")
async def models() -> dict[str, Any]:
    names = await list_models()
    return {"models": names, "ollama_online": bool(names)}


@app.post("/api/scan")
async def start_scan(request: ScanRequest) -> dict[str, Any]:
    try:
        username = normalize_username(request.username)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    request.username = username
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "username": username,
        "state": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "done": 0,
        "total": 0,
        "live_found": [],
        "counts": {},
        "results": [],
        "analysis": None,
    }
    jobs[job_id] = job
    job["task"] = asyncio.create_task(run_job(job_id, request))
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str) -> JSONResponse:
    job = jobs.get(job_id)
    if not job:
        path = HISTORY / f"{job_id}.json"
        if not path.exists():
            raise HTTPException(404, "Unknown job")
        job = json.loads(path.read_text(encoding="utf-8"))
    clean = {k: v for k, v in job.items() if k != "task"}
    return JSONResponse(clean)


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    job = jobs.get(request.job_id)
    if not job:
        path = HISTORY / f"{request.job_id}.json"
        if not path.exists():
            raise HTTPException(404, "Unknown job")
        job = json.loads(path.read_text(encoding="utf-8"))
        jobs[request.job_id] = job
    if job.get("state") != "complete":
        raise HTTPException(409, "Scan is not complete")
    if not request.model.strip():
        raise HTTPException(400, "Choose an installed Ollama model")
    try:
        analysis = await analyze_results(job["username"], request.model, job.get("results", []))
    except Exception as exc:
        raise HTTPException(502, f"Ollama analysis failed: {exc}") from exc
    job["analysis"] = analysis
    job["analysis_model"] = request.model
    persist(job)
    return analysis


@app.get("/api/export/{job_id}.json")
async def export_json(job_id: str) -> JSONResponse:
    path = HISTORY / f"{job_id}.json"
    if jobs.get(job_id):
        persist(jobs[job_id])
    if not path.exists():
        raise HTTPException(404, "Unknown job")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/export/{job_id}.csv")
async def export_csv(job_id: str) -> PlainTextResponse:
    job = jobs.get(job_id)
    if not job:
        path = HISTORY / f"{job_id}.json"
        if not path.exists():
            raise HTTPException(404, "Unknown job")
        job = json.loads(path.read_text(encoding="utf-8"))
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["site", "category", "status", "http_status", "profile_url", "title", "description"])
    for result in job.get("results", []):
        meta = result.get("metadata") or {}
        writer.writerow([
            result.get("site"), result.get("category"), result.get("status"),
            result.get("http_status"), result.get("profile_url"),
            meta.get("title"), meta.get("description"),
        ])
    return PlainTextResponse(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="tracefox_{job.get("username", "scan")}.csv"'})


def open_browser() -> None:
    webbrowser.open("http://127.0.0.1:8765")


if __name__ == "__main__":
    import uvicorn

    Timer(1.1, open_browser).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8765, reload=False)
