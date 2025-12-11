# Safe Code Executor — Secure Python & Node.js Sandbox Using Docker

Safe Code Executor is a fully functional miniature online code-runner system.  
It allows users to submit Python and Node.js code via an API or Web UI, which is executed securely inside Docker containers with strong isolation.

The project demonstrates how to safely run untrusted code using Docker-based sandboxing with resource limits and network isolation.

-----------------------------------------------------------------------------------------------------
## 1. Project Architecture
![safe-code-executor_architecture](https://github.com/PavanSPK/Safe-Code-Executor/blob/45f2f3c7136aae6a3df9bf77582e1acf5234588c/screenshots/safe-code-executor_architecture.png)
-----------------------------------------------------------------------------------------------------
## 2. Project Structure
```
## Project structure
```text
safe-code-executor/
├── app.py                  # Flask application: routes (/ , /run, /run-zip, /run-batch, /history)
├── executor.py             # Docker execution engine: builds and runs sandboxed containers
├── requirements.txt        # Python dependencies for the backend
├── Dockerfile              # Container image for deploying the backend itself
├── templates/
│   └── index.html          # Frontend UI: editor, snippets, output/errors, ZIP upload, history
├── test_security.py        # Script to automatically test timeout, memory, network, and validation
├── ziptest.zip             # Pre-built sample ZIP created from sample_data/ziptest
│      ├── main.py          # Entry file used in ZIP test (imports util and prints a message)
│      └── util.py          # Helper module used by main.py
└── tasks.json              # 5 containers in parallel (run-batch endpoint)
```
-----------------------------------------------------------------------------------------------------
### 3. Prerequisites
- Docker installed and running on the host machine.
- Python 3.11 (or 3.10+) and pip.
- For Windows: PowerShell or WSL for bash commands is recommended.
- Network access to pull Docker images on first run (python:3.11-slim, node:20-slim). You can pre-pull images if desired.
-----------------------------------------------------------------------------------------------------
## 4. Installation and Running
### Step 1 — Clone
```
git clone https://github.com/PavanSPK/Safe-Code-Executor.git  
cd safe-code-executor
```
### Step 2 — Create venv
Windows:
```
 `venv\Scripts\activate`  
```
Linux/macOS: 
```
`source venv/bin/activate`
```
### Step 3 — Install dependencies
```
pip install -r requirements.txt
```
### Step 4 — Pull images (optional)
```
docker pull python:3.11-slim  
docker pull node:20-slim
```
### Step 5 — Run server
```
python app.py
```
### Step 6 — Open UI
```
http://localhost:5000
```
-----------------------------------------------------------------------------------------------------
## Docker Build, Push & Pull Instructions
This section explains how to containerize the Safe Code Executor backend, push it to a container registry, and pull it on another system.
### 1. Build the Docker image
From the project root:
```
docker build -t spk487/safe-code-executor:latest .
```
Example:
```
docker build -t spk487/safe-code-executor:latest .
```
### 2. Test the image locally
```
docker run -p 5000:5000 spk487/safe-code-executor:latest
```
Open:
http://localhost:5000
Your UI should load.
### 3. Log in to Docker Hub
```
docker login
```
Enter your Docker Hub credentials.
### 4. Push the image to Docker Hub
```
docker push ]spk487/safe-code-executor:latest
```
Example push:
```
docker push spk487/safe-code-executor:latest
```
### 5. Pull the image anywhere
Public Docker link:
```
docker pull spk487/safe-code-executor
```
### 6. Run from Docker Hub (no local build needed)
```
docker run -p 5000:5000 spk487/safe-code-executor:latest
```
Example:
```
docker run -p 5000:5000 spk487/safe-code-executor:latest
```
This instantly launches the Safe Code Executor server using your pushed image.

-----------------------------------------------------------------------------------------------------
## 5. API Documentation
### /run (POST)
Executes a single code snippet.
Request:
```
{"code": "print(5+3)", "language": "python"}
```
Response:
```
{"output": "4\n", "error": "", "exit_code": 0}
```
-----------------------------------------------------------------------------------------------------
### /run-zip (POST)
Executes a ZIP file.
Multipart form:
- file=@project.zip
- entry=main.py
- language=python
-----------------------------------------------------------------------------------------------------
### /run-batch (POST)
Executes up to 5 tasks in parallel.

-----------------------------------------------------------------------------------------------------
## 6. Web UI Overview
UI includes:
- Code editor
- Language selector
- Run button
- Output + Errors panels
- Execution history
- ZIP upload panel
- Snippet buttons

![ui](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/ui.png)
-----------------------------------------------------------------------------------------------------

## 7. Security Features Implemented
### 7.1 Timeout (10 seconds)
```
while True: pass
```
triggers:  
**Execution timed out after 10 seconds**
### 7.2 Memory limit (128m)
Large allocations trigger:  
**Process killed (likely out of memory > 128m)**
### 7.3 Network isolation
Any HTTP request results in DNS/network error.
### 7.4 Read-only filesystem
Writing to `/tmp` or root fails with:  
**Read-only file system**
### 7.5 Code length validation
Rejects scripts >5000 characters.

-----------------------------------------------------------------------------------------------------
## 8. Docker Security Experiments
Now we use the system you built to learn about Docker’s isolation.
### 8.1. Try to read /etc/passwd
```
with open("/etc/passwd") as f:
    print(f.read())
