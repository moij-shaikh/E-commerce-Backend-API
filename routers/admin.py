import secrets
from redis_client import redis_py

from database.database import get_db
from database.models import User,Admin , Order,OrderItems , PaymentMethod , OrderStatus
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from services.email import send_admin_email
from services.auth import check_admin , make_access_token

from fastapi import APIRouter,Response,Request,HTTPException,Depends,Form,BackgroundTasks,status


router=APIRouter(prefix="/admin")

@router.post("/login",tags=["Admin"])
async def admin_login(res:Response,req:Request,bg_task:BackgroundTasks,username:str=Form(),password:str=Form(),db:AsyncSession=Depends(get_db)):
    try:
        db_admin= await db.get(Admin,username)
        # bg_task.add_task(send_admin_email,ip)
        if not db_admin:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Admin found. ")
        if password == db_admin.password:
            token=make_access_token(username,role="admin",exp=30)
            session_id=secrets.token_urlsafe(32)
            redis_py.set(f"admin:{session_id}",token,ex=60*30)
            res.set_cookie(key="session_id",value=session_id,samesite="strict",path='/admin',httponly=True)
            return {
                "message":"Successfully Login"
            }
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is not responding.")

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


# order
@router.get("/order",tags=["Admin / order"])
async def show_order(db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    db_obj=await db.execute(select(Order,User).join(User,Order.user_id==User.id).where(Order.status.not_in(["Delivered","cancelled"])))
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
async def manage_delivery(order_id:int,order_status:OrderStatus,db:AsyncSession=Depends(get_db),admin:dict=Depends(check_admin)):
    try:
        order= await db.get(Order,int(order_id))
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order not found.")
        if order.status == OrderStatus.DELIVERED :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was Delivered already.")
        if order.status == OrderStatus.CANCELLED :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was cancelled already.")
        if order.status ==OrderStatus.PENDING:
            if order_status not in {OrderStatus.CANCELLED, OrderStatus.OUT_FOR_DELIVERY}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pending orders status can be either cancelled or out_for_delivery. ")
        elif order.status ==OrderStatus.OUT_FOR_DELIVERY: 
            if order_status not in {OrderStatus.CANCELLED , OrderStatus.DELIVERED}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order can be cancelled or delivery.  ")
                   
        order.status=order_status
        await db.commit()
        return "Updated!"
    except SQLAlchemyError:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database Server is Down Try again later")

@router.post("/payment",tags=["Admin / delivery"])
async def user_payment(order_id:int,admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    try:
        db_order=await db.get(Order,order_id)
        if not db_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order Not Found.")
        if db_order.status == OrderStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order is cancelled.")

        if db_order.is_paid :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Payment is already done")
        if db_order.payment_method ==PaymentMethod.COD:
            if db_order.status != OrderStatus.DELIVERED:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="COD payment can only be confirmed after delivery. ")
                
            db_order.is_paid= True
        
        await db.commit()
        return {
            "message":"Payment confirmed successfully. "
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
        if db_order.status==OrderStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was already cancelled")
        if db_order.status==OrderStatus.DELIVERED:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Order was already Delivered")
        db_order.status="cancelled"
        await db.commit()
        if db_order.is_paid :
            return {
                    "message":f"{db_order.id} was cancelled. And Refund is issued. "
            }
        else:
            return {
                "message":f"{db_order.id} was cancelled."
            }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is down.")
