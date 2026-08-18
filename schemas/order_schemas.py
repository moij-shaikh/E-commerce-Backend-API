from pydantic import BaseModel , Field

class Cart_product(BaseModel):
    id:int
    qty:float


    
class show_history_items(BaseModel):
    id:int
    name:str
    quantity:int = Field(ge=1)
    price:float
    total:float