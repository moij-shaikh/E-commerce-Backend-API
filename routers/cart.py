from fastapi import APIRouter ,HTTPException , status, Depends , Form
from database.database import get_db
from database.models import Product, Cart , CartItem
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from services.auth import get_current_user

router=APIRouter(tags=["Cart"])

@router.get("/cart")
async def cart__get_cart(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get('sub'))
    db_cart= await db.scalar(select(Cart).where(Cart.user_id ==user_id).options(selectinload(Cart.items).selectinload(CartItem.product)))
    if not db_cart or not db_cart.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No product inside cart.")
    display_list={
        "user_id":db_cart.user_id,
        "items":[
            {
                "id":i.id,
                "product_id":i.product_id,
                "name":i.product.name,
                "quantity":i.quantity,
                "price":i.product.price,
                "unit":i.product.unit,
                "subtotal":i.product.price * i.quantity                
            }
            for i in db_cart.items 
        ],
        "total_amount":sum(
            i.product.price * i.quantity
            for i in db_cart.items
        )
    }
    return display_list
    

@router.post("/cart")
async def cart__new(product_id:int=Form(gt=0), product_qty:int=Form(gt=0),payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get("sub"))
    db_product= await db.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Product Found. ")
    if not db_product.is_available:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Product is not available. ")
        
    db_cart=await db.scalar(select(Cart).where(Cart.user_id == user_id))
    if not db_cart:
        db_cart= Cart(user_id=user_id)
        db.add(db_cart)
        await db.flush()
    db_cart_item= await db.scalar(select(CartItem).join(Cart).where(Cart.user_id == user_id, CartItem.product_id == product_id))
    if not db_cart_item:
        new_cart_item=CartItem(
            cart_id=db_cart.id,
            product_id=db_product.id,
            quantity=product_qty
        )
        db.add(new_cart_item)
    else:
        if product_qty > db_product.quantity:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested qty exceeds available stock. ")
        db_cart_item.quantity = product_qty
    try:
        await db.commit()
        return{
            "message":"New item added."
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Internal Server error. ")
    
@router.delete("/cart")
async def cart__delete(payload:dict=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get("sub"))
    db_cart= await db.scalar(select(Cart).where(Cart.user_id ==user_id))
    try:
        await db.delete(db_cart)
        await db.commit()
        return {
            "message":"Cart is deleted. "
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Internal Server error. ")
        

@router.delete("/cart/items/{id}")
async def cart__delete(id:int,payload:dict=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get("sub"))
    db_cart_item= await db.scalar(select(CartItem).join(Cart).where(Cart.user_id ==user_id, CartItem.id == id))
    if not db_cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found."  )
    try:
        await db.delete(db_cart_item)
        await db.commit()
        
        return {
            "message":"item is deleted. "
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Internal Server error. ")