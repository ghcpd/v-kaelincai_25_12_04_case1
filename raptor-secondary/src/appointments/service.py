from __future__ import annotations

from typing import Optional
from appointments.models import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentState,
    OutboxEvent,
    RouteRequest,
    Edge,
)
from appointments.state_machine import advance_state
from appointments.idempotency import InMemoryIdempotencyStore
from appointments.outbox import InMemoryOutbox
from appointments.clients import RoutingClient, BookingClient
from appointments.logging_utils import get_logger, log_with_mask


class AppointmentService:
    def __init__(
        self,
        idempotency_store: Optional[InMemoryIdempotencyStore] = None,
        outbox: Optional[InMemoryOutbox] = None,
        routing_client: Optional[RoutingClient] = None,
        booking_client: Optional[BookingClient] = None,
    ):
        self.idempotency_store = idempotency_store or InMemoryIdempotencyStore()
        self.outbox = outbox or InMemoryOutbox()
        self.routing_client = routing_client
        self.booking_client = booking_client
        self.logger = get_logger("appointment-service")

    def create_appointment(self, req: AppointmentCreateRequest) -> AppointmentResponse:
        cached = self.idempotency_store.get(req.idempotency_key)
        if cached:
            cached_resp = dict(cached)
            cached_resp["repeated"] = True
            return AppointmentResponse(**cached_resp)

        state = AppointmentState.INIT
        log_with_mask(
            self.logger,
            "appointment_init",
            request_id=req.idempotency_key,
            appointment_state=state,
            customer_id=req.customer_id,
            location=req.location.model_dump(),
        )

        # Validation phase
        state = advance_state(state, "validate_ok")

        # Routing
        state = advance_state(state, "route_selected")
        edges_data = req.metadata.get("edges", [])
        edges = [Edge(**e) if isinstance(e, dict) else e for e in edges_data]
        route_req = RouteRequest(
            request_id=req.idempotency_key,
            edges=edges,
            source=req.metadata.get("source", "A"),
            target=req.metadata.get("target", "B"),
            allow_negative=True,
        )
        route_resp = None
        try:
            if self.routing_client:
                route_resp = self.routing_client.route(route_req)
        except Exception:
            state = AppointmentState.FAILED
            resp = AppointmentResponse(
                appointment_id=req.idempotency_key,
                state=state,
                repeated=False,
            )
            self.idempotency_store.put(req.idempotency_key, resp.dict())
            return resp

        # Booking
        state = advance_state(state, "provider_reserved")
        booking_result = None
        try:
            if self.booking_client:
                booking_result = self.booking_client.book(req)
        except Exception:
            state = AppointmentState.FAILED
            resp = AppointmentResponse(
                appointment_id=req.idempotency_key,
                state=state,
                repeated=False,
            )
            self.idempotency_store.put(req.idempotency_key, resp.dict())
            # Outbox failure event
            ev = OutboxEvent(
                appointment_id=req.idempotency_key,
                event_type="appointment_failed",
                payload={},
            )
            self.outbox.add(ev)
            return resp

        # Finalize
        state = advance_state(state, "book_success")
        response_data = {
            "appointment_id": booking_result.get("appointment_id") if isinstance(booking_result, dict) else req.idempotency_key,
            "state": state,
            "route_path": getattr(route_resp, "path", None) if route_resp else None,
            "route_cost": getattr(route_resp, "cost", None) if route_resp else None,
            "repeated": False,
        }
        self.idempotency_store.put(req.idempotency_key, response_data)

        # Outbox event
        ev = OutboxEvent(
            appointment_id=response_data["appointment_id"],
            event_type="appointment_confirmed",
            payload={"route": getattr(route_resp, "path", None)},
        )
        self.outbox.add(ev)
        log_with_mask(
            self.logger,
            "appointment_confirmed",
            request_id=req.idempotency_key,
            appointment_id=response_data["appointment_id"],
            route_path=response_data["route_path"],
            route_cost=response_data["route_cost"],
            outbox_event_id=ev.id,
        )

        return AppointmentResponse(**response_data)


def reconcile_outbox(outbox: InMemoryOutbox, dispatcher) -> int:
    """Dispatch pending outbox events; returns count dispatched."""
    count = 0
    for ev in outbox.get_pending():
        dispatcher(ev)
        outbox.mark_dispatched(ev.id)
        count += 1
    return count
