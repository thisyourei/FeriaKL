"""Esquemas Pydantic: validación de entrada y forma de las respuestas JSON.

Las validaciones (longitudes, formatos) son una capa de seguridad: rechazan datos
malformados o abusivos antes de tocar la base.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

PASSWORD_MIN = 8


# ---------- Auth / Usuarios ----------
class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN, max_length=128)
    role: str = Field(default="vendedor", pattern="^(admin|vendedor)$")


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    role: str | None = Field(default=None, pattern="^(admin|vendedor)$")
    active: bool | None = None
    password: str | None = Field(default=None, min_length=PASSWORD_MIN, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=128)


# ---------- Productos ----------
class ProductBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    barcode: str | None = Field(default=None, max_length=64)
    emoji: str = Field(default="📦", max_length=8)
    categoria: str = Field(default="General", max_length=40)
    unidad: str = Field(default="un", pattern="^(un|kg)$")
    precio: float = Field(ge=0, le=99_999_999)
    costo: float = Field(default=0, ge=0, le=99_999_999)
    stock: float = Field(default=0, ge=0, le=9_999_999)
    stock_min: float = Field(default=0, ge=0, le=9_999_999)
    activo: bool = True
    # Formato/presentación del producto: litros, kilos o pack, con su cantidad
    # (litros, kilos, o unidades que componen el pack). Opcional.
    medida_tipo: str | None = Field(default=None, pattern="^(litros|kilos|pack)$")
    medida_valor: float | None = Field(default=None, ge=0, le=9_999_999)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    barcode: str | None = Field(default=None, max_length=64)
    emoji: str | None = Field(default=None, max_length=8)
    categoria: str | None = Field(default=None, max_length=40)
    unidad: str | None = Field(default=None, pattern="^(un|kg)$")
    precio: float | None = Field(default=None, ge=0, le=99_999_999)
    costo: float | None = Field(default=None, ge=0, le=99_999_999)
    stock: float | None = Field(default=None, ge=0, le=9_999_999)
    stock_min: float | None = Field(default=None, ge=0, le=9_999_999)
    activo: bool | None = None
    medida_tipo: str | None = Field(default=None, pattern="^(litros|kilos|pack)$")
    medida_valor: float | None = Field(default=None, ge=0, le=9_999_999)


class ProductOut(ProductBase):
    id: str


# ---------- Ventas ----------
class SaleItemIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    cantidad: float = Field(gt=0, le=9_999_999)


class SaleCreate(BaseModel):
    metodo_pago: str = Field(pattern="^(efectivo|transferencia)$")
    items: list[SaleItemIn] = Field(min_length=1, max_length=200)
    pagado_con: float | None = Field(default=None, ge=0, le=99_999_999)  # efectivo recibido (para el vuelto)


class EmailReceipt(BaseModel):
    email: EmailStr


class SaleItemOut(BaseModel):
    product_id: str
    nombre: str
    precio: float
    cantidad: float
    subtotal: float


class SaleOut(BaseModel):
    id: str
    metodo_pago: str
    total: float
    created_at: datetime
    items: list[SaleItemOut]
    pagado_con: float | None = None
    anulada: bool = False


# ---------- Mermas ----------
class MermaCreate(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    cantidad: float = Field(gt=0, le=9_999_999)
    motivo: str = Field(default="", max_length=200)


class MermaOut(BaseModel):
    id: str
    product_id: str
    cantidad: float
    motivo: str
    perdida: float
    created_at: datetime
