from sqlalchemy import Integer, String
from app.db.database_connection import Base
from sqlalchemy.orm import (Mapped, mapped_column)

class Sign(Base):
    __tablename__ = 'signs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)
    desc: Mapped[str] = mapped_column(String(500), nullable=False)
    videoUrl: Mapped[str] = mapped_column(String(150), nullable=False)
    pontos: Mapped[int] = mapped_column(Integer, default= 5, nullable=False)
    
