"""Modelos de datos (tablas) de FeriaKL."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="vendedor")  # admin | vendedor
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    barcode: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)  # código de barra (EAN/UPC)
    emoji: Mapped[str] = mapped_column(String(8), default="📦")
    categoria: Mapped[str] = mapped_column(String(40), default="General")
    unidad: Mapped[str] = mapped_column(String(8), default="un")  # kg | un
    precio: Mapped[float] = mapped_column(Float)   # precio de venta
    costo: Mapped[float] = mapped_column(Float, default=0)
    stock: Mapped[float] = mapped_column(Float, default=0)
    stock_min: Mapped[float] = mapped_column(Float, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Customer(Base):
    """Cliente con fiado (deuda)."""
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    telefono: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    payments: Mapped[list["Payment"]] = relationship(back_populates="customer")
    sales: Mapped[list["Sale"]] = relationship(back_populates="customer")


class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    metodo_pago: Mapped[str] = mapped_column(String(20))  # efectivo | transferencia | fiado
    total: Mapped[float] = mapped_column(Float)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)

    items: Mapped[list["SaleItem"]] = relationship(back_populates="sale", cascade="all, delete-orphan")
    customer: Mapped["Customer | None"] = relationship(back_populates="sales")


class SaleItem(Base):
    __tablename__ = "sale_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    nombre: Mapped[str] = mapped_column(String(120))   # snapshot del nombre al momento de venta
    precio: Mapped[float] = mapped_column(Float)        # snapshot del precio unitario
    cantidad: Mapped[float] = mapped_column(Float)
    subtotal: Mapped[float] = mapped_column(Float)

    sale: Mapped["Sale"] = relationship(back_populates="items")


class Payment(Base):
    """Abono de un cliente a su deuda (fiado)."""
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    monto: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    customer: Mapped["Customer"] = relationship(back_populates="payments")


class Merma(Base):
    """Pérdida de producto (dañado, vencido, no vendido)."""
    __tablename__ = "mermas"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    cantidad: Mapped[float] = mapped_column(Float)
    motivo: Mapped[str] = mapped_column(Text, default="")
    perdida: Mapped[float] = mapped_column(Float)  # pérdida valorizada al costo
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, index=True)
