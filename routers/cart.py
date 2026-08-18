from fastapi import APIRouter,Depends,Request,Response,HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,delete
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db 
from database.models import Product,Cart,CartItem,Order,OrderItems
from services.utils import get_current_user
from schemas.product_schemas import Display_products , Cart_items
from schemas.order_schemas import Cart_product
from redis_client import redis_py
import json
from datetime import datetime,timezone

router=APIRouter(prefix="/product")
@router.get("/",response_model=list[Display_products], tags=["Products"])
async def display_products(user:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    try:
        all_products=redis_py.get("products:all_cash")
        if all_products is not None:
            return json.loads(all_products)

        all_products_data= await db.scalars(select(Product))
        all_products=all_products_data.all()
        items=[
            {
                "id":i.id,
                "name":i.name,
                "price":i.price,
                "is_available":i.is_available
            } 
            for i in all_products
        ]
        redis_py.set("products:all_cash",json.dumps(items),ex=60*10)
        return items
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is Down. try again later.")

@router.post("/add_to_cart", tags=["Cart"])
async def add_item_to_cart(item:Cart_product,db:AsyncSession=Depends(get_db),payload:dict=Depends(get_current_user)):
    try:
        user_id=int(payload.get("sub"))
        cart=await db.scalar(select(Cart).where(Cart.user_id==user_id))
        if not cart:
            cart=Cart(user_id=user_id)
            db.add(cart)
            await db.flush()
        is_product=await db.get(Product,item.id)
        if not is_product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Items Found.")
        if not is_product.is_available:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Item is not available.")
        existing= await db.scalar(select(CartItem).where(CartItem.cart_id==cart.id , CartItem.product_id==item.id))
        if existing:
            existing.quantity=item.qty
            await db.commit()
            return {
                "message":"Updated"
            }

        new_item=CartItem(cart_id=cart.id,quantity=item.qty,product_id=item.id)
        db.add(new_item)
        await db.commit()
        return {
            "message":"Product was added successfully."
        }      
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down.")

@router.get("/cart",tags=["Cart"],response_model=list[Cart_items])
async def display_cart(db:AsyncSession=Depends(get_db),payload:dict=Depends(get_current_user)):
    user_id=payload.get("sub")
    try:
        data=await db.execute(select(CartItem,Product).join(Cart).join(Product).where(Cart.user_id==int(user_id)))
        product_list=[]
        # print( data.all())
        for cart_item , product in data:
            product_list.append(
                {
                    "id":cart_item.id,
                    "name":product.name,
                    "price":product.price,
                    "quantity":cart_item.quantity,
                    "total":product.price*cart_item.quantity
                }
            )
            print(product_list)
        return product_list

    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down.")



@router.delete("/cart/delete/item",tags=["Cart"])
async def delete_item_cart(cart_item_id:int,db:AsyncSession=Depends(get_db),payload:dict=Depends(get_current_user)):
    user_id=int(payload.get("sub"))
    db_cart_item= await db.scalar(select(CartItem).join(Cart).where(CartItem.id==cart_item_id,Cart.user_id==user_id))
    if not db_cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Items Found.")
    try:
        await db.delete(db_cart_item)
        await db.commit()
        return {
            "message":"Product was removed from cart."
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down.")

@router.post("/checkout", tags=["Checkout"])
async def checkout(
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = int(payload.get("sub"))

        result = await db.scalars(
            select(CartItem)
            .join(Cart)
            .where(Cart.user_id == user_id)
        )

        cart_list = result.all()

        if not cart_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your cart is empty"
            )
    
        products_ids=[i.product_id for i in cart_list]
        db_items_obj=await db.scalars(select(Product).where(Product.id.in_(products_ids)))
        products=db_items_obj.all()
        product_map={
            pro.id:pro
            for pro in products
        }

        new_order = Order(
                user_id=user_id,
                order_placed_at=datetime.now(timezone.utc),
                total_products=0,
                total_amount=0
            )
        db.add(new_order)
        await db.flush()



        total = 0
        all_items = []
        new_db_items = []


        for items in cart_list:
            pro = product_map.get(items.product_id)
            if not pro:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Some products were deleted from the database."
                )

            if not pro.is_available:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{pro.name} is not available. Try again later."
                )

            item_total = pro.price *items.quantity
            total += item_total

            all_items.append({
                "name": pro.name,
                "price": pro.price,
                "quantity":items.quantity,
                "total": item_total
            })

            new_db_items.append(
                OrderItems(
                    order_id=new_order.id,
                    product_name=pro.name,
                    product_qty=items.quantity,
                    price=pro.price
                )
            )

        new_order.total_products = sum(i.quantity for i in cart_list)
        new_order.total_amount = total

        db.add_all(new_db_items)


        await db.execute(
            delete(Cart).where(Cart.user_id == user_id)
        )

        await db.commit()

        return {
            "items": all_items,
            "grand_total": total
        }

    except SQLAlchemyError:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database is down."
        )
