from __future__ import annotations

from typing import List, Dict


class Outbox:
    def __init__(self):
        self._items: List[Dict] = []

    def push(self, item: Dict):
        self._items.append(item)

    def pop_all(self):
        items = self._items[:]
        self._items = []
        return items
