import json
import logging
from typing import Any, Dict

handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
log = logging.getLogger("appointment_service")
log.setLevel(logging.DEBUG)
log.handlers = [handler]


def structured(level: str, event: str, request_id: str | None = None, appointment_id: str | None = None, **extra: Any) -> None:
    payload: Dict[str, Any] = {
        "event": event,
        "level": level,
        "request_id": request_id,
        "appointment_id": appointment_id,
    }
    payload.update(extra)
    # Mask sensitive fields if present
    if "sensitive" in payload:
        payload["sensitive"] = "***MASKED***"
    log.log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload))
