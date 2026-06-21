"""Ventas (POS). Crear una venta descuenta stock con una transacción de Firestore."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter

from .. import schemas
from .. import db as store
from ..auth import get_current_user, require_admin

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
def list_sales(limit: int = 50, incluir_anuladas: bool = False, _: dict = Depends(get_current_user)):
    # Las anuladas no se borran de la BD: se marcan y se filtran (salvo que se pidan explícitamente).
    limit = max(1, min(limit, 200))
    tope = limit if incluir_anuladas else min(limit * 3 + 20, 500)
    q = store.col(store.SALES).order_by("created_at", direction=firestore.Query.DESCENDING).limit(tope)
    salidas = []
    for d in q.stream():
        s = store.doc_to_dict(d)
        if not incluir_anuladas and s.get("anulada"):
            continue
        salidas.append(schemas.SaleOut(**s))
        if len(salidas) >= limit:
            break
    return salidas


@router.delete("/{sale_id}", response_model=schemas.SaleOut)
def annul_sale(sale_id: str, admin: dict = Depends(require_admin)):
    """Anula una venta (solo admin): la marca como anulada y devuelve el stock.
    El documento permanece en la BD para auditoría; queda visible como 'Eliminada'."""
    transaction = store.db.transaction()
    resultado = {}

    @firestore.transactional
    def _anular(txn):
        sale_ref = store.col(store.SALES).document(sale_id)
        snap = sale_ref.get(transaction=txn)
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        sale = snap.to_dict()
        if sale.get("anulada"):
            raise HTTPException(status_code=400, detail="La venta ya está anulada")

        # Agrupar cantidades por producto y leer (todas las lecturas antes de escribir).
        cantidades: dict[str, float] = {}
        for it in sale.get("items", []):
            cantidades[it["product_id"]] = cantidades.get(it["product_id"], 0) + it.get("cantidad", 0)
        refs = {pid: store.col(store.PRODUCTS).document(pid) for pid in cantidades}
        snaps = {pid: ref.get(transaction=txn) for pid, ref in refs.items()}

        # Devolver stock a los productos que aún existen (si alguno fue eliminado, se omite).
        for pid, cant in cantidades.items():
            ps = snaps[pid]
            if ps.exists:
                txn.update(refs[pid], {"stock": ps.to_dict().get("stock", 0) + cant})
        txn.update(sale_ref, {
            "anulada": True,
            "anulada_at": datetime.now(timezone.utc),
            "anulada_by": admin["id"],
        })
        sale["id"] = sale_id
        sale["anulada"] = True
        resultado.update(sale)

    _anular(transaction)
    return schemas.SaleOut(**resultado)
