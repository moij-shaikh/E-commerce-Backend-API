from fastapi import APIRouter,HTTPException , status, Depends , Form , File , UploadFile

from schemas.product_schemas import  Unit, UpdateProduct , Display_products
from pathlib import Path
from database.database import get_db
from database.models import Product
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from services.auth import check_admin

router=APIRouter(tags=["Admin - Product"], prefix="/admin")



async def valid_image(image:UploadFile):
    image_dir=Path("Upload/Image")
    image_dir.mkdir(parents=True,exist_ok=True)
    supported_image={"image/jpeg","image/png"}
    if image.content_type not in supported_image:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Image is not supported.")
    image_path=image_dir / image.filename
    
    if image_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Image name already present.")
    with image_path.open("wb") as file:
        file.write( await image.read())
    return image_path


@router.post("/product")
async def product__add(
    name: str = Form(),
    unit: Unit = Form(),
    quantity: int = Form(),
    price: float = Form(),
    is_available: bool = Form(),
    image:UploadFile=File(...), 
    admin:dict=Depends(check_admin),
    db:AsyncSession=Depends(get_db)
):
    image_path=await valid_image(image)
    db_product=Product(
        unit=unit,
        quantity=quantity,
        name=name,
        price=price,
        is_available=is_available,
        image=str(image_path)
        
    )
    try:
        db.add(db_product)
        await db.commit()
        return{
            "message":"new product is added"
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is not working. ")
    
@router.get("/product", response_model=list[Display_products])
async def product__get_all(admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    db_products= await db.scalars(select(Product))
    db_product_list= db_products.all()
    return db_product_list

@router.get("/product/{id}", response_model=Display_products)
async def product__get_all(id:int, admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    db_product= await db.get(Product,id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Product found.")
    return db_product

@router.delete("/product/{id}")
async def product__get_all(id:int, admin:dict=Depends(check_admin),db:AsyncSession=Depends(get_db)):
    db_product= await db.get(Product,id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Product found.")
    try:
        await db.delete(db_product)
        await db.commit()
        return {
            "message":f"Id: {db_product.id}, Name: {db_product.name} was deleted successfully. "
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is not working. ")
    
@router.patch("/product/{id}/image")
async def product__update_image(id:int,image:UploadFile=File(...), admin:dict=Depends(check_admin) , db:AsyncSession=Depends(get_db)):
    db_product= await db.get(Product,id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Product found.")
    image_path= await valid_image(image)
    try:
        db_product.image = str(image_path)
        await db.commit()
        return{
            "message":f"Id: {db_product.id} products image is updated successfully. "
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is not working. ")
    


@router.patch("/product/{id}")
async def product__update_image(id:int,new_data:UpdateProduct,admin:dict=Depends(check_admin) , db:AsyncSession=Depends(get_db)):
    db_product= await db.get(Product,id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No Product found.")
    data=new_data.model_dump(exclude_none=True)
    for filed, val in data.items():
        setattr(db_product, filed , val)
    try:
        await db.commit()
        return {
            "message":f"Id: {db_product.id} products values are updated successfully. "
            
        }
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Database is not working. ")