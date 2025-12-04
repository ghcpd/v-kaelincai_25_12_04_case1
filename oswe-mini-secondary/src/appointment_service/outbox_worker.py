import time
from .db import SimpleDB
from .adapter import CalendarAdapter, TransientError, PermanentError
from .logger import structured


class OutboxWorker:
    def __init__(self, db: SimpleDB, adapter: CalendarAdapter, max_attempts: int = 3, backoff_seconds: float = 0.2):
        self.db = db
        self.adapter = adapter
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds

    def run_once(self):
        items = self.db.fetch_pending_outbox(limit=20)
        for item in items:
            outbox_id = item['id']
            appt_id = item['appointment_id']
            event_type = item['event_type']
            payload = item['payload']
            attempts = item['attempts']
            if attempts >= self.max_attempts:
                # permanent failure — mark appointment failed and ack outbox
                self.db.update_appointment_status(appt_id, 'FAILED')
                self.db.mark_outbox_attempt(outbox_id, success=True)
                structured('error', 'outbox_failed_max', appointment_id=appt_id, outbox_id=outbox_id)
                continue

            try:
                structured('debug', 'outbox_deliver_attempt', appointment_id=appt_id, outbox_id=outbox_id, attempt=attempts + 1)
                payload_obj = {} if payload is None else payload
                if isinstance(payload_obj, str):
                    # stored JSON string
                    import json

                    payload_obj = json.loads(payload_obj)

                res = self.adapter.schedule(payload_obj)
                if res.get('status') == 'ok':
                    self.db.update_appointment_status(appt_id, 'SCHEDULED')
                    self.db.mark_outbox_attempt(outbox_id, success=True)
                    structured('info', 'outbox_delivered', appointment_id=appt_id, outbox_id=outbox_id)
                else:
                    # transient
                    raise TransientError('not-ok')
            except TransientError:
                self.db.mark_outbox_attempt(outbox_id, success=False)
                time.sleep(self.backoff_seconds * (attempts + 1))
                structured('warning', 'outbox_transient', appointment_id=appt_id, outbox_id=outbox_id, attempts=attempts + 1)
            except PermanentError:
                # treat as permanent
                self.db.mark_outbox_attempt(outbox_id, success=False)
                structured('error', 'outbox_permanent', appointment_id=appt_id, outbox_id=outbox_id)
