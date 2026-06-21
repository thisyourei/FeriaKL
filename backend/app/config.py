"""Configuración de la app, leída desde variables de entorno (.env en local)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # En local usa SQLite (no requiere instalar nada). En Cloud Run apunta a Cloud SQL:
    #   postgresql+psycopg2://USER:PASS@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE
    database_url: str = "sqlite:///./feriakl.db"

    # Clave para firmar los JWT. En producción se inyecta como secreto (NO hardcodear).
    secret_key: str = "cambia-esta-clave-en-produccion-usa-un-secreto-de-gcp"
    access_token_expire_minutes: int = 60 * 12  # 12 horas (jornada de feria)
    algorithm: str = "HS256"

    # Orígenes permitidos para el frontend (CORS).
    cors_origins: str = "*"

    # Carpeta con el frontend a servir. Vacío = autodetecta (raíz del repo en local).
    # En el contenedor de producción se fija por variable de entorno (FRONTEND_DIR).
    frontend_dir: str = ""

    # Datos del usuario admin que se crea al iniciar si la base está vacía.
    seed_admin_email: str = "admin@feriakl.cl"
    seed_admin_password: str = "feria1234"
    seed_admin_name: str = "Administrador"


settings = Settings()
