"""Configuración de la app, leída desde variables de entorno (.env en local)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- GCP / Firestore ---
    # ID del proyecto de Google Cloud. En Cloud Run se detecta solo; en local conviene fijarlo.
    gcp_project: str = ""
    # Base de datos Firestore a usar ("(default)" salvo que crees una con nombre).
    firestore_database: str = "(default)"

    # --- Seguridad ---
    # Clave para firmar los JWT. OBLIGATORIO en producción (se inyecta como secreto).
    secret_key: str = "dev-insegura-cambiar-en-produccion"
    access_token_expire_minutes: int = 60 * 12  # 12 horas (una jornada)
    algorithm: str = "HS256"

    # "production" activa chequeos estrictos (exige secretos fuertes, cabeceras HSTS, etc.).
    environment: str = "development"

    # Orígenes permitidos para CORS. Vacío = solo mismo origen (la app se sirve desde el backend).
    cors_origins: str = ""

    # --- Frontend ---
    # Carpeta del frontend. Vacío = autodetecta (raíz del repo en local); en el contenedor: FRONTEND_DIR.
    frontend_dir: str = ""

    # --- Datos iniciales (seed) ---
    seed_admin_email: str = "admin@feriakl.cl"
    seed_admin_password: str = ""   # si está vacío en producción, NO se crea admin con clave por defecto
    seed_admin_name: str = "Administrador"
    seed_demo_products: bool = True  # cargar productos de limpieza de ejemplo si la colección está vacía

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")


settings = Settings()