```
#### What happens?
- It will usually work.
- But it’s reading /etc/passwd inside the container, not your host’s file.
- That file contains container’s users (like root:x:0:0:root:/root:/bin/bash etc.)
Lesson:
Docker isolates filesystem namespaces, but inside the container, the program can read any file that is readable inside that container filesystem.
### 8.2. Try to write to /tmp
```
with open("/tmp/test.txt", "w") as f:
    f.write("hacked!")
print("done")
```
### What happens?
- It will probably work by default.
- It writes to /tmp inside the container.
- That file disappears when the container stops (--rm removes container and ephemeral FS).
Lesson:
By default, the container root filesystem is writable.
But this is separate from your host, so it can’t directly overwrite your host files (unless you mount a host directory).
### 8.3. Add --read-only and test again
Modify executor.py to add --read-only:
```
cmd = [
    "docker", "run", "--rm",
    "--memory", MEMORY_LIMIT,
    "--network", "none",
    "--read-only",            # <--- add this
    "-v", f"{tmpdir}:/app:ro", # mount script dir as read-only too
    "-w", "/app",
    PYTHON_IMAGE,
    "python", "user_code.py",
]
```
Now test the /tmp write code again:
```
with open("/tmp/test.txt", "w") as f:
    f.write("hacked!")
