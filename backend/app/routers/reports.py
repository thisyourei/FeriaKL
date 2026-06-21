"""Reportes: resumen del día, ventas por día y productos más vendidos."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .. import models
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/reports", tags=["reportes"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    ventas_hoy = db.scalar(
        select(func.coalesce(func.sum(models.Sale.total), 0)).where(models.Sale.created_at >= start)
    )
    num_ventas = db.scalar(select(func.count(models.Sale.id)).where(models.Sale.created_at >= start))
    productos = db.scalars(select(models.Product).where(models.Product.activo == True)).all()  # noqa: E712
    stock_bajo = sum(1 for p in productos if p.stock <= p.stock_min)

    return {
        "ventas_hoy": float(ventas_hoy),
        "num_ventas": int(num_ventas),
        "ticket_promedio": float(ventas_hoy) / num_ventas if num_ventas else 0,
        "productos_activos": len(productos),
        "stock_bajo": stock_bajo,
    }


@router.get("/sales-by-day")
def sales_by_day(days: int = 7, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(func.date(models.Sale.created_at), func.sum(models.Sale.total))
        .where(models.Sale.created_at >= since)
        .group_by(func.date(models.Sale.created_at))
        .order_by(func.date(models.Sale.created_at))
    ).all()
    return [{"fecha": str(r[0]), "total": float(r[1])} for r in rows]


@router.get("/top-products")
def top_products(limit: int = 5, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    rows = db.execute(
        select(
            models.SaleItem.nombre,
            func.sum(models.SaleItem.cantidad),
            func.sum(models.SaleItem.subtotal),
        )
        .group_by(models.SaleItem.nombre)
        .order_by(func.sum(models.SaleItem.subtotal).desc())
        .limit(limit)
    ).all()
    return [{"nombre": r[0], "cantidad": float(r[1]), "ingresos": float(r[2])} for r in rows]
