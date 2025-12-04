import sqlite3
import json
from typing import Optional
from uuid import uuid4

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS appointments (
  id TEXT PRIMARY KEY,
  request_id TEXT,
  user_id TEXT,
  start_time TEXT,
  end_time TEXT,
  status TEXT,
  metadata TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_request_id ON appointments(request_id);

CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY,
  appointment_id TEXT,
  event_type TEXT,
  payload TEXT,
  attempts INTEGER DEFAULT 0,
  acked INTEGER DEFAULT 0
);
"""


class SimpleDB:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(DB_SCHEMA)
        self.conn.commit()

    def create_appointment(self, request_id: str, user_id: str, start_time: str, end_time: str, metadata: dict) -> str:
        cur = self.conn.cursor()
        # Idempotency: if request_id exists, return existing
        cur.execute("SELECT id FROM appointments WHERE request_id = ?", (request_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        appt_id = str(uuid4())
        cur.execute(
            "INSERT INTO appointments(id, request_id, user_id, start_time, end_time, status, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
            (appt_id, request_id, user_id, start_time, end_time, 'PENDING', json.dumps(metadata) if metadata else '{}'),
        )
        self.conn.commit()
        return appt_id

    def get_appointment(self, appt_id: str) -> Optional[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM appointments WHERE id = ?", (appt_id,))
        r = cur.fetchone()
        if not r:
            return None
        out = dict(r)
        out['metadata'] = json.loads(out['metadata'] or '{}')
        return out

    def update_appointment_status(self, appt_id: str, status: str) -> None:
        cur = self.conn.cursor()
        cur.execute("UPDATE appointments SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, appt_id))
        self.conn.commit()

    def push_outbox(self, appointment_id: str, event_type: str, payload: dict) -> str:
        cur = self.conn.cursor()
        eid = str(uuid4())
        cur.execute("INSERT INTO outbox(id, appointment_id, event_type, payload, attempts, acked) VALUES (?, ?, ?, ?, 0, 0)", (eid, appointment_id, event_type, json.dumps(payload)))
        self.conn.commit()
        return eid

    def fetch_pending_outbox(self, limit: int = 10):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM outbox WHERE acked = 0 ORDER BY rowid LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def mark_outbox_attempt(self, outbox_id: str, success: bool) -> None:
        cur = self.conn.cursor()
        if success:
            cur.execute("UPDATE outbox SET acked = 1, attempts = attempts + 1 WHERE id = ?", (outbox_id,))
        else:
            cur.execute("UPDATE outbox SET attempts = attempts + 1 WHERE id = ?", (outbox_id,))
        self.conn.commit()
