"""
Local HTTP API wrapper for the Canopy SFO Codex Agent workflow.

This server does not store API keys. Set keys as environment variables before
starting the server, then call POST /api/canopy-sfo/runs with task parameters.

Example:
  python canopy_sfo_agent_api.py --host 127.0.0.1 --port 8787
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional


WORKSPACE = Path(__file__).resolve().parent
PIPELINE = WORKSPACE / "canopy_sfo_pipeline.py"
RUN_ROOT = WORKSPACE / "output" / "api_runs"

RUNS: Dict[str, Dict[str, Any]] = {}
RUN_LOCK = threading.Lock()


DEFAULT_REQUEST_CONFIG: Dict[str, Any] = {
    "stage": "discover",
    "task": {
        "target_count": 30,
        "candidate_limit": 40,
        "regions": ["Hong Kong", "Taiwan", "Mainland China", "Thailand", "Malaysia"],
        "target_titles": [
            "Chief Investment Officer",
            "CIO",
            "Family Office Director",
            "Head of Family Office",
            "Principal",
            "Managing Partner",
            "Investment Director",
            "Family Principal",
        ],
        "min_aum_usd": 200000000,
        "require_email": True,
        "min_email_confidence": 70,
    },
    "resources": {
        "apollo": True,
        "serper": True,
        "brave": True,
        "hunter": True,
        "gemini_scoring": True,
        "gemini_outreach": True,
    },
    "human_review": {
        "after_candidate_discovery": True,
        "after_research_enrichment": True,
        "before_outreach_generation": True,
    },
    "scoring": {
        "a_level_min": 30,
        "b_level_min": 20,
        "weights": {
            "match_score": 0.35,
            "reach_score": 0.25,
            "budget_score": 0.25,
            "cycle_score": 0.15,
        },
    },
    "rate_limit": {"request_delay_seconds": 1.2},
}


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def safe_artifacts(run_dir: Path) -> Dict[str, str]:
    if not run_dir.exists():
        return {}
    artifacts: Dict[str, str] = {}
    for path in run_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md", ".xlsx"}:
            artifacts[path.name] = str(path)
    return artifacts


def start_pipeline_run(body: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_REQUEST_CONFIG))
    deep_merge(merged, body.get("config") or {})
    stage = body.get("stage") or merged.get("stage") or "discover"
    if stage not in {"discover", "research", "outreach", "full"}:
        raise ValueError("stage must be one of: discover, research, outreach, full")

    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config_path = run_dir / "task_config.json"
    config_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    review_input = body.get("review_input") or ""
    args = [
        sys.executable,
        str(PIPELINE),
        "--stage",
        stage,
        "--config",
        str(config_path),
        "--out-dir",
        str(run_dir),
    ]
    if review_input:
        args.extend(["--review-input", str(review_input)])

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    log_path = run_dir / "run.log"
    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        args,
        cwd=str(WORKSPACE),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
    )

    run_record = {
        "run_id": run_id,
        "stage": stage,
        "status": "running",
        "pid": process.pid,
        "return_code": None,
        "run_dir": str(run_dir),
        "config_path": str(config_path),
        "log_path": str(log_path),
        "started_at": time.time(),
        "_process": process,
        "_log_file": log_file,
    }
    with RUN_LOCK:
        RUNS[run_id] = run_record
    return public_run_record(run_record)


def refresh_run(run_id: str) -> Optional[Dict[str, Any]]:
    with RUN_LOCK:
        run = RUNS.get(run_id)
    if not run:
        return None
    process: subprocess.Popen[str] = run["_process"]
    rc = process.poll()
    if rc is not None and run["status"] == "running":
        run["return_code"] = rc
        run["status"] = "succeeded" if rc == 0 else "failed"
        run["finished_at"] = time.time()
        try:
            run["_log_file"].close()
        except Exception:
            pass
    return public_run_record(run)


def public_run_record(run: Dict[str, Any]) -> Dict[str, Any]:
    run_dir = Path(run["run_dir"])
    return {
        "run_id": run["run_id"],
        "stage": run["stage"],
        "status": run["status"],
        "pid": run["pid"],
        "return_code": run["return_code"],
        "run_dir": run["run_dir"],
        "config_path": run["config_path"],
        "log_path": run["log_path"],
        "artifacts": safe_artifacts(run_dir),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "CanopySFOAgentAPI/1.0"

    def do_GET(self) -> None:
        if self.path == "/health":
            json_response(self, HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/api/canopy-sfo/runs":
            with RUN_LOCK:
                run_ids = list(RUNS)
            payload = {"runs": [refresh_run(run_id) for run_id in run_ids]}
            json_response(self, HTTPStatus.OK, payload)
            return
        if self.path.startswith("/api/canopy-sfo/runs/"):
            run_id = self.path.rsplit("/", 1)[-1]
            run = refresh_run(run_id)
            if not run:
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "run not found"})
                return
            json_response(self, HTTPStatus.OK, run)
            return
        json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/api/canopy-sfo/runs":
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            body = read_json(self)
            run = start_pipeline_run(body)
            json_response(self, HTTPStatus.ACCEPTED, run)
        except Exception as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Canopy SFO Agent API listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
