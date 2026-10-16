from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,relationship
from sqlalchemy import ForeignKey  , DateTime , Enum as sqlenum
from datetime import datetime

from enum import Enum

class OrderStatus(str,Enum):
    PENDING='pending'
    OUT_FOR_DELIVERY='out_for_delivery'
    DELIVERED='delivered'
    CANCELLED=' cancelled'

class PaymentMethod(str,Enum):
    COD='cod'
    
class Base(DeclarativeBase):
    pass

class Admin(Base):
    __tablename__="admin"
    username:Mapped[str]=mapped_column(primary_key=True)
    password:Mapped[str]
    email:Mapped[str]

class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    full_name:Mapped[str]
    username:Mapped[str]=mapped_column(unique=True,nullable=False)
    password:Mapped[str]
    email:Mapped[str]
    is_verified:Mapped[bool]=mapped_column(default=False)
    is_blocked:Mapped[bool]=mapped_column(default=False)
    is_account_closed:Mapped[bool]=mapped_column(default=False)
    address:Mapped["Address"]=relationship("Address",back_populates="user")

class Address(Base):
    __tablename__="user_address"
    id:Mapped[int]=mapped_column(primary_key=True)
    house_no:Mapped[str]=mapped_column(nullable=False)
    street_name:Mapped[str]
    landmark:Mapped[str]=mapped_column(nullable=True)
    postal_code:Mapped[int]=mapped_column(nullable=False)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    user:Mapped["User"]=relationship("User",back_populates="address")


class Product(Base):
    __tablename__="products"
    id:Mapped[int]=mapped_column(primary_key=True)
    image:Mapped[str]
    unit:Mapped[str]
    quantity:Mapped[float]
    name:Mapped[str]=mapped_column(nullable=False,unique=True,index=True)
    price:Mapped[float]=mapped_column(nullable=False)
    is_available:Mapped[bool]=mapped_column(default=False)

    cartitem:Mapped["CartItem"]=relationship("CartItem",back_populates="product")
class Cart(Base):
    __tablename__="cart"
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),unique=True)
    
    items:Mapped[list["CartItem"]]=relationship("CartItem",back_populates="cart",cascade="all,delete-orphan")

class CartItem(Base):
    __tablename__="cart_items"
    id:Mapped[int]=mapped_column(primary_key=True)
    cart_id:Mapped[int]=mapped_column(ForeignKey("cart.id",ondelete="CASCADE"))
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id"))
    quantity:Mapped[float]
    
    cart:Mapped["Cart"]=relationship("Cart",back_populates="items")
    
    product:Mapped["Product"]=relationship("Product", back_populates="cartitem")


class Order(Base):
    __tablename__="orders"
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"))
    total_amount:Mapped[float]
    total_products:Mapped[int]
    status:Mapped[OrderStatus]=mapped_column(sqlenum(OrderStatus),default=OrderStatus.PENDING)
    order_placed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    is_paid:Mapped[bool]=mapped_column(default=False)
    payment_method:Mapped[PaymentMethod]=mapped_column( sqlenum(PaymentMethod), default=PaymentMethod.COD)
    items:Mapped[list["OrderItems"]]=relationship("OrderItems",back_populates="order")
        
class OrderItems(Base):
    __tablename__="order_items"
    id:Mapped[int]=mapped_column(primary_key=True)
    order_id:Mapped[int]=mapped_column(ForeignKey("orders.id",ondelete="CASCADE"))
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id", ondelete="SET NULL"),nullable=True)
    price:Mapped[float]
    product_qty:Mapped[float]
    total:Mapped[float]
    order:Mapped["Order"]=relationship("Order",back_populates="items")