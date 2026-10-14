from fastapi import FastAPI
from routers import user ,admin,cart , order , product
import logger


app=FastAPI()


app.include_router(user.router)
app.include_router(admin.router)
app.include_router(cart.router)
app.include_router(product.router)
app.include_router(order.router)
