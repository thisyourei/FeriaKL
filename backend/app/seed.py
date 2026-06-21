"""Datos iniciales en Firestore: usuario admin + productos de ejemplo si están vacíos."""
import logging
from datetime import datetime, timezone

from . import db as store
from .auth import hash_password
from .config import settings

log = logging.getLogger("feriakl.seed")

# Productos de limpieza con códigos de barra de muestra (EAN-13).
PRODUCTOS = [
    ("Detergente Omo 3kg", "🧴", "Ropa", "un", 8990, 6200, 12, 4, "7801234500017"),
    ("Cloro Clorox 1L", "🧴", "Desinfección", "un", 1690, 1050, 30, 10, "7801234500024"),
    ("Lavalozas Quix 750ml", "🧽", "Cocina", "un", 1990, 1280, 20, 6, "7801234500031"),
    ("Limpiapisos Lysoform 900ml", "🧹", "Pisos", "un", 2490, 1600, 15, 5, "7801234500048"),
    ("Papel higiénico Elite 4u", "🧻", "Papel", "un", 2290, 1500, 25, 8, "7801234500055"),
    ("Toalla Nova 2u", "🧻", "Papel", "un", 2790, 1850, 18, 6, "7801234500062"),
    ("Esponja multiuso 3u", "🧽", "Cocina", "un", 990, 520, 40, 12, "7801234500079"),
    ("Desinfectante Lysol 360ml", "🧴", "Desinfección", "un", 4490, 3100, 8, 4, "7801234500086"),
    ("Jabón líquido Ballerina 750ml", "🧼", "Baño", "un", 2190, 1400, 14, 5, "7801234500093"),
    ("Bolsa de basura 50L 10u", "🗑️", "Hogar", "un", 1590, 980, 35, 10, "7801234500109"),
    ("Lustramuebles Blem 360ml", "✨", "Hogar", "un", 3290, 2200, 9, 4, "7801234500116"),
    ("Limpiavidrios Cif 500ml", "🪟", "Vidrios", "un", 2690, 1750, 11, 4, "7801234500123"),
]


def _coleccion_vacia(nombre: str) -> bool:
    return not list(store.col(nombre).limit(1).stream())


def seed() -> None:
    # --- Admin ---
    if _coleccion_vacia(store.USERS):
        password = settings.seed_admin_password
        if not password:
            if settings.is_production:
                log.warning("No se creó admin: define SEED_ADMIN_PASSWORD (fuerte) para crear el primer usuario.")
                password = None
            else:
                password = "feria1234"  # solo desarrollo local
                log.warning("Admin de desarrollo creado con contraseña por defecto. NO usar en producción.")
        if password:
            store.col(store.USERS).document().set({
                "email": settings.seed_admin_email.lower(),
                "name": settings.seed_admin_name,
                "role": "admin",
                "active": True,
                "hashed_password": hash_password(password),
                "created_at": datetime.now(timezone.utc),
            })

    # --- Productos de ejemplo ---
    if settings.seed_demo_products and _coleccion_vacia(store.PRODUCTS):
        for nombre, emoji, cat, unidad, precio, costo, stock, smin, barcode in PRODUCTOS:
            store.col(store.PRODUCTS).document().set({
                "nombre": nombre, "emoji": emoji, "categoria": cat, "unidad": unidad,
                "precio": precio, "costo": costo, "stock": stock, "stock_min": smin,
                "barcode": barcode, "activo": True,
            })
