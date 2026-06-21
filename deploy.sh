#!/usr/bin/env bash
# Despliegue de FeriaKL a Google Cloud Run + Firestore (todo en el free tier).
# Uso:   bash deploy.sh
# Requisitos: gcloud instalado y autenticado (gcloud auth login).
set -euo pipefail

# ===== Parámetros (ajústalos) =====
PROJECT="${PROJECT:-feriakl-app}"          # ID del proyecto GCP (debe ser único global)
REGION="${REGION:-southamerica-west1}"     # región de Cloud Run (Santiago)
FS_LOCATION="${FS_LOCATION:-southamerica-west1}"  # ubicación de Firestore (si falla, prueba nam5)
SERVICE="${SERVICE:-feriakl}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@feriakl.cl}"

echo "==> Proyecto: $PROJECT | Región: $REGION | Servicio: $SERVICE"
gcloud config set project "$PROJECT"

echo "==> Habilitando APIs (Run, Firestore, Build, Artifact Registry, Secret Manager)..."
gcloud services enable \
  run.googleapis.com firestore.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com

echo "==> Creando base de datos Firestore (Native) si no existe..."
if ! gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  gcloud firestore databases create --location="$FS_LOCATION" --type=firestore-native
else
  echo "    Firestore ya existe."
fi

echo "==> Creando secretos (SECRET_KEY y SEED_ADMIN_PASSWORD) si no existen..."
if ! gcloud secrets describe feriakl-secret-key >/dev/null 2>&1; then
  openssl rand -hex 32 | tr -d '\n' | gcloud secrets create feriakl-secret-key --data-file=-
fi
if ! gcloud secrets describe feriakl-admin-password >/dev/null 2>&1; then
  # Genera una contraseña inicial fuerte para el admin (cámbiala luego desde la app).
  ADMIN_PW="$(openssl rand -base64 12 | tr -d '\n/+=' | cut -c1-14)"
  printf '%s' "$ADMIN_PW" | gcloud secrets create feriakl-admin-password --data-file=-
  echo "    >>> Contraseña inicial del admin: $ADMIN_PW"
  echo "    >>> Guárdala. Entra y cámbiala con el botón 🔑."
fi

# Cuenta de servicio del runtime de Cloud Run (por defecto la de Compute) con acceso a Firestore.
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "==> Dando acceso a Firestore y a los secretos a la cuenta $RUNTIME_SA ..."
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/datastore.user" >/dev/null
gcloud secrets add-iam-policy-binding feriakl-secret-key \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/secretmanager.secretAccessor" >/dev/null
gcloud secrets add-iam-policy-binding feriakl-admin-password \
  --member="serviceAccount:${RUNTIME_SA}" --role="roles/secretmanager.secretAccessor" >/dev/null

echo "==> Desplegando a Cloud Run (build del Dockerfile en la raíz)..."
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 512Mi \
  --set-env-vars "ENVIRONMENT=production,GCP_PROJECT=${PROJECT},SEED_ADMIN_EMAIL=${ADMIN_EMAIL}" \
  --set-secrets "SECRET_KEY=feriakl-secret-key:latest,SEED_ADMIN_PASSWORD=feriakl-admin-password:latest"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo ""
echo "================================================================"
echo "  ¡Listo! FeriaKL está en:  $URL"
echo "  Login: $ADMIN_EMAIL  (contraseña: la mostrada arriba)"
echo "================================================================"
