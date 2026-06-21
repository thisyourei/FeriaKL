"""Esquemas Pydantic: validación de entrada y forma de las respuestas JSON."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field


# ---------- Auth / Usuarios ----------
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str = Field(min_length=6)
    role: str = "vendedor"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    name: str
    role: str
    active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Productos ----------
class ProductBase(BaseModel):
    nombre: str
    barcode: str | None = None
    emoji: str = "📦"
    categoria: str = "General"
    unidad: str = "un"
    precio: float
    costo: float = 0
    stock: float = 0
    stock_min: float = 0
    activo: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    nombre: str | None = None
    barcode: str | None = None
    emoji: str | None = None
    categoria: str | None = None
    unidad: str | None = None
    precio: float | None = None
    costo: float | None = None
    stock: float | None = None
    stock_min: float | None = None
    activo: bool | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Ventas ----------
class SaleItemIn(BaseModel):
    product_id: int
    cantidad: float


class SaleCreate(BaseModel):
    metodo_pago: str  # efectivo | transferencia | fiado
    items: list[SaleItemIn]
    customer_id: int | None = None  # requerido si metodo_pago == "fiado"


class SaleItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    nombre: str
    precio: float
    cantidad: float
    subtotal: float


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    metodo_pago: str
    total: float
    customer_id: int | None
    created_at: datetime
    items: list[SaleItemOut]


# ---------- Clientes / Fiado ----------
class CustomerCreate(BaseModel):
    nombre: str
    telefono: str = ""


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    telefono: str
    deuda: float = 0  # calculado: ventas fiado - abonos


class PaymentCreate(BaseModel):
    monto: float = Field(gt=0)


# ---------- Mermas ----------
class MermaCreate(BaseModel):
    product_id: int
    cantidad: float
    motivo: str = ""


class MermaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    cantidad: float
    motivo: str
    perdida: float
    created_at: datetime
