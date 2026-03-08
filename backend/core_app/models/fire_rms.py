"""
Fire RMS supplemental models — extends fire.py with structured violation tracking
for the inspection workflow.

NOTE: Core NERIS incident, preplan, hydrant, and inspection models live in fire.py.
      This module adds the InspectionViolation detail table only.
"""
# pylint: disable=not-callable,unsubscriptable-object

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base


class InspectionViolation(Base):
    """
    Line-item violation record linked to a FireInspection.
    Tracks building/fire code deficiencies found during an inspection,
    their correction status, and resolution dates.
    """

    __tablename__ = "fire_inspection_violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fire_inspections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OUTSTANDING")
    correction_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    corrected_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
