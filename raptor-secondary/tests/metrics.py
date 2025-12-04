from __future__ import annotations

import json
from typing import Dict, Any
from threading import Lock

_data: Dict[str, Dict[str, Any]] = {}
_lock = Lock()


def record(test_name: str, **kwargs):
    with _lock:
        _data.setdefault(test_name, {}).update(kwargs)


def all_data() -> Dict[str, Dict[str, Any]]:
    with _lock:
        return dict(_data)


def export(path):
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2)
