import time
from typing import List

class MockCalendar:
    """A mock calendar server which will respond with a pre-configured sequence.

    Each call pops the next response in the `responses` list. Responses are dicts with:
      - type: 'ok' | 'transient' | 'permanent' | 'delay'
      - delay: optional seconds to sleep to simulate latency
      - payload: optional dict to return on 'ok'
    """

    def __init__(self, responses: List[dict]):
        self.responses = responses.copy()
        self.calls = 0

    def call(self, payload: dict) -> dict:
        self.calls += 1
        if not self.responses:
            # default success
            return {"status": "ok", "payload": payload}
        r = self.responses.pop(0)
        if r.get('delay'):
            time.sleep(r['delay'])
        t = r.get('type', 'ok')
        if t == 'ok':
            return {"status": "ok", "payload": r.get('payload', payload)}
        if t == 'transient':
            # raise a transient exception by direct import so callers can intercept
            from appointment_service.adapter import TransientError

            raise TransientError(r.get('message', 'transient'))
        if t == 'permanent':
            from appointment_service.adapter import PermanentError

            raise PermanentError(r.get('message', 'permanent'))
        return {"status": "ok", "payload": r.get('payload', payload)}
