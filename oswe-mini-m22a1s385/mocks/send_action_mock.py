from __future__ import annotations

import random
from typing import Dict

class FlakySender:
    def __init__(self, fail_rate: float = 0.5):
        self.fail_rate = fail_rate

    def __call__(self, appt) -> Dict[str, bool]:
        if random.random() < self.fail_rate:
            raise RuntimeError('downstream failure')
        return {'ok': True}
