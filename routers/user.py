import logging
import secrets
import os
from dotenv import load_dotenv
from redis_client import redis_py
from fastapi import APIRouter ,Depends,Request,Response ,HTTPException,status,BackgroundTasks,Form
from fastapi.security import OAuth2PasswordRequestForm
from schemas.user_schemas import Register_user
from schemas.order_schemas import show_history_items
from database.database import get_db 
from database.models import User,Address ,Order , OrderItems
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from jose import jwt , JWTError
from datetime import datetime,timedelta,timezone
from services.email import send_email
from services.utils import pass_hasher, get_current_user
load_dotenv()
jwt_key=os.getenv("JWT_SECRET_KEY")
jwt_algo=os.getenv("JWT_ALGORITHM")

router=APIRouter(prefix="/user")

@router.post("/register",tags=["User"])
async def register_user(bg_task:BackgroundTasks,request:Request,register_user:Register_user,db:AsyncSession=Depends(get_db)):
     existing=await db.scalar(select(User).where(User.username==register_user.username))
     if existing:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username is taken Try Another one.")
     existing= await db.scalar(select(User).where(User.email==register_user.email))
     if existing:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="An User is present with same email.")
     if request.client.host is None:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Server can not identify you as real user. If using vpn try again without vpn")
     try:
          user=User(
               full_name=register_user.full_name,
               username=register_user.username,
               ip_address=request.client.host,
               email=register_user.email,
               password=pass_hasher.hash(register_user.password)
               )
          db.add(user)
          await db.flush()
          address=Address(
               user_id=user.id,
               house_no=register_user.address.house_no,
               street_name=register_user.address.street_name,
               Pincode=register_user.address.Pincode,
               Landmark=register_user.address.Landmark
               )
          db.add(address)
          await db.commit()

          logging.info("%s is now registered",user.username)
          token=str(secrets.token_urlsafe(32))
          # bg_task.add_task(send_email,user.email,token)
          redis_py.set(f"email_verification_token:{token}",user.id,ex=60*7)
          return {
               "message":"Account was successfully Creates. Please Verify the Email ",
               "t":token
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")

@router.get("/verify/email",tags=["Auth"])
async def verify_user_email(token:str,db:AsyncSession=Depends(get_db)):
     user_id = redis_py.get(f"email_verification_token:{token}")
     if user_id is None:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid link")
     try:
          user=await db.get(User,user_id)
          if not user:
               raise HTTPException(detail="User Not Found",status_code=status.HTTP_404_NOT_FOUND)
          user.is_verified=True
          await db.commit()
          redis_py.delete(f"email_verification_token:{token}")
          return{
               "message":"Successfully Verified"
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")


@router.post("/login",tags=["User"])
async def user_login(res:Response,user_data:OAuth2PasswordRequestForm=Depends(),db:AsyncSession=Depends(get_db)):
     password=user_data.password
     username=user_data.username
     user= await db.scalar(select(User).where(User.username==username))
     if not user:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="please verify you Register")
     if not pass_hasher.verify(password,user.password):
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="please verify your password")
     if not user.is_verified :
               token=secrets.token_urlsafe(32)
               redis_py.set(f"email_verification_token:{token}",user.id,ex=60*7)
               return {
                    'email:token':token
               }
     if  user.is_blocked:
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You have been blocked Please Contact or email to us . ")
     payload={
          "sub":str(user.id),
          "token_id":str(secrets.token_urlsafe(16)),
          "exp":datetime.now(timezone.utc)+timedelta(minutes=10)
     }
     payload2={
          "sub":str(user.id),
          "exp":datetime.now(timezone.utc)+timedelta(days=7)
     }
     access_token=jwt.encode(payload,jwt_key,algorithm=jwt_algo)
     refresh_token=jwt.encode(payload2,jwt_key,algorithm=jwt_algo)
     res.set_cookie(key="refresh_token",value=refresh_token,samesite='strict',httponly=True,path="/user/auth/")
     redis_py.set(f"refresh_token:{refresh_token}",user.id,ex=60*60*24*7)
     return {
          "token_type":"bearer",
          "access_token":access_token
     }


