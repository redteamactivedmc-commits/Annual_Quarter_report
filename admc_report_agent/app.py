#!/usr/bin/env python3
"""ADMC Reporting Agent — Web Application."""

import os
import sys

# Prevent Flask and python-dotenv from auto-loading .env (crashes on Windows cp1252)
os.environ["FLASK_SKIP_DOTENV"] = "1"

import json
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
import calendar
import re

# Ensure the package root is on sys.path so internal imports work
# whether you run `python app.py` or `python -m admc_report_agent.app`
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from flask import Flask, render_template, request, jsonify, send_file, session


def _load_env_file(filepath):
    """Read a .env / env.txt file and set os.environ entries.

    Handles Windows cp1252 encoding (e.g. en-dash in OneDrive paths)
    without depending on python-dotenv which crashes on non-UTF-8 files.
    """
    content = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if content is None:
        return
    for line in content.splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            key, val = line.split("=", 1)
            val = val.strip().strip("\"'"  )
            os.environ[key.strip()] = val


# Load .env from multiple possible locations
_ENV_LOCATIONS = [
    os.path.join(_THIS_DIR, ".env"),
    os.path.join(_THIS_DIR, "env.txt"),
    os.path.join(_THIS_DIR, "..", ".env"),
    os.path.join(_THIS_DIR, "..", "env.txt"),
]
for _env_path in _ENV_LOCATIONS:
    if os.path.exists(_env_path):
        _load_env_file(_env_path)
        break

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)

# Tracker path is loaded from env var or settings panel — never hardcoded.
# Set ADMC_TRACKER_PATH in your .env / env.txt file, or use the app's
# settings panel to configure it. The app also checks these local fallbacks:
FALLBACK_TRACKER_PATHS = [
    os.path.join(_THIS_DIR, "trackers", "ADMC_Coverage_Tracker_Consolidated_2026.xlsx"),
    os.path.join(_THIS_DIR, "..", "trackers", "ADMC_Coverage_Tracker_Consolidated_2026.xlsx"),
]

