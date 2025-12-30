"""SQLite-backed structured memory store with recency and decay weighting."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


@dataclass
class MemoryEntry:
    id: int
    kind: str
    content: str
    importance: float
    decay_rate: float
    created_at: datetime
    last_accessed: datetime


class MemoryStore:
    """Persists structured memory entries with decay-aware retrieval."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 1.0,
                    decay_rate REAL NOT NULL DEFAULT 0.01,
                    created_at INTEGER NOT NULL,
                    last_accessed INTEGER NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name TEXT PRIMARY KEY
                );
                """
            )
            conn.commit()

    def _store(self, kind: str, content: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        content = content[:2048]
        now = int(time.time())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memory_entries (kind, content, importance, decay_rate, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (kind, content, importance, decay_rate, now, now),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def store_fact(self, content: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        return self._store("fact", content, importance=importance, decay_rate=decay_rate)

    def store_episode(self, content: str, *, importance: float = 1.0, decay_rate: float = 0.01) -> int:
        return self._store("episode", content, importance=importance, decay_rate=decay_rate)

    def store_open_loop(self, content: str, *, importance: float = 0.5, decay_rate: float = 0.02) -> int:
        return self._store("open_loop", content, importance=importance, decay_rate=decay_rate)

    def forget(self, entry_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def retrieve_relevant(self, query: str, *, limit: int = 5) -> List[MemoryEntry]:
        now = int(time.time())
        tokens = set(query.lower().split())
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, content, importance, decay_rate, created_at, last_accessed
                FROM memory_entries
                ORDER BY last_accessed DESC
                LIMIT 100
                """
            ).fetchall()

        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            age_hours = max(0.0, (now - row[6]) / 3600)
            recency_weight = 1 / (1 + age_hours)
            decay_weight = pow(2.71828, -row[4] * age_hours)
            content_tokens = set(row[2].lower().split())
            overlap = len(tokens & content_tokens)
            score = (row[3] + overlap) * recency_weight * decay_weight
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = [row for _, row in scored[:limit] if _ > 0]
        entry_ids = [row[0] for row in selected]
        self._mark_accessed(entry_ids)
        return [self._row_to_entry(row) for row in selected]

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row[0],
            kind=row[1],
            content=row[2],
            importance=row[3],
            decay_rate=row[4],
            created_at=datetime.fromtimestamp(row[5], tz=timezone.utc),
            last_accessed=datetime.fromtimestamp(row[6], tz=timezone.utc),
        )

    def _mark_accessed(self, entry_ids: Iterable[int]) -> None:
        ids = list(entry_ids)
        if not ids:
            return
        now = int(time.time())
        with self._connect() as conn:
            conn.executemany(
                "UPDATE memory_entries SET last_accessed = ? WHERE id = ?",
                [(now, entry_id) for entry_id in ids],
            )
            conn.commit()