@router.post("/auth/logout",tags=["Auth"])
def user_logout(res:Response,req:Request,payload:dict=Depends(get_current_user)):
     refresh=req.cookies.get("refresh_token")
     token_id=payload.get("token_id")
     if not refresh:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User already Logout.")
     redis_user=redis_py.get(f"refresh_token:{refresh}")
     if redis_user is None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User already Logout.")
     redis_py.delete(f"refresh_token:{refresh}")
     res.delete_cookie("refresh_token")
     redis_py.set(f"blocked_access_token:{token_id}","1",ex=60*10)
     return {
          "message":"Logout Successfully!"
     }

@router.post("/auth/refresh",tags=["Auth"])
def refresh_user_token(req:Request):
     token=req.cookies.get("refresh_token")
     if not token:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Please Check you Register and login correctly.")
     redis_token=redis_py.get(f"refresh_token:{token}")
     if redis_token is None:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Please Check you Register and login correctly.")
     try:
          payload=jwt.decode(token,jwt_key,algorithms=[jwt_algo])
     except JWTError:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Login First") 

     if str(redis_token) != str(payload.get("sub")):
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid token.")
     new_payload={
          "sub":str(redis_token),
          "exp":datetime.now(timezone.utc)+timedelta(minutes=10),
          "token_id":str(secrets.token_urlsafe(16))
     }
     access_token=jwt.encode(new_payload,jwt_key,algorithm=jwt_algo)
     return {
          "token_type":"bearer",
          "access_token":access_token
     } 

@router.patch("/info/update",tags=["User"])
async def update_user(
          payload:dict=Depends(get_current_user),
          full_name:str=Form(default=None),
          username:str=Form(default=None),
          db:AsyncSession=Depends(get_db)
          ):
     if full_name is  None and username is  None:
          return {
               "message": "Nothing has been Updated."
          }
     user=payload.get("sub")
     if not user:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Please Login First.")

     try:
          db_user=await db.get(User,user)
          if full_name is not None:
               db_user.full_name=full_name
          if username is not None:
               exists=await db.scalar(select(User).where(User.username==username))
               if exists and exists.id != db_user.id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Username is already Taken try Another.")
               db_user.username=username
          await db.commit()
          return {
               "message":f"{db_user.username} your information is Updated."
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")



@router.delete("/delete",tags=["User"])
async def delete_user(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
     try:
          user=payload.get("sub")
          db_user=await db.get(User,user)
          if not db_user:
               raise HTTPException(detail="User Not Found",status_code=status.HTTP_404_NOT_FOUND)
          username=db_user.username
          await db.delete(db_user)
          await db.commit()
          return {
               "message":f"{username} has been deleted"
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")

@router.get("/order/history",tags=["User"])
async def show_order_history(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
     user_id=int(payload.get("sub"))
     if not user_id:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No user Found.")
     db_order=await db.scalars(select(Order).where(Order.user_id==user_id))
     orders=db_order.all()

     if not orders:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No data found.")
     return orders

@router.get("/order/history/items",response_model=list[show_history_items],tags=["User"])
async def get_order_items(order_id:int,payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
     user_id=int(payload.get("sub"))
     db_order=await db.scalar(select(Order).where(Order.id==order_id,Order.user_id==user_id))
     if not db_order:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Not found.")
     db_items_obj=await db.scalars(select(OrderItems).where(OrderItems.order_id==order_id))
     db_items=db_items_obj.all()
     if not db_items:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No data found.")
     items=[]
     for i in db_items:
          items.append(
               {
                    "id":i.id,
                    "name":i.product_name,
                    "quantity":i.product_qty,
                    "price":i.price,
                    "total":i.price*i.product_qty
               }
          )
     return items


