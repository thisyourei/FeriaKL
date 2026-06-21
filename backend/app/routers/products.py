"""Inventario: productos."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import models, schemas
from ..auth import get_current_user, require_admin
from ..database import get_db

router = APIRouter(prefix="/products", tags=["productos"])


@router.get("", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return db.scalars(select(models.Product).order_by(models.Product.nombre)).all()


@router.get("/barcode/{code}", response_model=schemas.ProductOut)
def get_by_barcode(code: str, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    product = db.scalar(select(models.Product).where(models.Product.barcode == code))
    if not product:
        raise HTTPException(status_code=404, detail="No hay un producto con ese código de barra")
    return product


@router.post("", response_model=schemas.ProductOut, status_code=201)
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    if data.barcode:
        existe = db.scalar(select(models.Product).where(models.Product.barcode == data.barcode))
        if existe:
            raise HTTPException(status_code=400, detail=f"El código {data.barcode} ya está asignado a {existe.nombre}")
    product = models.Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product
