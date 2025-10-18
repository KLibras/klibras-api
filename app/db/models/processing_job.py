from sqlalchemy import Column, String, JSON, DateTime, Boolean, Integer
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from datetime import datetime
from typing import Optional

Base = declarative_base()

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_action: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="processing")
    action_found: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    predicted_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_match: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)