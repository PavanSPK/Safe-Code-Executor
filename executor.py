# executor.py
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

PYTHON_IMAGE = "python:3.11-slim"
NODE_IMAGE = "node:20-slim"

TIMEOUT_SECONDS = 10
MEMORY_LIMIT = "128m"

DOCKER_BASE_FLAGS = [
    "docker", "run", "--rm",
    "--memory", MEMORY_LIMIT,
    "--network", "none",
    "--read-only",
]


def _build_cmd_for_file(container_filename: str, lang: str, tmpdir: str):
    lang = (lang or "python").lower()
    if lang == "python":
        image = PYTHON_IMAGE
        run_cmd = ["python", container_filename]
    elif lang == "node":
        image = NODE_IMAGE
        run_cmd = ["node", container_filename]
    else:
        raise ValueError(f"Unsupported language: {lang}")

    cmd = DOCKER_BASE_FLAGS + [
        "-v", f"{tmpdir}:/app:ro",
        "-w", "/app",
        image
    ] + run_cmd

    return cmd


def run_code(code: str, lang: str = "python"):
    """
    Run code in Docker. lang: "python" or "node".
    Returns (stdout, stderr, exit_code).
    """
    lang = (lang or "python").lower()
    if lang not in ("python", "node"):
        return "", f"Unsupported language: {lang}", -2

    # correct file names
    filename = "user_code.py" if lang == "python" else "user_code.js"

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

        cmd = _build_cmd_for_file(filename, lang, tmpdir)

        # debugging so you see exactly what command is used
        print("DEBUG executor: running command:", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )

            stdout = result.stdout or ""
            stderr = result.stderr or ""
            exit_code = result.returncode

            # ---- OOM FIX: detect container kill ----
            if exit_code == 137 or "Killed" in stderr or "OOM" in stderr:
                return "", f"Process killed (likely out of memory > {MEMORY_LIMIT}).", 137

            # ---- Python-level MemoryError ----
            if "MemoryError" in stderr:
                return "", stderr, exit_code

            return stdout, stderr, exit_code

        except subprocess.TimeoutExpired:
            return "", f"Execution timed out after {TIMEOUT_SECONDS} seconds.", -1


def run_code_from_dir(entry_filename: str, lang: str, host_dir: str):
    """
    Run an existing file (entry_filename) inside an already-extracted host_dir by
    mounting host_dir into the container and executing the entry file.
    Returns: stdout, stderr, exit_code
    """
    lang = (lang or "python").lower()
    if lang not in ("python", "node"):
        return "", f"Unsupported language: {lang}", -2

    # ensure entry exists in host_dir (server side)
    entry_path = os.path.join(host_dir, entry_filename)
    if not os.path.exists(entry_path):
        return "", f"Entry file not found: {entry_filename}", -3

    # Use container-side path same as entry_filename (we mount host_dir to /app)
    cmd = _build_cmd_for_file(entry_filename, lang, host_dir)
    print("DEBUG executor: running command (from dir):", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode
        if exit_code != 0 and "Killed" in stderr:
            stderr = f"Process killed (likely out of memory > {MEMORY_LIMIT})."
        return stdout, stderr, exit_code
    except subprocess.TimeoutExpired:
        return "", f"Execution timed out after {TIMEOUT_SECONDS} seconds.", -1


def run_multiple(tasks, max_workers=5):
    """
    Runs up to 5 containers in parallel.
    """
    results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures_map = {}
        for i, t in enumerate(tasks):
            code = t.get("code", "")
            lang = t.get("lang", "python")
            futures_map[ex.submit(run_code, code, lang)] = i

        for fut in as_completed(futures_map):
            i = futures_map[fut]
            try:
                out, err, code = fut.result()
            except Exception as e:
                out, err, code = "", f"Executor error: {e}", -3
            results[i] = {"output": out, "error": err, "exit_code": code}

    return results
