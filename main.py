from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import user ,admin,cart 
import logger
from contextlib import asynccontextmanager
from redis_client import redis_py

@asynccontextmanager
async def lifespan(app:FastAPI):
    yield
    redis_py.close()
app=FastAPI(lifespan=lifespan)

app.mount("/static",StaticFiles(directory="static"),name="static")

app.include_router(user.router)
app.include_router(admin.router)
app.include_router(cart.router)