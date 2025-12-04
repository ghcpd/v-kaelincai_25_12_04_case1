# Simple mock for external calendar API interactions

def create_calendar_event(payload):
    # Simulate deterministic calendar id
    return {"calendar_id": "cal-" + payload.get("user", "x")}


def failing_create_calendar_event(payload):
    raise RuntimeError("calendar service error")


def cancel_calendar_event(payload):
    # Simulate cancel action success
    return {"cancelled": True}
