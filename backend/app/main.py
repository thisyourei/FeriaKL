"""Punto de entrada de la API FeriaKL (FastAPI)."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, engine, SessionLocal
from .seed import seed
from .routers import auth, products, sales, mermas, reports

# Carpeta con el frontend (index.html, manifest.json, sw.js, vendor/).
# En producción se fija con FRONTEND_DIR; en local se autodetecta (raíz del repo).
FRONTEND_DIR = Path(settings.frontend_dir) if settings.frontend_dir else Path(__file__).resolve().parent.parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas y siembra datos iniciales al arrancar.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="FeriaKL API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
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

# El frontend se sirve desde el mismo servidor (misma URL que el API → sin CORS).
# Debe ir AL FINAL: las rutas del API ya están registradas y tienen prioridad.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
