# Imagen de producción para Cloud Run: incluye el backend (FastAPI) Y el frontend (PWA).
# Cloud Run termina el TLS automáticamente con un certificado administrado y confiable,
# por eso la app corre en HTTP simple dentro del contenedor (en el puerto $PORT).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv

# Dependencias
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend
COPY backend/app ./app
# Frontend (servido por el mismo backend, mismo origen)
COPY index.html manifest.json sw.js ./
COPY vendor ./vendor

# El frontend vive aquí dentro de la imagen
ENV FRONTEND_DIR=/srv
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
