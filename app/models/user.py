from typing import List, TYPE_CHECKING
from sqlalchemy import (Integer, String, Enum as SQLAlchemyEnum, Table, Column, ForeignKey)
from sqlalchemy.orm import (Mapped, mapped_column, relationship)
from app.db.database_connection import Base
from app.schemas.enums import UserRole

if TYPE_CHECKING:
    from app.models.module import Module
    from app.models.sign import Sign

user_module_association = Table(
    "user_module_association",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("module_id", ForeignKey("modules.id"), primary_key=True),
)

user_sign_association = Table(
    "user_sign_association",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("sign_id", ForeignKey("signs.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLAlchemyEnum(UserRole, name="roles_enum"), default=UserRole.USER, nullable=False)

    completed_modules: Mapped[List["Module"]] = relationship(
        "Module",
        secondary=user_module_association,
        back_populates="completed_by_users"
    )
    known_signs: Mapped[List["Sign"]] = relationship(
        secondary=user_sign_association, 
        back_populates="known_by_users"
    )

    def __repr__(self):
        return f"User(id={self.id}, username='{self.username}', points={self.points})"
    
    def __iter__(self):
        yield self.id
        yield self.email
        yield self.username
        yield self.points
        yield self.role
