#!/usr/bin/env python3
"""ADMC Reporting Agent — Web Application."""

import os
import sys
import json
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

# Ensure the package root is on sys.path so internal imports work
# whether you run `python app.py` or `python -m admc_report_agent.app`
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from flask import Flask, render_template, request, jsonify, send_file, session
from dotenv import load_dotenv

# Load .env from multiple possible locations
_ENV_LOCATIONS = [
    os.path.join(_THIS_DIR, ".env"),
    os.path.join(_THIS_DIR, "env.txt"),
    os.path.join(_THIS_DIR, "..", ".env"),
    os.path.join(_THIS_DIR, "..", "env.txt"),
    os.path.expanduser(r"~\Annual_Quarter_report\Annual_Quarter_report\env.txt"),
    os.path.expanduser(r"~\Annual_Quarter_report\Annual_Quarter_report\.env"),
]
for _env_path in _ENV_LOCATIONS:
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
        break
else:
    load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)

# Default tracker path (Windows OneDrive)
DEFAULT_TRACKER_PATH = r"C:\Users\LeaKhoury–Active\OneDrive - ACTIVE FZ LLC\ActiveDMC-DC - SHARED DATA\CLIENT CAMPAIGNS\Active DMC\Reporting\Coverage Tracking\2026\ADMC_Coverage Tracker Consolidated 2026.xlsx"

# Also check a Linux-friendly path for when running on non-Windows
FALLBACK_TRACKER_PATHS = [
    os.path.expanduser("~/OneDrive/ActiveDMC-DC - SHARED DATA/CLIENT CAMPAIGNS/Active DMC/Reporting/Coverage Tracking/2026/ADMC_Coverage Tracker Consolidated 2026.xlsx"),
    os.path.join(_THIS_DIR, "trackers", "ADMC_Coverage_Tracker_Consolidated_2026.xlsx"),
]

