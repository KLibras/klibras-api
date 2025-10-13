from typing import List, TYPE_CHECKING
from sqlalchemy import (Column, ForeignKey, Integer, String, Table)
from sqlalchemy.orm import (Mapped, mapped_column, relationship)
from app.db.database_connection import Base

if TYPE_CHECKING:
    from app.models.sign import Sign
    from app.models.user import User

module_sign_association = Table(
    "module_sign_association",
    Base.metadata,
    Column("module_id", ForeignKey("modules.id"), primary_key=True),
    Column("sign_id", ForeignKey("signs.id"), primary_key=True),
)

class Module(Base):
    __tablename__ = 'modules'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    signs: Mapped[List["Sign"]] = relationship(
        secondary=module_sign_association,
        back_populates="modules"
    )
    
    completed_by_users: Mapped[List["User"]] = relationship(
        secondary="user_module_association",
        back_populates="completed_modules"
    )
