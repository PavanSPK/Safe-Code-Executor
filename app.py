"""
app.py

Flask application that provides:
- POST /run       -> run single code snippet (language: python|node)
- POST /run-batch -> run multiple snippets in parallel (up to 5)
- POST /run-zip   -> upload a zip, extract and run entry file
- GET  /history   -> recent runs (in-memory + sqlite persisted)
- GET  /          -> UI (templates/index.html)
"""

import os
import time
import sqlite3
import tempfile
import zipfile
import threading
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

from executor import run_code, run_multiple

app = Flask(__name__, template_folder="templates")

MAX_CODE_CHARS = 5000
HISTORY = []
HISTORY_LOCK = threading.Lock()
MAX_HISTORY = 100
DB_PATH = "history.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        language TEXT,
        code TEXT,
        output TEXT,
        error TEXT,
        exit_code INTEGER
    )
    """)
    conn.commit()
    conn.close()


def save_history_item(item):
    """
    Save item both to in-memory HISTORY list and persist to sqlite.
    item: dict with keys: timestamp, language, code, output, error, exit_code
    """
    with HISTORY_LOCK:
        HISTORY.insert(0, item)
        if len(HISTORY) > MAX_HISTORY:
            HISTORY.pop()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO runs (timestamp, language, code, output, error, exit_code) VALUES (?, ?, ?, ?, ?, ?)",
        (item["timestamp"], item["language"], item["code"], item["output"], item["error"], item["exit_code"])
    )
    conn.commit()
    conn.close()


@app.route("/run", methods=["POST"])
def run():
    """
    POST /run
    Body: { "code": "...", "language": "python" }
    """
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    language = (data.get("language", "python") or "python").lower()

    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Field 'code' is required and must be a non-empty string."}), 400

    if len(code) > MAX_CODE_CHARS:
        return jsonify({"error": f"Code is too long (max {MAX_CODE_CHARS} characters)."}), 400

    out, err, status = run_code(code, language)

    item = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "language": language,
        "code": code[:2000],
        "output": out,
        "error": err,
        "exit_code": status
    }
    try:
        save_history_item(item)
    except Exception:
        # don't fail the API if history DB fails
        pass

    return jsonify({"output": out, "error": err, "exit_code": status})


@app.route("/run-batch", methods=["POST"])
def run_batch():
    """
    POST /run-batch
    Body: { "tasks": [ { "code": "...", "language":"python" }, ... ] }
    Runs up to 5 containers in parallel and returns results list.
    """
    data = request.get_json(silent=True) or {}
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return jsonify({"error": "Missing tasks list"}), 400

    # Validate tasks
    for t in tasks:
        if not isinstance(t.get("code", ""), str):
            return jsonify({"error": "Each task must have a code string"}), 400
        if len(t.get("code", "")) > MAX_CODE_CHARS:
            return jsonify({"error": "A task code is too long"}), 400

    results = run_multiple(tasks, max_workers=5)

    # Save each to history
    for idx, t in enumerate(tasks):
        item = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "language": t.get("language", "python"),
            "code": t.get("code", "")[:2000],
            "output": results[idx]["output"],
            "error": results[idx]["error"],
            "exit_code": results[idx]["exit_code"]
        }
        try:
            save_history_item(item)
        except Exception:
            pass

    return jsonify({"results": results})


@app.route("/run-zip", methods=["POST"])
def run_zip():
    """
    POST /run-zip
    Form data:
      - file: zip file
      - entry: entry filename inside zip (e.g., main.py or index.js)
      - language: python|node
    """
    file = request.files.get("file")
    entry = request.form.get("entry")
    language = (request.form.get("language", "python") or "python").lower()

    if not file or not entry:
        return jsonify({"error": "file and entry required (entry = filename inside zip)"}), 400

    filename = secure_filename(file.filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, filename)
        file.save(zip_path)
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(tmpdir)
        except zipfile.BadZipFile:
            return jsonify({"error": "Bad zip file"}), 400

        # Ensure the entry exists relative to tmpdir
        entry_path = os.path.join(tmpdir, entry)
        if not os.path.exists(entry_path):
            return jsonify({"error": "Entry file not found in zip"}), 400

        # Now run the entry file from the extracted directory (mounting it)
        from executor import run_code_from_dir
        out, err, status = run_code_from_dir(entry, language, tmpdir)

        item = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "language": language,
            "code": f"[zip run] {entry} (from {filename})",
            "output": out,
            "error": err,
            "exit_code": status
        }
        try:
            save_history_item(item)
        except Exception:
            pass

        return jsonify({"output": out, "error": err, "exit_code": status})


@app.route("/history", methods=["GET"])
def history():
    with HISTORY_LOCK:
        # return a shallow copy
        return jsonify({"history": HISTORY})


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