# Report output directory
REPORTS_DIR = os.path.join(_THIS_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Upload directory for manual tracker uploads
UPLOAD_DIR = os.path.join(_THIS_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

generation_status = {}


def _get_asana_token():
    """Get the Asana token from env var, or from a plain asana_token.txt file.

    The text-file fallback is the simplest possible way to configure the
    token — it avoids any .env encoding/quoting issues.
    """
    token = os.getenv("ASANA_PAT")
    if token and token.strip():
        return token.strip()
    for candidate in (
        os.path.join(_THIS_DIR, "asana_token.txt"),
        os.path.join(_THIS_DIR, "..", "asana_token.txt"),
    ):
        if os.path.exists(candidate):
            try:
                for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                    try:
                        with open(candidate, "r", encoding=enc) as f:
                            val = f.read().strip().strip("\"'")
                        if val:
                            os.environ["ASANA_PAT"] = val
                            return val
                    except (UnicodeDecodeError, UnicodeError):
                        continue
            except Exception:
                pass
    return None


def find_tracker_path():
    """Find the tracker file from env var, settings, or local fallbacks."""
    custom = os.getenv("ADMC_TRACKER_PATH")
    paths = []
    if custom:
        paths.append(custom)
    paths.extend(FALLBACK_TRACKER_PATHS)
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
    has_asana = bool(_get_asana_token())

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
    data = request.json or {}
    env_path = os.path.join(_THIS_DIR, ".env")

    print(f"\n[Settings] Saving to: {env_path}")
    print(f"[Settings] Request data keys: {list(data.keys())}")

    env_vars = {}
    if os.path.exists(env_path):
        print(f"[Settings] .env exists, reading...")
        content = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                with open(env_path, "r", encoding=enc) as f:
                    content = f.read()
                print(f"[Settings] Read with encoding: {enc}")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if content:
            for line in content.splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()
            print(f"[Settings] Loaded {len(env_vars)} existing variables")
    else:
        print(f"[Settings] .env does not exist, creating new")

    def _sanitize(val):
        return val.replace("\n", "").replace("\r", "").strip()

    if data.get("anthropic_key"):
        val = _sanitize(data["anthropic_key"])
        env_vars["ANTHROPIC_API_KEY"] = val
        os.environ["ANTHROPIC_API_KEY"] = val
        print(f"[Settings] Set ANTHROPIC_API_KEY ({len(val)} chars)")
    if data.get("asana_token"):
        val = _sanitize(data["asana_token"])
        env_vars["ASANA_PAT"] = val
        os.environ["ASANA_PAT"] = val
        print(f"[Settings] Set ASANA_PAT ({len(val)} chars, first 12: {val[:12]}...)")
    if data.get("tracker_path"):
        val = _sanitize(data["tracker_path"])
        env_vars["ADMC_TRACKER_PATH"] = val
        os.environ["ADMC_TRACKER_PATH"] = val
        print(f"[Settings] Set ADMC_TRACKER_PATH")

    print(f"[Settings] Writing {len(env_vars)} variables to {env_path}")
    try:
        with open(env_path, "w") as f:
            for key, val in env_vars.items():
                f.write(f"{key}={val}\n")
        print(f"[Settings] ✓ Wrote .env successfully")
        print(f"[Settings] File now contains: {', '.join(env_vars.keys())}")
    except Exception as e:
        print(f"[Settings] ✗ FAILED to write .env: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

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


def _parse_period_dates(period):
    """
    Parse a period string like "2026-01 – 2026-03" into (start_date, end_date)
    as YYYY-MM-DD strings.

    Supports formats:
        "2026-01 – 2026-03"  (YYYY-MM range)
        "2026-01"            (single month)

    Returns (period_start, period_end) as YYYY-MM-DD strings, or (None, None).
    """
    if not period:
        return None, None

    # Split on dash/en-dash/em-dash with optional spaces
    parts = re.split(r'\s*[–—]\s*', period.strip())
    # Fall back to splitting on regular hyphen only if it separates YYYY-MM tokens
    if len(parts) == 1:
        # Try splitting on " - " (space-hyphen-space) to avoid splitting YYYY-MM
        parts = re.split(r'\s+-\s+', period.strip())
    parts = [p.strip() for p in parts if p.strip()]

    MONTH_NAMES = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9,
        "oct": 10, "nov": 11, "dec": 12,
    }

    def month_str_to_dates(s):
        """Convert various date formats to (first_day, last_day) strings."""
        s = s.strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
            return s, s
        m = re.match(r'^(\d{4})-(\d{2})$', s)
        if m:
            year, month = int(m.group(1)), int(m.group(2))
            last_day = calendar.monthrange(year, month)[1]
            return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"
        m = re.match(r'^(\w+)\s+(\d{4})$', s)
        if m:
            month_name = m.group(1).lower()
            year = int(m.group(2))
            month = MONTH_NAMES.get(month_name)
            if month:
                last_day = calendar.monthrange(year, month)[1]
                return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"
        return None, None

    if len(parts) == 1:
        start, end = month_str_to_dates(parts[0])
        return start, end
    elif len(parts) >= 2:
        start, _ = month_str_to_dates(parts[0])
        _, end = month_str_to_dates(parts[-1])
        return start, end

    return None, None


def _run_generation(job_id, client_name, period, tracker_path):
    """Background report generation."""
    try:
        warnings = []
        print(f"\n{'='*60}")
        print(f"  GENERATING REPORT: {client_name} | {period}")
        print(f"{'='*60}")

        # Step 1: Parse tracker
        generation_status[job_id] = {"status": "running", "progress": 10, "message": "Reading coverage tracker..."}

        tracker_data = {}
        if tracker_path and os.path.exists(tracker_path):
            try:
                from data_sources.tracker_parser import parse_tracker_sheet
                tracker_data = parse_tracker_sheet(tracker_path, client_name)
                print(f"  [Tracker] Found {tracker_data.get('total_placements', 0)} placements")
            except Exception as e:
                warnings.append(f"Tracker: {e}")
                print(f"  [Tracker] ERROR: {e}")
                tracker_data = {"total_placements": 0, "rows": []}
        else:
            print(f"  [Tracker] No tracker file found at: {tracker_path}")

        # Step 2: Fetch Asana data
        generation_status[job_id] = {"status": "running", "progress": 25, "message": "Fetching Asana deliverables..."}

        asana_token = _get_asana_token()
        deliverables = []
        asana_note = None
        period_start_date, period_end_date = _parse_period_dates(period)
        print(f"  [Asana] Token present: {bool(asana_token)}")
        print(f"  [Asana] Token first 8 chars: {asana_token[:8] + '...' if asana_token else 'NONE'}")
        print(f"  [Asana] Period parsed: {period_start_date} to {period_end_date}")
        if asana_token:
            try:
                from data_sources.asana_fetcher import fetch_asana_data
                asana_data = fetch_asana_data(
                    client_name, asana_token,
                    period_start=period_start_date,
                    period_end=period_end_date,
                )
                deliverables = asana_data.get("deliverables", [])
                print(f"  [Asana] Projects found: {[p['name'] for p in asana_data.get('projects_found', [])]}")
                print(f"  [Asana] Total tasks: {asana_data.get('total_tasks', 0)}")
                print(f"  [Asana] Deliverables: {len(deliverables)}")
                if asana_data.get("error"):
                    warnings.append(f"Asana: {asana_data['error']}")
                    asana_note = f"Could not load deliverables from Asana:\n{asana_data['error']}"
                    print(f"  [Asana] WARNING: {asana_data['error']}")
                elif not deliverables:
                    asana_note = (
                        f"No deliverables found for '{client_name}' in the period "
                        f"{period_start_date} to {period_end_date}.\n"
                        f"Asana connected OK but matched 0 tasks in this date range."
                    )
            except Exception as e:
                warnings.append(f"Asana error: {e}")
                asana_note = f"Asana error: {e}"
                print(f"  [Asana] ERROR: {e}")
                import traceback
                traceback.print_exc()
        else:
            warnings.append("Asana: No token configured — deliverables will be empty")
            asana_note = (
                "No Asana token configured.\n"
                "Add your token in Settings, or create a file named 'asana_token.txt' "
                "in the admc_report_agent folder containing just the token."
            )
            print("  [Asana] SKIPPED — no token")

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
                warnings.append(f"AI: {e}")
        else:
            warnings.append("AI: No Anthropic API key — insights will be empty")

        # Step 4: Build PPTX
        generation_status[job_id] = {"status": "running", "progress": 85, "message": "Building PowerPoint report..."}

        from report_builder.slide_factory import build_report, load_logo, load_admc_logo, _INPUT_DIRS
        print(f"  [Logos] Input dirs: {_INPUT_DIRS}")
        print(f"  [Logos] Client logo: {load_logo(client_name)}")
        print(f"  [Logos] ADMC logo: {load_admc_logo()}")

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
            deliverables_note=asana_note,
        )

        msg = "Report ready!"
        if warnings:
            msg += " Warnings: " + "; ".join(warnings)
        generation_status[job_id] = {
            "status": "complete",
            "progress": 100,
            "message": msg,
            "filename": filename,
            "warnings": warnings,
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
    from werkzeug.utils import secure_filename as _secure
    safe_name = _secure(filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join(REPORTS_DIR, safe_name)
    if not os.path.realpath(filepath).startswith(os.path.realpath(REPORTS_DIR)):
        return jsonify({"error": "Invalid filename"}), 400
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True, download_name=safe_name)


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


@app.route("/api/assets")
def list_assets():
    """List available logos and images in input/ and Inputs/ folders."""
    input_dirs = []
    for name in ("input", "Inputs"):
        d = os.path.join(_THIS_DIR, name)
        if os.path.isdir(d):
            input_dirs.append(d)

    assets = {"client_logos": set(), "admc_logos": set(), "images": set()}

    for input_dir in input_dirs:
        for sub in ("logos/clients", "logos/Clients"):
            clients_dir = os.path.join(input_dir, sub)
            if os.path.isdir(clients_dir):
                assets["client_logos"].update(f for f in os.listdir(clients_dir) if not f.startswith("."))

        for sub in ("logos/active_dmc", "logos/Active_DMC"):
            admc_dir = os.path.join(input_dir, sub)
            if os.path.isdir(admc_dir):
                assets["admc_logos"].update(f for f in os.listdir(admc_dir) if not f.startswith("."))

        images_dir = os.path.join(input_dir, "images")
        if os.path.isdir(images_dir):
            assets["images"].update(f for f in os.listdir(images_dir) if not f.startswith("."))

    return jsonify({k: sorted(v) for k, v in assets.items()})


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
