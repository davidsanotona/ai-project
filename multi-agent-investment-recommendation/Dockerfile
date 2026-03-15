# Dockerfile
# ----------
# Multi-stage build: keeps the final image lean by separating
# dependency installation from the runtime layer.
#
# Stage 1 (builder): installs Python deps into a virtual environment
# Stage 2 (runtime): copies only the venv and app code — no build tools

# ---- Stage 1: builder ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies needed by some Python packages (e.g. yfinance C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker layer caching means this layer only
# rebuilds when requirements.txt changes, not on every code change
COPY requirements.txt .

# Install into an isolated venv inside the container
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy only the virtualenv from builder — no gcc, no pip cache
COPY --from=builder /opt/venv /opt/venv

# Copy application source
COPY . .

# Create output directory — volume can be mounted here from host
RUN mkdir -p /app/output

# Put venv binaries on PATH so `python` resolves to the venv interpreter
ENV PATH="/opt/venv/bin:$PATH"

# Explicitly add /app to PYTHONPATH so all modules resolve correctly
# regardless of how the container is invoked
ENV PYTHONPATH="/app"

# API keys are injected at runtime via --env-file or -e flags
# Never bake secrets into the image
ENV ANTHROPIC_API_KEY=""
ENV TAVILY_API_KEY=""

# Default entrypoint — can be overridden in docker-compose or docker run
ENTRYPOINT ["python", "main.py"]

# Default arguments — overridden by passing args after the image name
CMD ["--help"]