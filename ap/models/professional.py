from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

class PermissionRequest(Base):
    __tablename__ = "permission_requests"

    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    action: Mapped[str] = mapped_column(String)
    client_label: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(String)
    risk_tier: Mapped[str] = mapped_column(String)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String, default="pending")

class DeliveredNote(Base):
    __tablename__ = "delivered_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String)
    client_label: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(String)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
