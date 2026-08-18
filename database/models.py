from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,relationship
from sqlalchemy import ForeignKey 
from datetime import datetime

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
    ip_address:Mapped[str]=mapped_column(nullable=False)
    email:Mapped[str]
    is_verified:Mapped[bool]=mapped_column(default=False)
    is_blocked:Mapped[bool]=mapped_column(default=False)
    address:Mapped["Address"]=relationship("Address",back_populates="user")

class Address(Base):
    __tablename__="user_address"
    id:Mapped[int]=mapped_column(primary_key=True)
    house_no:Mapped[str]=mapped_column(nullable=False)
    street_name:Mapped[str]
    Landmark:Mapped[str]=mapped_column(nullable=True)
    Pincode:Mapped[int]=mapped_column(nullable=False)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    user:Mapped["User"]=relationship("User",back_populates="address")


class Product(Base):
    __tablename__="products"
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(nullable=False,unique=True,index=True)
    price:Mapped[float]=mapped_column(nullable=False)
    is_available:Mapped[bool]=mapped_column(default=False)

class Cart(Base):
    __tablename__="cart"
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    items:Mapped[list["CartItem"]]=relationship("CartItem",back_populates="cart")

class CartItem(Base):
    __tablename__="cart_items"
    id:Mapped[int]=mapped_column(primary_key=True)
    cart_id:Mapped[int]=mapped_column(ForeignKey("cart.id",ondelete="CASCADE"))
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id"))
    quantity:Mapped[float]
    cart:Mapped["Cart"]=relationship("Cart",back_populates="items")
    product:Mapped["Product"]=relationship("Product")


class Order(Base):
    __tablename__="orders"
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"))
    total_amount:Mapped[int]
    total_products:Mapped[int]
    status:Mapped[str]=mapped_column(default="pending")
    order_placed_at:Mapped[datetime]
    is_paid:Mapped[bool]=mapped_column(default=False)
        
class OrderItems(Base):
    __tablename__="order_items"
    id:Mapped[int]=mapped_column(primary_key=True)
    order_id:Mapped[int]=mapped_column(ForeignKey("orders.id",ondelete="CASCADE"))
    product_name:Mapped[str]
    product_qty:Mapped[int]
    price:Mapped[float]