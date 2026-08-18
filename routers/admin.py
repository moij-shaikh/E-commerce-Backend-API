from fastapi import APIRouter,Response,Request,HTTPException,Depends,Form,BackgroundTasks,status
from database.database import get_db
from database.models import Product ,User,Admin , Order,OrderItems
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas.product_schemas import Add_product
from services.email import send_admin_email
from services.utils import check_admin
from datetime import timedelta , timezone,datetime
from jose import jwt
import os 
import secrets
from dotenv import load_dotenv
from redis_client import redis_py
load_dotenv()
jwt_key=os.getenv("JWT_SECRET_KEY")
jwt_algo=os.getenv("JWT_ALGORITHM")
router=APIRouter(prefix="/admin")

@router.post("/login",tags=["Admin"])
async def admin_login(res:Response,req:Request,bg_task:BackgroundTasks,username:str=Form(),password:str=Form(),db:AsyncSession=Depends(get_db)):
    try:
        db_admin= await db.get(Admin,username)
        ip=req.client.host 
        # bg_task.add_task(send_admin_email,ip)        
        if not db_admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Nothing Try Again")
        if password == db_admin.password:
            payload={
                "sub":str(username),
                "role":"admin",
                "exp":datetime.now(timezone.utc)+timedelta(minutes=30)
            }
            token=jwt.encode(payload,jwt_key,algorithm=jwt_algo)
            session_id=secrets.token_urlsafe(32)
            redis_py.set(f"admin:{session_id}",token,ex=60*30)
            res.set_cookie(key="session_id",value=session_id,samesite="strict",path='/admin',httponly=True)
            return {
                "message":"Successfully Login"
            }        
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is not responding.") 


@router.get("/products/display",tags=["admin / Products"])
async def list_products(admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    try:
        db_list=await db.scalars(select(Product))
        product_list=db_list.all()
        return [item for item in product_list]
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down try again later.")

@router.post("/products/add",tags=["Admin / Products"])
async def add_product(product:Add_product,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    try:
        new_product=Product(name=product.name,price=product.price,is_available=product.is_available)
        db.add(new_product)
        await db.commit()
        redis_py.delete("products:all_cash")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is Down Try Again Later.")
    return product

@router.patch("/product/update",tags=["Admin / Products"])
async def update_product(
    product_id:int,
    admin:dict=Depends(check_admin),
    name:str|None=Form(default=None),
    price:float|None=Form(default=None),
    is_available:bool|None=Form(default=None),
    db:AsyncSession=Depends(get_db)
):
    try:
        db_product=await db.get(Product,product_id)
        if db_product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Product dose not exists try to refresh.")
        if name is not None:
            db_product.name=name
        if price is not None:
            db_product.price=price
        if is_available is not None:
            db_product.is_available=is_available
        await db.commit()
        redis_py.delete("products:all_cash")
        return {
            "message":"Product have been successfully Updated.",
            "pro":db_product
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down try again Later.")

@router.delete("/product/delete",tags=["Admin / Products"])
async def delete_products(product_id:int,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    try:
        product= await db.get(Product,product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No product Found.")
        await db.delete(product)
        await db.commit()
        redis_py.delete("products:all_cash")
        return {"message":f"{product.name} was Deleted Successfully"}
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down try again Later.")    

@router.post("/user/block",tags=["Admin / user"])
async def block_user(user_id:int,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    db_user=await db.get(User,user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User Not Found.")
    try:
        db_user.is_blocked=True
        await db.commit()
        return {
            "message":f"{db_user.username} was successfully Blocked."
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database Server is Down Try again later")

@router.post("/user/unblock",tags=["Admin / user"])
async def unblock_user(user_id:int,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    db_user= await db.get(User,user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No User Found.")
    try:
        db_user.is_blocked=False
        await db.commit()
        return {
            "message":f"{db_user.username} was successfully Unblocked."
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database Server is Down Try again later")


@router.delete("/user/delete",tags=["Admin / user"])
async def delete_user(user_id:int,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    db_user=await db.get(User,user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No User Found.")
    try:
        await db.delete(db_user)
        await db.commit()
        return {
            "message":f"{db_user.username} was successfully deleted."
        }
    except SQLAlchemyError:
        await db.rollback()

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database Server is Down Try again later")


@router.get("/order",tags=["Admin / order"])
async def show_order(db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    db_obj=await db.execute(select(Order,User).join(User,Order.user_id==User.id).where(Order.status.not_in("Delivered","cancelled")))
    db_list=db_obj.all()
    data=[]
    for order,user in db_list:
        data.append(
            {
                "user_id:":user.id,
                "order_id":order.id,
                "full_name:":user.full_name,
                "email : ":user.email,
                "blocked: ":user.is_blocked,
                "total_amount":order.total_amount,
                "total_products: ":order.total_products,
                "order_placed_at":order.order_placed_at,
                "status":order.status
            }
        )
    return data

@router.get("/order/history",tags=["Admin / order"])
async def show_order_history(db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    db_obj=await db.execute(select(Order,User).join(User,Order.user_id==User.id))
    db_list=db_obj.all()
    if not db_list:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No products Found.")
    data=[]
    for order,user in db_list:
        data.append(
            {
                "user_id:":user.id,
                "order_id":order.id,
                "full_name:":user.full_name,
                "email : ":user.email,
                "blocked: ":user.is_blocked,
                "total_amount":order.total_amount,
                "total_products: ":order.total_products,
                "order_placed_at":order.order_placed_at,
                "status":order.status
            }
        )
    return data

@router.get("/order/items" ,tags=["Admin / order"])
async def get_order_items(order_id:int,db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    if not order_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Order Found.")
    db_items=await db.scalars(select(OrderItems).where(OrderItems.order_id==order_id))
    data=db_items.all()
    if not data:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No data found.")
    return data

@router.post("/delivery",tags=["Admin / delivery"])
async def manage_delivery(order_id:int,order_status:str,db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    allowed_status=["Pending","Out_for_Delivery","Delivered","cancelled"]
    try:
        if order_status not in allowed_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Enter correct Status.")

        order= await db.get(Order,int(order_id))
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order not found.")
        if order.status == "Delivered" :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was Delivered already.")
        if order.status == "cancelled" :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was cancelled already.")
        order.status=order_status   
        await db.commit()
        return "Updated!"
    except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database Server is Down Try again later")

@router.post("/payment",tags=["Admin / delivery"])
async def user_payment(order_id:int,payment_status:str,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    allowed_status=["Pending","Paid"]
    try:
        if payment_status not in allowed_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Select Correct response.")
        db_order=await db.get(Order,order_id)
        if not db_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order Not Found.")
        if payment_status != "Paid":
            db_order.is_paid=False
        if payment_status == "Paid":
            db_order.is_paid=True
        await db.commit()
        return {
            "message":f"Payment was {payment_status}."
        }
    except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database Server is Down Try again later")

@router.patch("/order/cancel",tags=["Admin / order"])
async def cancel_order(order_id:int,db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    try:
        db_order=await db.get(Order,order_id)
        if not db_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order Not Found.")
        if db_order.status=="cancelled":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was already cancelled")
        if db_order.status=="Delivered":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was already Delivered")
        db_order.status="cancelled"
        await db.commit()
        return {
            "message":f"{db_order.id} was cancelled."
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down.")