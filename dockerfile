# --- Stage 1: Builder (install dependencies) ---
FROM python:3.11-slim AS builder

# Avoid prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# Install OS deps required for building some Python packages (kept minimal)
# You can add packages here if any requirement needs them (e.g. gcc, libffi-dev).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create working dir for building wheels
WORKDIR /app

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip, install wheel, then install requirements into the builder image
RUN python -m pip install --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Final runtime image ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    FLASK_ENV=production \
    PORT=5000

# Create non-root user and app directory
ARG APP_USER=appuser
ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd --gid ${APP_GID} ${APP_USER} \
    && useradd --uid ${APP_UID} --gid ${APP_GID} --create-home --shell /bin/bash ${APP_USER} \
    && mkdir -p /app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

# Ensure proper ownership
RUN chown -R ${APP_USER}:${APP_USER} /app

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE 5000

# Healthcheck (simple HTTP check; adjust as needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import sys,urllib.request; \
    import json; \
    try: \
      req=urllib.request.Request('http://127.0.0.1:5000/'); \
      urllib.request.urlopen(req, timeout=2); \
      sys.exit(0) \
    except Exception as e: \
      sys.exit(1)"

# Command: use gunicorn with sensible defaults. Adjust workers for your CPU count.
# NOTE: app:app assumes your Flask file is app.py and Flask instance is `app`.
CMD ["python", "app.py"]

