"""Punto de entrada de la API FeriaKL (FastAPI + Firestore)."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .seed import seed
from .routers import auth, products, sales, mermas, reports

log = logging.getLogger("feriakl")
logging.basicConfig(level=logging.INFO)

# Carpeta del frontend (index.html, manifest.json, sw.js, vendor/).
FRONTEND_DIR = Path(settings.frontend_dir) if settings.frontend_dir else Path(__file__).resolve().parent.parent.parent

# Política de seguridad de contenido. Permite el script/estilo en línea de la app
# (todo el JS es propio y del mismo origen) y bloquea todo lo demás externo.
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "media-src 'self' blob:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # En producción, exigir secreto fuerte (no arrancar con la clave de desarrollo).
    if settings.is_production and settings.secret_key == "dev-insegura-cambiar-en-produccion":
        raise RuntimeError("SECRET_KEY no configurada: define un secreto fuerte para producción.")
    try:
        seed()
    except Exception as e:  # no tumbar la app si Firestore aún no responde; queda en el log
        log.warning("No se pudo ejecutar el seed inicial: %s", e)
    yield


app = FastAPI(title="FeriaKL API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
    resp.headers["Content-Security-Policy"] = CSP
    if settings.is_production:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return resp


# CORS: por defecto solo mismo origen (la app se sirve desde el backend).
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/healthz")
def health():
    return {"app": "FeriaKL API", "status": "ok"}


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(mermas.router)
app.include_router(reports.router)

# El frontend se sirve desde el mismo servidor (mismo origen → sin CORS). Va al final.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
