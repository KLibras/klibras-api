from pydantic import BaseModel, EmailStr, validator
from typing import TYPE_CHECKING, List
from .enums import UserRole 
from app.models.sign import Sign

if TYPE_CHECKING:
    from app.models.user import User

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    points: int
    role: UserRole = UserRole.USER


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    points: int
    signs_count: int = 0
    
    @validator('signs_count', pre=True, always=True)
    def calculate_signs_count(cls, v, values):
        return v
    
    class Config:
        orm_mode = True