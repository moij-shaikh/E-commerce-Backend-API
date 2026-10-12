from pwdlib import PasswordHash
from redis_client import redis_py

from database.database import get_db
from database.models import Admin
from sqlalchemy.ext.asyncio import AsyncSession


from fastapi import HTTPException,status , Depends , Cookie
from config import JWT_ALGORITHM , JWT_SECRET_KEY
import secrets 
from datetime import datetime  , timedelta , timezone
pass_hasher=PasswordHash.recommended()


jwt_key=JWT_SECRET_KEY
jwt_algo=JWT_ALGORITHM
from jose import jwt,JWTError

from fastapi.security import OAuth2PasswordBearer
get_jwt_token=OAuth2PasswordBearer(tokenUrl="/user/login",auto_error=False)


def make_access_token(sub, role , exp):
      if not exp:
            exp=10
      payload={
            "sub":sub,
            "exp":datetime.now(timezone.utc)+ timedelta(minutes=exp),
            "token_id":str(secrets.token_urlsafe(16))
      }
      if role:
            payload["role"]=role
      try:
            access_token=jwt.encode(payload, jwt_key , algorithm=jwt_algo)
            return access_token
      except JWTError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server is down")
def make_refresh_token(sub):
      payload={
            "sub":sub,
            "exp":datetime.now(timezone.utc)+ timedelta(days=7),
            "token_id":str(secrets.token_urlsafe(16))
      }
      try:
            refresh_token=jwt.encode(payload, jwt_key , algorithm=jwt_algo)
            return refresh_token
      except JWTError:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server is down")



def get_current_user(token:str=Depends(get_jwt_token))->dict:
    if not token:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Please login First.")
    try:
        payload=jwt.decode(token,jwt_key,algorithms=[jwt_algo])
    except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Try to login")
    is_blocked=redis_py.get(f"blocked_access_token:{payload.get("token_id")}")
    if is_blocked is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Please Login First")
    user=payload.get("sub")
    if not user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Please Try again later")
    return payload

def generate_access_token_from_refresh_token(refresh_token:str=Cookie())->str:
      if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login First. cookie")
      redis_token= redis_py.get(f"refresh_token:{refresh_token}")
      if not redis_token or redis_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login First. redis ")
            
      try:
            payload=jwt.decode(redis_token , jwt_key, algorithms=[jwt_algo])
            if str(redis_token) != str(payload.get("sub")):
                  raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid token.")
            access_token=make_access_token(payload.get("sub"))
            return access_token
      except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Login First. ")

async def check_admin(session_id:str=Cookie(),db:AsyncSession=Depends(get_db))->dict:
    if not session_id:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Data Found Try to login First.")
    admin_token=redis_py.get(f"admin:{session_id}")
    if admin_token is None:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Data Found Try to login First.")
    try:
          payload=jwt.decode(admin_token,jwt_key,algorithms=[jwt_algo])
          if payload.get("role") != "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not authorized to access this page.")
    except JWTError:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Credential try again later")
    db_admin= await db.get(Admin,payload.get("sub"))
    if not db_admin:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Invalid Credential try again later")
    return {
          "username":db_admin.username,
    }
