"""Mermas: registro de pérdidas (descuenta stock y valoriza al costo)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/mermas", tags=["mermas"])


@router.post("", response_model=schemas.MermaOut, status_code=201)
def create_merma(data: schemas.MermaCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    product = db.get(models.Product, data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if data.cantidad <= 0:
        raise HTTPException(status_code=400, detail="Cantidad inválida")
    merma = models.Merma(
        product_id=product.id, user_id=user.id, cantidad=data.cantidad,
        motivo=data.motivo, perdida=round(product.costo * data.cantidad),
    )
    product.stock = max(0, product.stock - data.cantidad)
    db.add(merma)
    db.commit()
    db.refresh(merma)
    return merma


@router.get("", response_model=list[schemas.MermaOut])
def list_mermas(limit: int = 50, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.scalars(select(models.Merma).order_by(desc(models.Merma.created_at)).limit(limit)).all()
