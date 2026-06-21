"""Autenticación: hash de contraseñas, JWT, dependencias de seguridad y anti-fuerza-bruta."""
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import bcrypt

from .config import settings
from . import db as store

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------- Contraseñas ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------- JWT ----------
def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    cred_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
    except (JWTError, ValueError):
        raise cred_error
    if not user_id:
        raise cred_error
    snap = store.col(store.USERS).document(user_id).get()
    user = store.doc_to_dict(snap)
    if user is None or not user.get("active", False):
        raise cred_error
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    return user


# ---------- Anti-fuerza-bruta (rate limit de login en memoria) ----------
# Nota: en memoria por instancia. Para tráfico pequeño es suficiente y eleva la barrera.
_FAILS: dict[str, list[float]] = {}
_MAX_FAILS = 8
_WINDOW = 300  # 5 minutos


def _key(request: Request, email: str) -> str:
    ip = request.client.host if request.client else "?"
    return f"{ip}:{email.lower()}"


def check_login_rate(request: Request, email: str) -> None:
    now = time.time()
    k = _key(request, email)
    intentos = [t for t in _FAILS.get(k, []) if now - t < _WINDOW]
    _FAILS[k] = intentos
    if len(intentos) >= _MAX_FAILS:
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.")


def register_login_fail(request: Request, email: str) -> None:
    _FAILS.setdefault(_key(request, email), []).append(time.time())


def clear_login_fails(request: Request, email: str) -> None:
    _FAILS.pop(_key(request, email), None)
