from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from config import DATABASE_URL

engine=create_async_engine(DATABASE_URL)

local_session=async_sessionmaker(bind=engine,expire_on_commit=False)

async def get_db():
    async with local_session() as db:
        yield db



