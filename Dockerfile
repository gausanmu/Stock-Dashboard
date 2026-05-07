# ── Stage 1: Backend deps ────────────────────────────────────────
FROM python:3.11-slim AS backend-builder
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 2: Frontend build ──────────────────────────────────────
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

# Install deps. The emergentbase visual-edits package is dev-only
# and hosted on an external URL that may be unreachable from CI.
# If install fails on it, strip it and retry.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps 2>/dev/null || \
    (sed -i '/@emergentbase/d' package.json && npm install --legacy-peer-deps)

COPY frontend/ .
ENV CI=false
ENV REACT_APP_BACKEND_URL=""
RUN npm run build

# Verify the build actually produced output
RUN test -f /app/frontend/build/index.html || (echo "FATAL: React build missing index.html" && exit 1)

# ── Stage 3: Final image ────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl bash && rm -rf /var/lib/apt/lists/*

# Python deps
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Backend source
COPY backend/ /app/backend/

# Frontend static build
COPY --from=frontend-builder /app/frontend/build /app/frontend/build

EXPOSE 8000
ENV PORT=8000
ENV HOST=0.0.0.0

WORKDIR /app/backend
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
