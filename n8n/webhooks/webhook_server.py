"""
webhook_server.py
-----------------
n8n ↔ pytest bridge with proper lifecycle handling
"""

import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request, abort
from flask_cors import CORS

# ── Project root ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.reporter import read_results, summarise, clear_results
from utils.logger import get_logger

log = get_logger("webhook_server")

# ── App setup ────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

_SERVER_START = datetime.now(timezone.utc)
_ACTIVE_RUNS: Dict[str, Dict] = {}
_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "stb-n8n-secret-changeme")


# ── AUTH ─────────────────────────────────────────────────────
def _check_auth():
    if not _WEBHOOK_SECRET:
        return
    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != _WEBHOOK_SECRET:
        abort(401, description="Invalid webhook secret")


# ── HEALTH ───────────────────────────────────────────────────
@app.get("/webhook/health")
def health():
    uptime = (datetime.now(timezone.utc) - _SERVER_START).total_seconds()
    return jsonify({
        "status": "ok",
        "uptime": uptime,
        "active_runs": len(_ACTIVE_RUNS)
    })


# ============================================================
# 🔥 RUN TESTS (SYNC) — FIXED
# ============================================================

@app.post("/webhook/run-tests")
def run_tests():
    _check_auth()
    body = request.get_json(silent=True) or {}

    # 🔥 CRITICAL FIX: RESET RESULTS
    clear_results()
    log.info("Results cleared before test run")

    run_id, cmd = _build_pytest_cmd(body)

    log.info("[%s] Running: %s", run_id, " ".join(cmd))

    _ACTIVE_RUNS[run_id] = {
        "status": "running",
        "started": datetime.now(timezone.utc).isoformat(),
        "command": cmd
    }

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=600
        )

        results = read_results()
        summary = summarise(results)

        _ACTIVE_RUNS[run_id]["status"] = "done"
        _ACTIVE_RUNS[run_id]["exit_code"] = proc.returncode

        return jsonify({
            "run_id": run_id,
            "summary": summary,
            "results": results,
            "exit_code": proc.returncode
        })

    except Exception as e:
        _ACTIVE_RUNS[run_id]["status"] = "error"
        return jsonify({"error": str(e)}), 500


# ============================================================
# 🔥 RUN TESTS (ASYNC) — FIXED
# ============================================================

@app.post("/webhook/run-tests-async")
def run_tests_async():
    _check_auth()
    body = request.get_json(silent=True) or {}

    # 🔥 CRITICAL FIX
    clear_results()

    run_id, cmd = _build_pytest_cmd(body)

    _ACTIVE_RUNS[run_id] = {
        "status": "queued",
        "started": datetime.now(timezone.utc).isoformat(),
        "command": cmd
    }

    def _run():
        _ACTIVE_RUNS[run_id]["status"] = "running"
        try:
            proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT))
            proc.wait(timeout=600)

            _ACTIVE_RUNS[run_id]["status"] = "done"
            _ACTIVE_RUNS[run_id]["exit_code"] = proc.returncode

        except Exception as e:
            _ACTIVE_RUNS[run_id]["status"] = "error"
            _ACTIVE_RUNS[run_id]["error"] = str(e)

    threading.Thread(target=_run, daemon=True).start()

    return jsonify({"run_id": run_id, "status": "started"})


# ── STATUS ───────────────────────────────────────────────────
@app.get("/webhook/run-status/<run_id>")
def run_status(run_id):
    return jsonify(_ACTIVE_RUNS.get(run_id, {"error": "not found"}))


# ── RESULTS ──────────────────────────────────────────────────
@app.get("/webhook/results")
def get_results():
    return jsonify(read_results())


# ── SUMMARY ──────────────────────────────────────────────────
@app.get("/webhook/summary")
def get_summary():
    results = read_results()
    summary = summarise(results)

    summary["has_failures"] = summary["failed"] > 0
    summary["timestamp"] = datetime.now(timezone.utc).isoformat()

    return jsonify(summary)


# ── CLEAR RESULTS ────────────────────────────────────────────
@app.post("/webhook/clear-results")
def clear():
    clear_results()
    return jsonify({"status": "cleared"})


# ── DEVICE STATUS ────────────────────────────────────────────
@app.get("/webhook/device-status")
def device_status():
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().splitlines()

        devices = [
            {"id": l.split()[0], "state": l.split()[1]}
            for l in lines[1:] if "device" in l
        ]

        return jsonify({
            "devices": devices,
            "count": len(devices)
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# 🔥 BUILD PYTEST COMMAND (FIXED)
# ============================================================

def _build_pytest_cmd(body: Dict[str, Any]):
    import uuid

    run_id = str(uuid.uuid4())[:8]

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v"
    ]

    # Marker
    if body.get("markers"):
        cmd += ["-m", body["markers"]]

    # Parallel
    if body.get("workers"):
        cmd += ["-n", str(body["workers"])]

    # Reruns
    if body.get("reruns"):
        cmd += [f"--reruns={body['reruns']}"]

    # 🔥 FIXED ARG NAME
    if body.get("device_ip"):
        cmd += [f"--device_ip={body['device_ip']}"]

    return run_id, cmd


# ── MAIN ─────────────────────────────────────────────────────
if __name__ == "__main__":
    port = 5050
    log.info("Starting webhook server on port %d", port)
    app.run(host="0.0.0.0", port=port)