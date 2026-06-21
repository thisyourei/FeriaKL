"""Login y gestión de usuarios (login por persona, con roles)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token, get_current_user, require_admin
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm usa "username"; aquí es el email.
    user = db.scalar(select(models.User).where(models.User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password) or not user.active:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    token = create_access_token(user.id)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    return db.scalars(select(models.User)).all()


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(data: schemas.UserCreate, db: Session = Depends(get_db), _: models.User = Depends(require_admin)):
    if db.scalar(select(models.User).where(models.User.email == data.email)):
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese correo")
    user = models.User(
        email=data.email, name=data.name, role=data.role,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