# Report output directory
REPORTS_DIR = os.path.join(_THIS_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Upload directory for manual tracker uploads
UPLOAD_DIR = os.path.join(_THIS_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

generation_status = {}


def find_tracker_path():
    """Find the tracker file from known paths."""
    paths = [DEFAULT_TRACKER_PATH] + FALLBACK_TRACKER_PATHS
    custom = os.getenv("ADMC_TRACKER_PATH")
    if custom:
        paths.insert(0, custom)
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def get_client_tabs(tracker_path):
    """Read sheet/tab names from the consolidated tracker."""
    import openpyxl
    try:
        wb = openpyxl.load_workbook(tracker_path, read_only=True, data_only=True)
        sheets = wb.sheetnames
        wb.close()
        return sheets
    except Exception as e:
        return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return current configuration status."""
    tracker_path = find_tracker_path()
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_asana = bool(os.getenv("ASANA_PAT"))

    clients = []
    if tracker_path:
        clients = get_client_tabs(tracker_path)

    return jsonify({
        "tracker_found": tracker_path is not None,
        "tracker_path": tracker_path or "",
        "clients": clients,
        "has_anthropic_key": has_anthropic,
        "has_asana_token": has_asana,
    })


@app.route("/api/upload-tracker", methods=["POST"])
def upload_tracker():
    """Upload a tracker file manually."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename.endswith((".xlsx", ".xls")):
        return jsonify({"error": "File must be .xlsx or .xls"}), 400

    save_path = os.path.join(UPLOAD_DIR, "uploaded_tracker.xlsx")
    f.save(save_path)

    clients = get_client_tabs(save_path)
    return jsonify({
        "success": True,
        "tracker_path": save_path,
        "clients": clients,
    })


@app.route("/api/save-settings", methods=["POST"])
def save_settings():
    """Save API keys to .env file."""
    data = request.json
    env_path = os.path.join(_THIS_DIR, ".env")

    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()

    if data.get("anthropic_key"):
        env_vars["ANTHROPIC_API_KEY"] = data["anthropic_key"]
        os.environ["ANTHROPIC_API_KEY"] = data["anthropic_key"]
    if data.get("asana_token"):
        env_vars["ASANA_PAT"] = data["asana_token"]
        os.environ["ASANA_PAT"] = data["asana_token"]
    if data.get("tracker_path"):
        env_vars["ADMC_TRACKER_PATH"] = data["tracker_path"]
        os.environ["ADMC_TRACKER_PATH"] = data["tracker_path"]

    with open(env_path, "w") as f:
        for key, val in env_vars.items():
            f.write(f"{key}={val}\n")

    return jsonify({"success": True})


@app.route("/api/generate", methods=["POST"])
def generate_report():
    """Start report generation."""
    data = request.json
    client_name = data.get("client", "").strip()
    period_start = data.get("period_start", "").strip()
    period_end = data.get("period_end", "").strip()
    tracker_path = data.get("tracker_path") or find_tracker_path()
    uploaded_path = os.path.join(UPLOAD_DIR, "uploaded_tracker.xlsx")

    if not tracker_path and os.path.exists(uploaded_path):
        tracker_path = uploaded_path

    if not client_name:
        return jsonify({"error": "Please select a client"}), 400
    if not period_start:
        return jsonify({"error": "Please select a start date"}), 400

    period = period_start
    if period_end:
        period = f"{period_start} – {period_end}"

    # Generate unique job ID
    job_id = f"{client_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    generation_status[job_id] = {"status": "starting", "progress": 0, "message": "Initializing..."}

    # Run generation in background thread
    thread = threading.Thread(
        target=_run_generation,
        args=(job_id, client_name, period, tracker_path),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


def _run_generation(job_id, client_name, period, tracker_path):
    """Background report generation."""
    try:
        # Step 1: Parse tracker
        generation_status[job_id] = {"status": "running", "progress": 10, "message": "Reading coverage tracker..."}

        tracker_data = {}
        if tracker_path and os.path.exists(tracker_path):
            try:
                from data_sources.tracker_parser import parse_tracker_sheet
                tracker_data = parse_tracker_sheet(tracker_path, client_name)
            except Exception as e:
                generation_status[job_id]["message"] = f"Tracker warning: {e}"
                tracker_data = {"total_placements": 0, "rows": []}

        # Step 2: Fetch Asana data
        generation_status[job_id] = {"status": "running", "progress": 25, "message": "Fetching Asana deliverables..."}

        asana_token = os.getenv("ASANA_PAT")
        deliverables = []
        if asana_token:
            try:
                from data_sources.asana_fetcher import fetch_asana_data
                asana_data = fetch_asana_data(client_name, asana_token)
                deliverables = asana_data.get("deliverables", [])
            except Exception as e:
                pass

        # Step 3: Generate insights
        generation_status[job_id] = {"status": "running", "progress": 40, "message": "Generating strategic insights..."}

        insights = {}
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                from ai_engine.insight_generator import generate_all_insights

                def progress_cb(section, idx, total):
                    pct = 40 + int((idx / total) * 40)
                    generation_status[job_id] = {
                        "status": "running",
                        "progress": pct,
                        "message": f"Generating insights: {section}...",
                    }

                insights = generate_all_insights(
                    client=client_name,
                    period=period,
                    tracker_data=tracker_data,
                    deliverables_data=deliverables,
                    api_key=anthropic_key,
                    progress_callback=progress_cb,
                )
            except Exception as e:
                pass

        # Step 4: Build PPTX
        generation_status[job_id] = {"status": "running", "progress": 85, "message": "Building PowerPoint report..."}

        from report_builder.slide_factory import build_report

        safe_name = client_name.replace(" ", "_")
        safe_period = period.replace(" ", "_").replace("/", "-").replace("–", "-")
        filename = f"ADMC_{safe_name}_{safe_period}_Report.pptx"
        output_path = os.path.join(REPORTS_DIR, filename)

        build_report(
            client=client_name,
            period=period,
            tracker_data=tracker_data,
            deliverables=deliverables,
            insights=insights,
            output_path=output_path,
        )

        generation_status[job_id] = {
            "status": "complete",
            "progress": 100,
            "message": "Report ready!",
            "filename": filename,
        }

    except Exception as e:
        generation_status[job_id] = {
            "status": "error",
            "progress": 0,
            "message": f"Generation failed: {str(e)}",
        }


@app.route("/api/status/<job_id>")
def get_status(job_id):
    """Check generation status."""
    status = generation_status.get(job_id)
    if not status:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(status)


@app.route("/api/download/<filename>")
def download_report(filename):
    """Download a generated report."""
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route("/api/asana-setup")
def asana_setup():
    """Return Asana setup instructions."""
    return jsonify({
        "steps": [
            "1. Go to https://app.asana.com/0/my-apps",
            "2. Click '+ Create new token'",
            "3. Give it a name like 'ADMC Report Agent'",
            "4. Copy the token (you won't see it again)",
            "5. Paste it in the Settings panel of this app",
            "6. The agent will search your Asana workspace for projects matching the client name",
        ],
        "note": "The token gives read access to your Asana workspace. Store it securely."
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    url = f"http://localhost:{port}"
    print(f"\n  ADMC Reporting Agent")
    print(f"  Opening {url} in your browser...\n")
    print(f"  (Keep this window open while using the app)")
    print(f"  (Press Ctrl+C to stop)\n")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="0.0.0.0", port=port, debug=debug)
