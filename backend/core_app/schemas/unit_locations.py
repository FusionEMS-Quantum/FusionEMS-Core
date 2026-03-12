from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class LatestUnitLocation(BaseModel):
    unit_id: uuid.UUID
    lat: float
    lng: float
    recorded_at: datetime
    record_id: uuid.UUID


class LatestUnitLocationsResponse(BaseModel):
    items: list[LatestUnitLocation]
