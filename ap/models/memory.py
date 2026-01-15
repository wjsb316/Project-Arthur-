from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

class Memory(Base):
    __tablename__ = "memory_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True, default="default")
    kind: Mapped[str] = mapped_column(String)  # "fact", "episode", "open_loop"
    content: Mapped[str] = mapped_column(String)
    importance: Mapped[float] = mapped_column(Float, default=1.0)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.01)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Note: Vector data will likely be stored in a parallel 'vec0' virtual table
    # or we handle it via raw SQL queries joining on 'id'.
    # sqlite-vec usually works best with a rowid linkage - "id".
