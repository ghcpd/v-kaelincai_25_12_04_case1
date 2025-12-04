from __future__ import annotations

import time
from typing import Dict
from fastapi import FastAPI, HTTPException
from appointments.models import RouteRequest, RouteResponse, AppointmentCreateRequest
from appointments.routing_algo import bellman_ford


class MockBackend:
    def __init__(self):
        self.scenario_by_key: Dict[str, str] = {}
        self.route_calls: Dict[str, int] = {}
        self.booking_calls: Dict[str, int] = {}

    def _scenario(self, key: str) -> str:
        return self.scenario_by_key.get(key, "immediate")

    def route(self, req: RouteRequest) -> RouteResponse:
        key = req.request_id
        scenario = self._scenario(key)
        self.route_calls[key] = self.route_calls.get(key, 0) + 1

        if scenario == "routing_slow":
            time.sleep(0.6)  # trigger timeout in client
        elif scenario == "routing_fail_once":
            if self.route_calls[key] == 1:
                raise Exception("transient routing failure")
        # compute path
        path, cost = bellman_ford(req.edges, req.source, req.target)
        return RouteResponse(path=path, cost=cost, validated=True)

    def book(self, req: AppointmentCreateRequest):
        key = req.idempotency_key
        scenario = self._scenario(key)
        self.booking_calls[key] = self.booking_calls.get(key, 0) + 1

        if scenario == "booking_fail_once":
            if self.booking_calls[key] == 1:
                raise Exception("booking temporary failure")
        elif scenario == "booking_always_fail":
            raise Exception("booking failure")
        elif scenario == "booking_delayed":
            time.sleep(0.5)

        return {"appointment_id": f"appt-{key}"}


def create_app(backend: MockBackend) -> FastAPI:
    app = FastAPI()

    @app.post("/route")
    def route(req: RouteRequest):
        try:
            return backend.route(req)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/v2/appointments")
    def book(req: AppointmentCreateRequest):
        try:
            return backend.book(req)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app
