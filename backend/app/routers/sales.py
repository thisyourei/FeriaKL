"""Ventas (POS). Crear una venta descuenta stock con una transacción de Firestore."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

from .. import schemas
from .. import db as store
from ..auth import get_current_user

router = APIRouter(prefix="/sales", tags=["ventas"])


@router.post("", response_model=schemas.SaleOut, status_code=201)
def create_sale(data: schemas.SaleCreate, user: dict = Depends(get_current_user)):
    # Agrupar cantidades por producto (defensa ante ítems repetidos).
    cantidades: dict[str, float] = {}
    for it in data.items:
        cantidades[it.product_id] = cantidades.get(it.product_id, 0) + it.cantidad

    transaction = store.db.transaction()
    resultado = {}

    @firestore.transactional
    def _registrar(txn):
        refs = {pid: store.col(store.PRODUCTS).document(pid) for pid in cantidades}
        snaps = {pid: ref.get(transaction=txn) for pid, ref in refs.items()}  # todas las lecturas primero

        items_out = []
        total = 0.0
        nuevos_stock = {}
        for pid, cant in cantidades.items():
            snap = snaps[pid]
            if not snap.exists:
                raise HTTPException(status_code=404, detail=f"Producto {pid} no existe")
            p = snap.to_dict()
            if p.get("stock", 0) < cant:
                raise HTTPException(status_code=409, detail=f"Stock insuficiente de {p.get('nombre','producto')}")
            subtotal = round(p["precio"] * cant)
            total += subtotal
            nuevos_stock[pid] = p["stock"] - cant
            items_out.append({"product_id": pid, "nombre": p["nombre"], "precio": p["precio"],
                              "cantidad": cant, "subtotal": subtotal})

        for pid, nuevo in nuevos_stock.items():  # luego las escrituras
            txn.update(refs[pid], {"stock": nuevo})
        sale_ref = store.col(store.SALES).document()
        doc = {"user_id": user["id"], "metodo_pago": data.metodo_pago, "total": total,
               "items": items_out, "created_at": datetime.now(timezone.utc)}
        txn.set(sale_ref, doc)
        doc["id"] = sale_ref.id
        resultado.update(doc)

    _registrar(transaction)
    return schemas.SaleOut(**resultado)


@router.get("", response_model=list[schemas.SaleOut])
def list_sales(limit: int = 50, _: dict = Depends(get_current_user)):
    limit = max(1, min(limit, 200))
    q = store.col(store.SALES).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
    return [schemas.SaleOut(**store.doc_to_dict(d)) for d in q.stream()]
