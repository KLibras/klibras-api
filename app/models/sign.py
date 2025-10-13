from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, String
from app.db.database_connection import Base
from sqlalchemy.orm import (Mapped, mapped_column, relationship)

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.module import Module

class Sign(Base):
    __tablename__ = 'signs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)
    desc: Mapped[str] = mapped_column(String(500), nullable=False)
    videoUrl: Mapped[str] = mapped_column(String(150), nullable=False)
    pontos: Mapped[int] = mapped_column(Integer, default= 5, nullable=False)
    
    known_by_users: Mapped[List["User"]] = relationship(
        secondary="user_sign_association",
        back_populates="known_signs"
    )

    modules: Mapped[List["Module"]] = relationship(
        secondary="module_sign_association",
        back_populates="signs"
    )
