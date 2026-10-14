from pydantic import BaseModel ,Field
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
    quantity:float
    image:str
    is_available:bool
    

class Cart_items(BaseModel):
    id:int
    name:str
    price:float
    quantity:float
    total:int