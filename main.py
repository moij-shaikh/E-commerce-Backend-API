from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import user ,admin,cart , order , product , pages
import logger
from arq import create_pool
from arq.connections import RedisSettings
from contextlib import asynccontextmanager

@asynccontextmanager
async def  lifespan(app:FastAPI):
    app.state.arq =  await create_pool(RedisSettings())
    yield
    await app.state.arq.aclose()

app=FastAPI(lifespan=lifespan)


app.include_router(user.router)
app.include_router(admin.router)
app.include_router(cart.router)
app.include_router(product.router)
app.include_router(order.router)
app.include_router(pages.router)
app.mount("/static", StaticFiles(directory="static"))