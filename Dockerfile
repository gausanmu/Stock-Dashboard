# Use Python 3.11 slim image
FROM python:3.11-slim AS backend-builder

# Set working directory for backend
WORKDIR /app/backend

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Use Node 18 to build frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies and build React app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY frontend/ .
ENV CI=false
RUN npm run build

# Final Unified Image
FROM python:3.11-slim
WORKDIR /app

# Install bash/curl in final image just in case
RUN apt-get update && apt-get install -y --no-install-recommends curl bash && rm -rf /var/lib/apt/lists/*

# Copy python dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend source
COPY backend/ /app/backend/

# Copy built frontend statically into place
COPY --from=frontend-builder /app/frontend/build /app/frontend/build

# Expose render web port
EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0

WORKDIR /app/backend
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
