"""Acceso a Firestore (base de datos nativa de GCP).

- En Cloud Run usa automáticamente las credenciales del servicio (ADC).
- En local usa el emulador (variable FIRESTORE_EMULATOR_HOST) o `gcloud auth application-default login`.
"""
import os
from google.cloud import firestore

from .config import settings


def _make_client() -> firestore.Client:
    kwargs = {}
    # El proyecto: explícito por config, o el que use el entorno (Cloud Run lo provee).
    project = settings.gcp_project or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if project:
        kwargs["project"] = project
    if settings.firestore_database and settings.firestore_database != "(default)":
        kwargs["database"] = settings.firestore_database
    return firestore.Client(**kwargs)


db = _make_client()

# Nombres de colecciones
USERS = "users"
PRODUCTS = "products"
SALES = "sales"
MERMAS = "mermas"


def doc_to_dict(snap) -> dict | None:
    """Convierte un snapshot de Firestore en dict, agregando su id."""
    if not snap.exists:
        return None
    data = snap.to_dict()
    data["id"] = snap.id
    return data


def col(name: str):
    return db.collection(name)
