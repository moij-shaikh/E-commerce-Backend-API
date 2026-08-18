from .models import Base
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
import os
import logging
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL=os.getenv("DATABASE_URL")
engine=create_async_engine(DATABASE_URL)



local_session=async_sessionmaker(bind=engine,expire_on_commit=False)

async def get_db():
    async with local_session() as db:
        yield db



