import os
from dotenv import load_dotenv
from pwdlib import PasswordHash
from redis_client import redis_py
from fastapi import HTTPException,status,Depends , Cookie ,Response
from database.database import get_db
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Admin , User
load_dotenv()

pass_hasher=PasswordHash.recommended()


jwt_key=os.getenv("JWT_SECRET_KEY")
jwt_algo=os.getenv("JWT_ALGORITHM")
from jose import jwt,JWTError

from fastapi.security import OAuth2PasswordBearer
get_jwt_token=OAuth2PasswordBearer(tokenUrl="/user/login",auto_error=False)


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
