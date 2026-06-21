"""Clientes y fiado (deudas + abonos)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/customers", tags=["clientes / fiado"])


def _deuda(db: Session, customer_id: int) -> float:
    ventas = db.scalar(
        select(func.coalesce(func.sum(models.Sale.total), 0))
        .where(models.Sale.customer_id == customer_id, models.Sale.metodo_pago == "fiado")
    )
    abonos = db.scalar(
        select(func.coalesce(func.sum(models.Payment.monto), 0))
        .where(models.Payment.customer_id == customer_id)
    )
    return float(ventas) - float(abonos)


@router.get("", response_model=list[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    customers = db.scalars(select(models.Customer).order_by(models.Customer.nombre)).all()
    out = []
    for c in customers:
        item = schemas.CustomerOut.model_validate(c)
        item.deuda = _deuda(db, c.id)
        out.append(item)
    return out


@router.post("", response_model=schemas.CustomerOut, status_code=201)
def create_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    customer = models.Customer(**data.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{customer_id}/payments", response_model=schemas.CustomerOut, status_code=201)
def add_payment(customer_id: int, data: schemas.PaymentCreate, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    customer = db.get(models.Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.add(models.Payment(customer_id=customer_id, monto=data.monto))
    db.commit()
    out = schemas.CustomerOut.model_validate(customer)
    out.deuda = _deuda(db, customer_id)
    return out
