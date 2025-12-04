from __future__ import annotations

from typing import Dict, Tuple
from appointments.models import AppointmentState

# Allowed transitions: (from_state, event) -> to_state
TRANSITIONS: Dict[Tuple[AppointmentState, str], AppointmentState] = {
    (AppointmentState.INIT, "validate_ok"): AppointmentState.VALIDATING,
    (AppointmentState.VALIDATING, "route_selected"): AppointmentState.ROUTING,
    (AppointmentState.ROUTING, "provider_reserved"): AppointmentState.BOOKING,
    (AppointmentState.BOOKING, "book_success"): AppointmentState.CONFIRMED,
    (AppointmentState.BOOKING, "book_failed"): AppointmentState.FAILED,
    (AppointmentState.INIT, "cancel"): AppointmentState.CANCELLED,
    (AppointmentState.VALIDATING, "cancel"): AppointmentState.CANCELLED,
    (AppointmentState.ROUTING, "cancel"): AppointmentState.CANCELLED,
    (AppointmentState.BOOKING, "cancel"): AppointmentState.CANCELLED,
}


def advance_state(current: AppointmentState, event: str) -> AppointmentState:
    key = (current, event)
    if key not in TRANSITIONS:
        raise ValueError(f"Invalid transition from {current} on {event}")
    return TRANSITIONS[key]
