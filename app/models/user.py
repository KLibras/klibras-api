from sqlalchemy import Column, Integer, String, ARRAY, Enum as SQLAlchemyEnum
from app.db.database_connection import Base
from app.schemas.enums import UserRole 


class User(Base):
    __tablename__ = "users"  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(10), unique=True, index=True, nullable=False,)
    password = Column(String(100), nullable=False)
    points = Column(Integer, default=0,nullable=False)

    role = Column(SQLAlchemyEnum(UserRole, name="roles_enum"), nullable=False)

    def __repr__(self):
        return f"User(id={self.id}, username='{self.username}', points={self.points})"
    
    def __iter__(self):
        yield self.id
        yield self.email
        yield self.username
        yield self.points
        yield self.role