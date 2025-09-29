from pydantic import BaseModel, EmailStr
from typing import List
from .enums import UserRole 


class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.USER


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    points: int
    class Config:
        orm_mode = True
     