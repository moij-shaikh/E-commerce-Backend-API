import logging
import secrets

from redis_client import redis_py
from redis.exceptions import RedisError
from fastapi import APIRouter ,Depends,Request,Response ,HTTPException,status,BackgroundTasks,Form
from fastapi.security import OAuth2PasswordRequestForm
from schemas.user_schemas import Register_user  , UpdateUser 
from database.database import get_db
from database.models import User,Address, Order

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from services.email import send_email
from services.auth import pass_hasher, get_current_user , make_access_token , make_refresh_token , generate_access_token_from_refresh_token


router=APIRouter(prefix="/user")

@router.post("",tags=["User"])
async def register_user(bg_task:BackgroundTasks,request:Request,register_user:Register_user,db:AsyncSession=Depends(get_db)):
     existing=await db.scalar(select(User).where(User.username==register_user.username))
     if existing:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username is taken Try Another one.")
     existing= await db.scalar(select(User).where(User.email == register_user.email))
     if existing:
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="An User is present with same email.")
     token=str(secrets.token_urlsafe(32))
     try:
          user=User(
               full_name=register_user.full_name,
               username=register_user.username,
               email=register_user.email,
               password=pass_hasher.hash(register_user.password)
               )
          db.add(user)
          await db.flush()
          address=Address(
               user_id=user.id,
               house_no=register_user.address.house_no,
               street_name=register_user.address.street_name,
               postal_code=register_user.address.postal_code,
               landmark=register_user.address.Landmark
               )
          db.add(address)

          logging.info("%s is now registered",user.username)
          # bg_task.add_task(send_email,user.email,token)
          redis_py.set(f"email_verification_token:{token}",user.id,ex=60*7)
          
          await db.commit()
          
          return {
               "message":"Account was successfully Creates. Please Verify the Email ",
               "t":token
          }
     except SQLAlchemyError:
          await db.rollback()
          try:
               redis_py.delete(f"email_verification_token:{token}")
          except RedisError:
               pass
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")
     except RedisError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,detail="Email Verification is not Available. Try again later.")

@router.get("/verify/email",tags=["Auth"])
async def verify_user_email(token:str,db:AsyncSession=Depends(get_db)):
     user_id = redis_py.get(f"email_verification_token:{token}")
     if user_id is None:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid link")
     try:
          user_id=int(user_id)
          user=await db.get(User,user_id)
          if not user:
               raise HTTPException(detail="User Not Found",status_code=status.HTTP_404_NOT_FOUND)
          redis_py.delete(f"email_verification_token:{token}")
          
          user.is_verified=True
          await db.commit()
          return{
               "message":"Successfully Verified"
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")
     except RedisError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,detail="Email Verification is not Available. Try again later.")

@router.post("/login",tags=["User"])
async def user_login(res:Response,user_data:OAuth2PasswordRequestForm=Depends(),db:AsyncSession=Depends(get_db)):
     password=user_data.password
     username=user_data.username
     user= await db.scalar(select(User).where(User.username==username))
     if not user:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No user found.")
 
     if not pass_hasher.verify(password,user.password) or not user:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid username or password.")
     if not user.is_verified :
               token=secrets.token_urlsafe(32)
               try:
                    redis_py.set(f"email_verification_token:{token}",user.id,ex=60*7)
                    return {
                         'email:token':token
                    }
               except RedisError:
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Verification service is unavailable")
     if  user.is_blocked:
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You have been blocked Please Contact or email to us . ")
     if user.is_account_closed:
          raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="your account is closed. ")
          
     access_token=make_access_token(str(user.id))
     refresh_token=make_refresh_token(str(user.id))
     res.set_cookie(key="refresh_token",value=refresh_token,samesite='strict',httponly=True,path="/user/auth/",max_age=60*60*24*7)
     try:
          redis_py.set(f"refresh_token:{refresh_token}",user.id,ex=60*60*24*7)
          return {
                    "token_type":"bearer",
                    "access_token":access_token
               }
     except RedisError:
          raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Login service is down.")
     
     


@router.post("/auth/logout",tags=["Auth"])
def user_logout(res:Response,req:Request,payload:dict=Depends(get_current_user)):
     refresh=req.cookies.get("refresh_token")
     token_id=payload.get("token_id")
     exp=payload.get("exp")
     if not refresh:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User already Logout.")
     redis_user=redis_py.get(f"refresh_token:{refresh}")
     if redis_user is None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User already Logout.")
     redis_py.delete(f"refresh_token:{refresh}")
     res.delete_cookie(key="refresh_token",path="/user/auth/",httponly=True,samesite="strict")
     redis_py.set(f"blocked_access_token:{token_id}","1",ex=60*10)
     return {
          "message":"Logout Successfully!"
     }

@router.post("/auth/refresh",tags=["Auth"])
def refresh_user_token(access_token:str=Depends(generate_access_token_from_refresh_token)):
     return {
          "token_type":"bearer",
          "access_token":access_token
     }

@router.patch("",tags=["User"])
async def update_user(
          update_data:UpdateUser,
          payload:dict=Depends(get_current_user),
          db:AsyncSession=Depends(get_db)
          ):
     user=payload.get("sub")
     db_user=await db.get(User,user)
     if not db_user:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No user found.")
     db_address= await db.scalar(select(Address).where(Address.user_id == db_user.id))
     if not db_address:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No address found.")
          
     if update_data.username is not None:
          exists=await db.scalar(select(User).where(User.username==update_data.username))
          if exists and exists.id != db_user.id:
               raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Username is already Taken try Another.")
          
     user_data=update_data.model_dump(exclude_none=True)
     try:
          address_filed={
               "house_no",
               'street_name',
               'postal_code',
               'Landmark',
          }
          for field, val in user_data.items():
               if field in address_filed:
                    setattr(db_address, field , val)
               else:
                    setattr(db_user, field , val)
          await db.commit()
          return {
               "message":f"{db_user.username} your information is Updated."
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")

@router.delete("/account",tags=["User"])
async def delete_user(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
     try:
          user=int(payload.get("sub"))
          db_user=await db.get(User,user)
          if not db_user:
               raise HTTPException(detail="User Not Found",status_code=status.HTTP_404_NOT_FOUND)
          db_order= await db.scalars(select(Order).where(Order.user_id == db_user.id, Order.is_paid == False))
          db_order_list=db_order.all()
          if db_order_list:
               order_ids=[
                    order.id
                    for order in db_order_list
               ]
               raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Some unpaid orders remains with ids {order_ids}")
          
          db_user.is_account_closed=True
          await db.commit()
          return {
               "message":f"{db_user.username} your account has been closed. "
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")
@router.post("/account",tags=["User"])
async def delete_user(payload:dict=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
     try:
          user=int(payload.get("sub"))
          db_user=await db.get(User,user)
          if not db_user:
               raise HTTPException(detail="account is not closed. ",status_code=status.HTTP_400_BAD_REQUEST)
          if not db_user.is_account_closed:
                         raise HTTPException(detail="User Not Found",status_code=status.HTTP_404_NOT_FOUND)
          db_user.is_account_closed=False
          await db.commit()
          return {
               "message":f"{db_user.username} your account has been re-opened. "
          }
     except SQLAlchemyError:
          await db.rollback()
          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Sorry our database is down. try again")