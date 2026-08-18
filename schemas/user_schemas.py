from pydantic import BaseModel,Field
class User_address(BaseModel):
    house_no:str
    street_name:str
    Pincode:str
    Landmark:str|None=None

class Register_user(BaseModel):
    full_name:str=Field(...,description="Enter your full name")
    username:str=Field(...,description="Enter an unique Username, You can not change username later.")
    password:str
    email:str
    address:User_address
