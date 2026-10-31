"""Mô hình ORM (SQLAlchemy 2.0) cho dữ liệu quan hệ: đơn hàng, dòng hàng, lịch sử trạng thái, email
nhận tin. Mỗi lớp Python ánh xạ tới một bảng SQLite; quan hệ một–nhiều giữa đơn hàng và dòng hàng /
lịch sử được khai báo bằng `relationship`, nên tầng lưu trữ (`OrderStore`) thao tác bằng đối tượng
thay vì viết câu lệnh SQL.

Tên bảng và cột giữ đúng như lược đồ của bản trước (viết SQL tay), nên tệp SQLite đã có vẫn mở được.

  orders(id PK, created_at, status, khách hàng…, payment, subtotal, shipping, total, coupon, discount)
  order_items(order_id FK → orders ON DELETE CASCADE, line_no, sku, size, name, price, qty)
  order_history(order_id FK → orders ON DELETE CASCADE, seq, status, at)
  newsletter(email PK, created_at)
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("idx_orders_status", "status"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)  # DH-yymmdd-xxxx
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # new | shipping | done | cancelled
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_phone: Mapped[str] = mapped_column(String, nullable=False)
    customer_email: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    customer_address: Mapped[str] = mapped_column(String, nullable=False)
    customer_note: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    payment: Mapped[str] = mapped_column(String, nullable=False)  # cod | bank
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    coupon: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    discount: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # Một đơn — nhiều dòng hàng / nhiều mốc trạng thái. passive_deletes: để CSDL tự xóa theo nhờ
    # khóa ngoại ON DELETE CASCADE (ràng buộc nằm ở CSDL, đúng cả khi xóa bằng công cụ khác).
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", order_by="OrderItem.line_no", cascade="all, delete-orphan", passive_deletes=True
    )
    history: Mapped[list[OrderHistory]] = relationship(
        back_populates="order", order_by="OrderHistory.seq", cascade="all, delete-orphan", passive_deletes=True
    )

    def to_dict(self) -> dict:
        """Dạng dữ liệu mà tầng nghiệp vụ (core/orders.py) và API dùng."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "status": self.status,
            "customer": {
                "name": self.customer_name,
                "phone": self.customer_phone,
                "email": self.customer_email,
                "address": self.customer_address,
                "note": self.customer_note,
            },
            "payment": self.payment,
            "items": [it.to_dict() for it in self.items],
            "subtotal": self.subtotal,
            "shipping": self.shipping,
            "total": self.total,
            "coupon": self.coupon,
            "discount": self.discount,
            "history": [h.to_dict() for h in self.history],
        }

    @classmethod
    def from_dict(cls, order: dict) -> Order:
        c = order["customer"]
        return cls(
            id=order["id"],
            created_at=order["created_at"],
            status=order["status"],
            customer_name=c["name"],
            customer_phone=c["phone"],
            customer_email=c.get("email", ""),
            customer_address=c["address"],
            customer_note=c.get("note", ""),
            payment=order["payment"],
            subtotal=order["subtotal"],
            shipping=order["shipping"],
            total=order["total"],
            coupon=order.get("coupon", ""),
            discount=order.get("discount", 0),
            items=[
                OrderItem(line_no=i, sku=it["sku"], size=it["size"], name=it["name"], price=it["price"], qty=it["qty"])
                for i, it in enumerate(order["items"], start=1)
            ],
            history=[OrderHistory(seq=i, status=h["status"], at=h["at"]) for i, h in enumerate(order["history"], start=1)],
        )


class OrderItem(Base):
    """Dòng hàng — tên và giá được CHỤP LẠI lúc đặt (đổi giá sau này không làm sai đơn cũ)."""

    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    line_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")

    def to_dict(self) -> dict:
        return {"sku": self.sku, "size": self.size, "name": self.name, "price": self.price, "qty": self.qty}


class OrderHistory(Base):
    __tablename__ = "order_history"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    at: Mapped[str] = mapped_column(String, nullable=False)

    order: Mapped[Order] = relationship(back_populates="history")

    def to_dict(self) -> dict:
        return {"status": self.status, "at": self.at}


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