print("done")
```
Expected:
- This should now fail with a permission / read-only filesystem error.
- Your API returns this error in error field.
Lesson:
- --read-only makes the container’s root filesystem read-only.
- You can selectively mount specific directories as writable (e.g., a scratch volume) if needed.
- This is a powerful extra safety layer against malicious writes.
-----------------------------------------------------------------------------------------------------
## 9. Simple Report
### What worked?
- Code executed safely.
- Timeout triggered correctly.
- OOM kill worked.
- Network completely blocked.
- Read-only filesystem prevented writes.
- ZIP and batch runs succeeded.
### What failed?
- Writing to container filesystem before enabling read-only (expected).
- Any network attempt.
- Any code exceeding memory/time limits.
### What I learned
- Docker provides useful but not perfect isolation.
- Additional flags (`--read-only`, `--network none`) dramatically improve safety.
- Memory and time must be enforced externally.
- Online code runner systems use similar sandboxing layers.
- Containers can still access some internal files; isolation ≠ full security.
-----------------------------------------------------------------------------------------------------
## 10. Required Demonstration Tests
### Phase 1 — Normal code
- Hello (python)

![hello](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/hello.png)

- Arithmetic

 ![arithmetic](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/arithmetic.png)

- loops

![loop](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/loop.png)
![node_loop](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/node_loop.png)

### Phase 2 — Security tests
- Infinite loop → timeout 

![infinite_loop](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/infinite_loop.png)

- Memory bomb → OOM  

![memory_bomb](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/memory_bomb.png)

- Network request → blocked

 ![nw_test](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/nw_test.png)
 ![nw_test2](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/nw_test2.png)
 ![node_nw](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/node_nw.png)

- Write file → blocked (read-only)  

 ![write](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/write.png)

- Long code (>5000 chars) → rejected  

 ![5000_chars](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/5000_chars.png)

### Phase 3 — Docker experiments
- Read /etc/passwd  

 ![read](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/read.png)

- Write before/after read-only flag  

 ![alloc](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/alloc.png)

-------------------------------------------------------------------------------------------------------------------------------------------

## 11. Bonus Features Implemented
### Easy Level
### - Node.js execution
- Support JavaScript (Node.js)
- Added a language field to /run (defaults to python).
- If language == "node" use node:20-slim and run node user_code.js with the same Docker safety flags.

 ![node_hello](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/node_hello.png)

### - UI improvements: add language selector, prettier tweaks, history panel
- Added a language select (Python / NodeJS).
- Added a History sidebar (list recent runs returned from /history).
- Added a button to run a batch of snippets.
- Added Prism.js for syntax highlighting in read-only preview (we’ll keep the editor as <textarea> but show a highlighted preview).
Below is a drop-in replacement of your index.html that:
- Adds a language select
- Shows a History panel on the right (fetches /history)
- Adds a "Run as Node" option
- Adds basic Prism highlighting for the preview (client side)
- Execution history

![ui](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/ui.png)

### - Add history of recent executions
- Included in backend app.py and UI /history usage. History stores timestamp, language, truncated code, output, error, exit_code.

### Medium Level
### - Support multiple files (user uploads a zip)
What this does
- Adds a new endpoint POST /run-zip that accepts multipart/form-data with a zip file, extracts it to a temp folder, and runs a specified entrypoint (e.g., main.py or index.js) inside Docker with same safety flags.

![zip](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/zip.png)

### - Syntax highlighting (optional)
- highlights a read-only preview using Prism. This avoids replacing <textarea> (which is heavy to replace with a code editor) while still showing highlighted code.

![ui](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/ui.png)

### - Parallel execution (5 containers)
- Implemented in executor.py as run_multiple using ThreadPoolExecutor(max_workers=5) and exposed via /run-batch endpoint. UI can send a list of tasks:
Example curl:
```
curl -X POST http://localhost:5000/run-batch \
  -H "Content-Type: application/json" \
  -d '{"tasks":[{"code":"print(1)","language":"python"},{"code":"console.log(2)","language":"node"}]}'
```
- Response: JSON with results list, each entry {"output","error","exit_code"} in same order.

![parallel2](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/parallel2.png)
![parallel1](https://github.com/PavanSPK/Safe-Code-Executor/blob/33cec7d5e34d589b9126d4bb806aafbfdc3917ee/screenshots/parallel1.png)
-----------------------------------------------------------------------------------------------------
## 12. Final Learning Reflection (Short Brief)
This project provided hands-on experience building a secure sandbox for executing untrusted code. The key learnings are:
### 1. Why untrusted code is dangerous
Running external code can cause infinite loops, memory exhaustion, unauthorized file access, or network abuse. This highlighted the need for strict isolation and resource controls.
### 2. Docker as a security boundary
I learned how Docker containers provide process isolation and how features like:
- --memory
- --network none
- --read-only
controlled bind mounts help limit what code can access. I also learned Docker’s limitations (containers can still read /etc/passwd, can still consume CPU, etc.).
### 3. Implementing layered safety
Security must be multi-layered. I implemented:
- timeouts
- memory limits
- input size validation
- disabled networking
- read-only file systems
- clean error messages
- These layers together make execution safer.
### 4. Multi-language and multi-file execution
Adding Node.js support and ZIP project execution taught me how to generalize the executor to support different runtimes and filesystem structures inside containers.
### 5. Concurrency & parallel containers
Running 5 containers in parallel using ThreadPoolExecutor helped me understand safe concurrency, container scheduling, and how parallel workloads are isolated.
### 6. Building a clean UI
The UI work improved my understanding of frontend design, syntax highlighting, editor behavior, and user-friendly error display.
### 7. Automated security testing
Creating test_security.py taught me how to systematically test:
- timeout behavior
- memory crashes
- network blocking
- input validation
This reinforced the importance of regression testing in security-focused projects.
### 8. Documentation & architecture thinking
Preparing the README, diagrams, and test instructions helped strengthen skills in communicating design decisions and explaining system behavior clearly.

-----------------------------------------------------------------------------------------------------
## Author
**Sandu Pavan Kumar**  
GitHub: [@PavanSPK](https://github.com/PavanSPK) 
