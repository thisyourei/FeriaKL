"""Login, gestión de usuarios y cambio de contraseña (login por persona, con roles)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from google.cloud.firestore_v1 import FieldFilter

from .. import schemas
from .. import db as store
from ..auth import (
    hash_password, verify_password, create_access_token, get_current_user, require_admin,
    check_login_rate, register_login_fail, clear_login_fails,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _find_user_by_email(email: str):
    q = store.col(store.USERS).where(filter=FieldFilter("email", "==", email.lower())).limit(1)
    docs = list(q.stream())
    return store.doc_to_dict(docs[0]) if docs else None


def _public(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "name": user["name"],
            "role": user["role"], "active": user["active"]}


@router.post("/login", response_model=schemas.Token)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    email = form.username.strip().lower()
    check_login_rate(request, email)
    user = _find_user_by_email(email)
    if not user or not user.get("active") or not verify_password(form.password, user.get("hashed_password", "")):
        register_login_fail(request, email)
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    clear_login_fails(request, email)
    token = create_access_token(user["id"])
    return schemas.Token(access_token=token, user=schemas.UserOut(**_public(user)))


@router.get("/me", response_model=schemas.UserOut)
def me(user: dict = Depends(get_current_user)):
    return schemas.UserOut(**_public(user))


@router.post("/change-password", status_code=204)
def change_password(data: schemas.ChangePassword, user: dict = Depends(get_current_user)):
    if not verify_password(data.current_password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
    store.col(store.USERS).document(user["id"]).update({"hashed_password": hash_password(data.new_password)})
    return None


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(_: dict = Depends(require_admin)):
    users = [store.doc_to_dict(d) for d in store.col(store.USERS).stream()]
    return [schemas.UserOut(**_public(u)) for u in users]


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(data: schemas.UserCreate, _: dict = Depends(require_admin)):
    if _find_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")
    doc = {
        "email": data.email.lower(),
        "name": data.name.strip(),
        "role": data.role,
        "active": True,
        "hashed_password": hash_password(data.password),
        "created_at": datetime.now(timezone.utc),
    }
    ref = store.col(store.USERS).document()
    ref.set(doc)
    doc["id"] = ref.id
    return schemas.UserOut(**_public(doc))
