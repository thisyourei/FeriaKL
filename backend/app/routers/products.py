"""Inventario: productos (Firestore)."""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud.firestore_v1 import FieldFilter

from .. import schemas
from .. import db as store
from ..auth import get_current_user, require_admin

router = APIRouter(prefix="/products", tags=["productos"])


def _by_barcode(code: str):
    q = store.col(store.PRODUCTS).where(filter=FieldFilter("barcode", "==", code)).limit(1)
    docs = list(q.stream())
    return store.doc_to_dict(docs[0]) if docs else None


@router.get("", response_model=list[schemas.ProductOut])
def list_products(_: dict = Depends(get_current_user)):
    items = [store.doc_to_dict(d) for d in store.col(store.PRODUCTS).stream()]
    items.sort(key=lambda p: p.get("nombre", "").lower())
    return [schemas.ProductOut(**p) for p in items]


@router.get("/barcode/{code}", response_model=schemas.ProductOut)
def get_by_barcode(code: str, _: dict = Depends(get_current_user)):
    p = _by_barcode(code)
    if not p:
        raise HTTPException(status_code=404, detail="No hay un producto con ese código de barra")
    return schemas.ProductOut(**p)


@router.post("", response_model=schemas.ProductOut, status_code=201)
def create_product(data: schemas.ProductCreate, _: dict = Depends(require_admin)):
    payload = data.model_dump()
    if payload.get("barcode"):
        existe = _by_barcode(payload["barcode"])
        if existe:
            raise HTTPException(status_code=400, detail=f"El código {payload['barcode']} ya está asignado a {existe['nombre']}")
    ref = store.col(store.PRODUCTS).document()
    ref.set(payload)
    payload["id"] = ref.id
    return schemas.ProductOut(**payload)


@router.patch("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: str, data: schemas.ProductUpdate, _: dict = Depends(require_admin)):
    ref = store.col(store.PRODUCTS).document(product_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    cambios = data.model_dump(exclude_unset=True)
    if cambios.get("barcode"):
        existe = _by_barcode(cambios["barcode"])
        if existe and existe["id"] != product_id:
            raise HTTPException(status_code=400, detail=f"El código {cambios['barcode']} ya está asignado a {existe['nombre']}")
    if cambios:
        ref.update(cambios)
    return schemas.ProductOut(**store.doc_to_dict(ref.get()))
