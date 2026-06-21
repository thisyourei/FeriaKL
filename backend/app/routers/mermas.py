"""Mermas: registro de pérdidas (descuenta stock y valoriza al costo)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from .. import schemas
from .. import db as store
from ..auth import get_current_user

router = APIRouter(prefix="/mermas", tags=["mermas"])


@router.post("", response_model=schemas.MermaOut, status_code=201)
def create_merma(data: schemas.MermaCreate, user: dict = Depends(get_current_user)):
    transaction = store.db.transaction()
    resultado = {}

    @firestore.transactional
    def _registrar(txn):
        ref = store.col(store.PRODUCTS).document(data.product_id)
        snap = ref.get(transaction=txn)
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        p = snap.to_dict()
        nuevo_stock = max(0, p.get("stock", 0) - data.cantidad)
        txn.update(ref, {"stock": nuevo_stock})
        merma_ref = store.col(store.MERMAS).document()
        doc = {"product_id": data.product_id, "user_id": user["id"], "cantidad": data.cantidad,
               "motivo": data.motivo, "perdida": round(p.get("costo", 0) * data.cantidad),
               "created_at": datetime.now(timezone.utc)}
        txn.set(merma_ref, doc)
        doc["id"] = merma_ref.id
        resultado.update(doc)

    _registrar(transaction)
    return schemas.MermaOut(**resultado)


@router.get("", response_model=list[schemas.MermaOut])
def list_mermas(limit: int = 50, _: dict = Depends(get_current_user)):
    limit = max(1, min(limit, 200))
    q = store.col(store.MERMAS).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
    return [schemas.MermaOut(**store.doc_to_dict(d)) for d in q.stream()]
