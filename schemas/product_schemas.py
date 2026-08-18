from pydantic import BaseModel ,ConfigDict

class Add_product(BaseModel):
    name:str
    price:float
    is_available:bool=False

class Display_products(BaseModel):
    id:int
    name:str
    price:float
    is_available:bool
    model_config=ConfigDict(from_attributes=True)

class Cart_items(BaseModel):
    id:int
    name:str
    price:float
    quantity:float
    total:int