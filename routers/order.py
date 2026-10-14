from fastapi import APIRouter ,HTTPException , status, Depends , Form
from database.database import get_db
from database.models import Order, OrderItems, Product , Cart , CartItem
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from services.auth import get_current_user
from datetime import datetime , timezone

router=APIRouter(tags=["User - Order"])

@router.get("/product")
async def product__get_all(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    db_products= await db.scalars(select(Product))
    db_product_list= db_products.all()
    return db_product_list

@router.get("/order")
async def order__get_all(payload:dict=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get("sub"))
    db_orders= await db.scalars(select(Order).where(Order.user_id == user_id))
    db_orders_list=db_orders.all()
    if not db_orders_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Order Found. ")
    return db_orders_list

@router.get("/order/{id}")
async def order__get_one(id:int,payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get("sub"))
    db_order= await db.scalar(select(Order).where(Order.id == id , Order.user_id ==user_id).options(selectinload(Order.items)))
    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Order Found. ")
    display={
        "id":db_order.id,
        "user_id":db_order.user_id,
        "items":[
            {
                "id":i.product_id,
                "price":i.price,
                "qty":i.product_qty ,
                'total':i.total
            }
            for i in db_order.items
        ],
        "total_products":db_order.total_products,
        "total_amount":db_order.total_amount,
        "order_placed_at":db_order.order_placed_at,
        "status":db_order.status,
        "is_paid":db_order.is_paid
        
    }
    return display

@router.post("/order/buy-now")
async def order__new(
    product_id:int=Form(gt=0),
    product_qty:float=Form(gt=0),
    payload:dict=Depends(get_current_user),
    db:AsyncSession=Depends(get_db)
):
    user_id=int(payload.get("sub"))
    is_product= await db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if not is_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Product Found. ")
    if not is_product.is_available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Product is not available. ")
    if is_product.quantity < product_qty:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Product is Stock not available.we only have {is_product.quantity}  ")
        
    total_amount=is_product.price * product_qty
    new_order=Order(
        user_id=user_id,
        total_amount=total_amount,
        total_products=product_qty,
        order_placed_at=datetime.now(timezone.utc),
        status="pending"
    )
    try:
        db.add(new_order)
        await db.flush()
        await db.refresh(new_order)
        order_items=OrderItems(
            order_id=new_order.id,
            product_id=product_id,
            price=is_product.price,
            product_qty=product_qty,
            total=total_amount
        )
        
        db.add(order_items)
        is_product.quantity -= product_qty
        await db.commit()
        return {
            "message":"Order is placed. "
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Error.")

@router.post("/order/check-out")
async def order__checkout(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get('sub'))
    db_cart=await db.scalar(select(Cart).where(Cart.user_id==user_id).options(selectinload(Cart.items).selectinload(CartItem.product)))
    if not db_cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error while loading cart. ")
    if not db_cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty. ")
    product_ids={ i.product_id for i in db_cart.items}
    db_products= await db.scalars(select(Product).where(Product.id.in_(product_ids)).order_by(Product.id).with_for_update())
    products={
        product.id:product
        for product in db_products.all()
    }
    if len(product_ids) > len(products.keys()):
        not_available_items=set()
        for id in  products.keys():
            if id not in product_ids:
                not_available_items.add(id)
            
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Some products are not available. {not_available_items}")
    for item in db_cart.items:
        product=products.get(item.product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Product {item.product_id} no longer exists. ")
        if not product.is_available:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Product is not available. ")
        if product.quantity < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f"Product is Stock not available.we only have {is_product.quantity}  ")
    total_amount=sum(
        products[item.product_id].price * item.quantity
        for item in db_cart.items
    )
    new_order=Order(
        user_id=user_id,
        order_placed_at=datetime.now(timezone.utc),
        total_amount=total_amount,
        total_products=len(db_cart.items),
    )
    db.add(new_order)
    await db.flush()
    new_order_items=[]
    for item in db_cart.items:
        product= products[item.product_id]
        new_order_items.append(
            OrderItems(
                order_id=new_order.id,
                product_id=product.id,
                price=product.price,
                product_qty=item.quantity,
                total=product.price * item.quantity
            )
        )
        product.quantity -= item.quantity
    db.add_all(new_order_items)
    # try:
    await db.delete(db_cart)
    await db.commit()
    return{
        "message":"order placed successfully. "
    }
    # except SQLAlchemyError:
    #     await db.rollback()
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Oder could not be placed. ")
        
    


@router.delete("/order/{id}")
async def order__delete(id:int, payload:dict=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    user_id=int(payload.get("sub"))
    db_order= await db.scalar(select(Order).where(Order.id == id, Order.user_id == user_id))
    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Order Found. ")
    if db_order.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="you can not delete this order. ")
    db_order.status="cancel"
    
    try:
        await db.commit()
        if db_order.is_paid:
            return {
                    "message":"Order is canceled. and refund will be issued soon. "
                }
        else:
            return {
                "message":"Order is deleted. "
            }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Error.")
        
    