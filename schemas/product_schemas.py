from pydantic import BaseModel ,Field , ConfigDict
from enum import Enum

class Unit(str,Enum):
    PIECE="piece"
    KG="kg"
    G="g"
    ML="ml"
    LITRE="litre"
    METER="meter"
    PACK="pack"
    BOX="box"
    


class AddProduct(BaseModel):
    name:str
    unit:Unit
    quantity:float
    price:float=Field(gt=0)
    is_available:bool=False
    
class UpdateProduct(BaseModel):
    name:str|None=None
    unit:Unit|None=None
    quantity:float|None=None
    price:float|None=Field(default=None,gt=0)
    is_available:bool|None=None

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