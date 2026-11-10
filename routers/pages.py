from fastapi import APIRouter, Depends, Request, HTTPException , status
from fastapi.templating import Jinja2Templates
from database.database import get_db
from database.models import Product , User, Cart, CartItem
from services.auth import get_current_user

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router=APIRouter()
template=Jinja2Templates(directory="template")


@router.get("/")
async def root(req:Request, db:AsyncSession = Depends(get_db)):
    result= await db.scalars(select(Product).where(Product.is_available == True))
    products=result.all()
    if not products:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No products found. ")
    return template.TemplateResponse(req,"index.html", {"products":products})

@router.get("/login")
async def page__login(req:Request):
    return template.TemplateResponse(
        req, "login.html"
    )
    
@router.get("/register")
async def page__register(req:Request):
    return template.TemplateResponse(
        req, "register.html"
    )
    
@router.get("/page/cart")
async def page__cart(req:Request):
    return template.TemplateResponse(req, "cart.html")