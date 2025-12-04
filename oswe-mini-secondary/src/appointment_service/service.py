from typing import Optional, Dict
from .db import SimpleDB
from .adapter import CalendarAdapter, TransientError, PermanentError
from .logger import structured


class AppointmentService:
    def __init__(self, db: SimpleDB, adapter: CalendarAdapter):
        self.db = db
        self.adapter = adapter

    def create_appointment(self, request_id: str, user_id: str, start_time: str, end_time: str, metadata: Dict[str, object], auto_schedule: bool = True) -> str:
        structured("info", "create_attempt", request_id=request_id, user_id=user_id)
        appt_id = self.db.create_appointment(request_id, user_id, start_time, end_time, metadata)
        # push initial event
        self.db.push_outbox(appt_id, "appointment.created", {"request_id": request_id})

        if auto_schedule:
            try:
                self._attempt_schedule(appt_id, metadata)
            except TransientError:
                # Let outbox worker retry later
                structured("warning", "schedule_transient", request_id=request_id, appointment_id=appt_id)
            except PermanentError:
                self.db.update_appointment_status(appt_id, "FAILED")
                self.db.push_outbox(appt_id, "appointment.failed", {"request_id": request_id})
                structured("error", "schedule_permanent", request_id=request_id, appointment_id=appt_id)

        return appt_id

    def _attempt_schedule(self, appt_id: str, metadata: Dict[str, object]) -> None:
        # call calendar adapter synchronously for prototype; if it fails we'll rely on outbox
        payload = {"appointment_id": appt_id, **metadata}
        res = self.adapter.schedule(payload)
        # success path
        if res.get("status") == "ok":
            self.db.update_appointment_status(appt_id, "SCHEDULED")
            self.db.push_outbox(appt_id, "appointment.scheduled", payload)
            structured("info", "scheduled", appointment_id=appt_id)
        else:
            # treat any other response as transient for now
            raise TransientError("not-ok")
