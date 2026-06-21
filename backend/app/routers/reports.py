"""Reportes: resumen del día, ventas por día y productos más vendidos.

Firestore no agrega/agrupa del lado servidor, así que traemos los documentos
recientes y agregamos en Python (suficiente para el volumen de un puesto).
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

from .. import db as store
from ..auth import get_current_user

router = APIRouter(prefix="/reports", tags=["reportes"])


@router.get("/summary")
def summary(_: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    ventas_hoy = 0.0
    num_ventas = 0
    q = store.col(store.SALES).where(filter=FieldFilter("created_at", ">=", start))
    for d in q.stream():
        s = d.to_dict()
        ventas_hoy += s.get("total", 0)
        num_ventas += 1

    productos = [d.to_dict() for d in store.col(store.PRODUCTS).stream()]
    activos = [p for p in productos if p.get("activo", True)]
    stock_bajo = sum(1 for p in activos if p.get("stock", 0) <= p.get("stock_min", 0))

    return {
        "ventas_hoy": float(ventas_hoy),
        "num_ventas": int(num_ventas),
        "ticket_promedio": float(ventas_hoy) / num_ventas if num_ventas else 0,
        "productos_activos": len(activos),
        "stock_bajo": stock_bajo,
    }


@router.get("/sales-by-day")
def sales_by_day(days: int = 7, _: dict = Depends(get_current_user)):
    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    por_dia: dict[str, float] = defaultdict(float)
    q = store.col(store.SALES).where(filter=FieldFilter("created_at", ">=", since))
    for d in q.stream():
        s = d.to_dict()
        fecha = s["created_at"].astimezone(timezone.utc).date().isoformat()
        por_dia[fecha] += s.get("total", 0)
    return [{"fecha": f, "total": float(t)} for f, t in sorted(por_dia.items())]


@router.get("/top-products")
def top_products(limit: int = 5, _: dict = Depends(get_current_user)):
    limit = max(1, min(limit, 50))
    acum: dict[str, dict] = {}
    # Agrega sobre las ventas recientes (hasta 500 docs) para no recorrer todo el historial.
    q = store.col(store.SALES).order_by("created_at", direction=firestore.Query.DESCENDING).limit(500)
    for d in q.stream():
        for it in d.to_dict().get("items", []):
            a = acum.setdefault(it["nombre"], {"nombre": it["nombre"], "cantidad": 0.0, "ingresos": 0.0})
            a["cantidad"] += it.get("cantidad", 0)
            a["ingresos"] += it.get("subtotal", 0)
    top = sorted(acum.values(), key=lambda x: x["ingresos"], reverse=True)[:limit]
    return [{"nombre": x["nombre"], "cantidad": float(x["cantidad"]), "ingresos": float(x["ingresos"])} for x in top]
