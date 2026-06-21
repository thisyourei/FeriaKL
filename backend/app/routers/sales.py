"""Ventas (punto de venta). Crear una venta descuenta stock de forma transaccional."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/sales", tags=["ventas"])


@router.post("", response_model=schemas.SaleOut, status_code=201)
def create_sale(data: schemas.SaleCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if not data.items:
        raise HTTPException(status_code=400, detail="La venta no tiene productos")
    if data.metodo_pago == "fiado" and not data.customer_id:
        raise HTTPException(status_code=400, detail="Una venta fiada requiere un cliente")

    sale = models.Sale(user_id=user.id, metodo_pago=data.metodo_pago, total=0, customer_id=data.customer_id)
    total = 0.0
    for item in data.items:
        product = db.get(models.Product, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no existe")
        if item.cantidad <= 0:
            raise HTTPException(status_code=400, detail="Cantidad inválida")
        if product.stock < item.cantidad:
            raise HTTPException(status_code=409, detail=f"Stock insuficiente de {product.nombre}")
        subtotal = round(product.precio * item.cantidad)
        total += subtotal
        product.stock -= item.cantidad
        sale.items.append(models.SaleItem(
            product_id=product.id, nombre=product.nombre,
            precio=product.precio, cantidad=item.cantidad, subtotal=subtotal,
        ))
    sale.total = total
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@router.get("", response_model=list[schemas.SaleOut])
def list_sales(limit: int = 50, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.scalars(select(models.Sale).order_by(desc(models.Sale.created_at)).limit(limit)).all()
