# from pydantic import BaseModel, EmailStr

# class UserSignup(BaseModel):
#     first_name: str
#     last_name: str
#     email: EmailStr
#     phone: str
#     cnic: str
#     password: str

from pydantic import BaseModel, EmailStr, Field

class UserSignup(BaseModel):
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    email: EmailStr
    phone: str
    cnic: str
    password: str

    class Config:
        populate_by_name = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    phone: str
    cnic: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
