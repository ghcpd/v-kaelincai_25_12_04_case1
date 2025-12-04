from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class AppointmentState(str, Enum):
    INIT = "INIT"
    VALIDATING = "VALIDATING"
    ROUTING = "ROUTING"
    BOOKING = "BOOKING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Location(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)


class Constraints(BaseModel):
    max_travel_minutes: Optional[int] = Field(default=None, ge=0)
    behavior: Optional[str] = None  # test hook to simulate behaviors


class AppointmentCreateRequest(BaseModel):
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    requested_time: str  # ISO8601 string; validation can be added
    location: Location
    constraints: Constraints = Field(default_factory=Constraints)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AppointmentResponse(BaseModel):
    appointment_id: str
    state: AppointmentState
    route_path: Optional[List[str]] = None
    route_cost: Optional[float] = None
    repeated: bool = False  # idempotent replay indicator


class Edge(BaseModel):
    source: str
    target: str
    weight: float


class RouteRequest(BaseModel):
    request_id: str
    edges: List[Edge]
    source: str
    target: str
    allow_negative: bool = True


class RouteResponse(BaseModel):
    path: List[str]
    cost: float
    validated: bool


class OutboxEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    appointment_id: str
    event_type: str
    payload: Dict[str, Any]
    dispatched: bool = False

