from datetime import datetime
import json
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    trace_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details_json: Mapped[Optional[str]] = mapped_column("details", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @property
    def details(self) -> Optional[dict]:
        if not self.details_json:
            return None
        try:
            return json.loads(self.details_json)
        except json.JSONDecodeError:
            return None

    @details.setter
    def details(self, value: Optional[dict]):
        if value is None:
            self.details_json = None
        else:
            self.details_json = json.dumps(value)
