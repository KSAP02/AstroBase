# Build context is the repo root (see docker-compose.yml), because requirements.txt
# and data_warehouse/seed/ live there. .dockerignore keeps .env and the DB out.
FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependencies first, so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
# Baked in so the image can seed on its own; under Compose the ./data_warehouse
# volume mount covers this folder with the host copy (same files).
COPY data_warehouse/seed/ data_warehouse/seed/

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
