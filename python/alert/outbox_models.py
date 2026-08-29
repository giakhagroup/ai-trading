import sqlite3
import json
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum

class AlertStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"

class AlertEvent(BaseModel):
    alert_id: Optional[int] = None
    signal_id: str
    destination: str
    payload: Dict[str, Any]
    status: AlertStatus = AlertStatus.PENDING
    retry_count: int = 0
    next_retry_at: int = 0
    created_at: int = 0

class OutboxRepository:
    def __init__(self, db_path: str = "data/outbox.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS outbox_events (
                    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    next_retry_at INTEGER DEFAULT 0,
                    created_at INTEGER DEFAULT 0,
                    UNIQUE(signal_id, destination)
                )
            ''')
            conn.commit()

    def add_event(self, event: AlertEvent) -> bool:
        """Returns True if added, False if duplicate"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO outbox_events 
                    (signal_id, destination, payload, status, created_at, next_retry_at, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.signal_id,
                    event.destination,
                    json.dumps(event.payload),
                    event.status.value,
                    event.created_at or int(time.time()),
                    event.next_retry_at,
                    event.retry_count
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Duplicate signal_id and destination
            return False

    def get_pending_events(self, limit: int = 50) -> List[AlertEvent]:
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT alert_id, signal_id, destination, payload, status, retry_count, next_retry_at, created_at
                FROM outbox_events
                WHERE status IN ('PENDING', 'RETRYING') AND next_retry_at <= ?
                ORDER BY created_at ASC
                LIMIT ?
            ''', (now, limit))
            
            events = []
            for row in cursor.fetchall():
                events.append(AlertEvent(
                    alert_id=row[0],
                    signal_id=row[1],
                    destination=row[2],
                    payload=json.loads(row[3]),
                    status=AlertStatus(row[4]),
                    retry_count=row[5],
                    next_retry_at=row[6],
                    created_at=row[7]
                ))
            return events

    def update_event_status(self, alert_id: int, status: AlertStatus, retry_count: int, next_retry_at: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE outbox_events
                SET status = ?, retry_count = ?, next_retry_at = ?
                WHERE alert_id = ?
            ''', (status.value, retry_count, next_retry_at, alert_id))
            conn.commit()
