"""Phase 4: SQLite intent-keyed catalog.

Persistent L0 cache for `LocatorResolver`. Replaces the substring-keyed
JSONL HealingCatalog for the intent-cache use case (the legacy
error-pattern catalog stays in `healing_catalog.py` for L2/L3 matching).

Schema:

    CREATE TABLE intent_resolutions (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        intent_text          TEXT NOT NULL,
        url_signature        TEXT NOT NULL,
        action               TEXT NOT NULL,
        resolved_call        TEXT NOT NULL,
        resolved_selector    TEXT,
        confidence           REAL DEFAULT 1.0,
        usage_count          INTEGER DEFAULT 0,
        success_count        INTEGER DEFAULT 0,
        last_used            TEXT,
        created_at           TEXT NOT NULL,
        attributes_at_record TEXT,
        attributes_at_heal   TEXT,
        status               TEXT DEFAULT 'active',
        UNIQUE(intent_text, url_signature, action)
    );

URL normalisation collapses numeric path segments and query strings so
the same intent on `/users/123` and `/users/456` share one cache row.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = ".testforge/intent_catalog.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS intent_resolutions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_text          TEXT NOT NULL,
    url_signature        TEXT NOT NULL,
    action               TEXT NOT NULL,
    resolved_call        TEXT NOT NULL,
    resolved_selector    TEXT,
    confidence           REAL DEFAULT 1.0,
    usage_count          INTEGER DEFAULT 0,
    success_count        INTEGER DEFAULT 0,
    last_used            TEXT,
    created_at           TEXT NOT NULL,
    attributes_at_record TEXT,
    attributes_at_heal   TEXT,
    status               TEXT DEFAULT 'active',
    UNIQUE(intent_text, url_signature, action)
);
CREATE INDEX IF NOT EXISTS idx_intent ON intent_resolutions(intent_text);
CREATE INDEX IF NOT EXISTS idx_lookup ON intent_resolutions(intent_text, url_signature, action);

CREATE TABLE IF NOT EXISTS legacy_recipes (
    recipe_id        TEXT PRIMARY KEY,
    trigger_family   TEXT,
    trigger_code     TEXT,
    trigger_pattern  TEXT,
    trigger_framework TEXT,
    solution_strategy TEXT,
    solution_selector TEXT,
    solution_js      TEXT,
    priority         INTEGER DEFAULT 0,
    usage_count      INTEGER DEFAULT 0,
    success_count    INTEGER DEFAULT 0,
    last_used        TEXT,
    status           TEXT DEFAULT 'active',
    created_at       TEXT
);
"""


_NUMERIC_PATH = re.compile(r"/\d+(?=/|$)")
_UUID_PATH = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)"
)


def normalize_url(url: str) -> str:
    """Collapse numeric IDs, UUIDs, queries, and fragments to a stable signature.

    Examples:
        https://app/users/123/edit?tab=1#x → host=app path=/users/*/edit
        http://localhost:8765/             → host=localhost:8765 path=/
    """
    if not url:
        return "host= path=/"
    try:
        u = urlparse(url)
    except Exception:
        return f"host= path={url}"
    host = u.hostname or ""
    if u.port and u.port not in (80, 443):
        host = f"{host}:{u.port}"
    path = u.path or "/"
    path = _UUID_PATH.sub("/*", path)
    path = _NUMERIC_PATH.sub("/*", path)
    return f"host={host} path={path}"


@dataclass
class IntentResolution:
    intent_text: str
    url_signature: str
    action: str
    resolved_call: str
    resolved_selector: str = ""
    confidence: float = 1.0
    usage_count: int = 0
    success_count: int = 0
    last_used: str = ""
    created_at: str = ""
    attributes_at_record: dict = field(default_factory=dict)
    attributes_at_heal: dict = field(default_factory=dict)
    status: str = "active"

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "IntentResolution":
        def _loads(s: Optional[str]) -> dict:
            if not s:
                return {}
            try:
                return json.loads(s)
            except Exception:
                return {}
        return cls(
            intent_text=row["intent_text"],
            url_signature=row["url_signature"],
            action=row["action"],
            resolved_call=row["resolved_call"],
            resolved_selector=row["resolved_selector"] or "",
            confidence=row["confidence"] or 0.0,
            usage_count=row["usage_count"] or 0,
            success_count=row["success_count"] or 0,
            last_used=row["last_used"] or "",
            created_at=row["created_at"] or "",
            attributes_at_record=_loads(row["attributes_at_record"]),
            attributes_at_heal=_loads(row["attributes_at_heal"]),
            status=row["status"] or "active",
        )


class IntentCatalog:
    """SQLite-backed intent-keyed cache for LocatorResolver."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    def lookup(self, intent_text: str, url: str, action: str) -> Optional[IntentResolution]:
        """Return the most-trusted active resolution, or None."""
        sig = normalize_url(url)
        cur = self._conn.execute(
            """
            SELECT * FROM intent_resolutions
            WHERE intent_text = ? AND url_signature = ? AND action = ?
              AND status = 'active'
            ORDER BY confidence DESC, success_count DESC, last_used DESC
            LIMIT 1
            """,
            (intent_text, sig, action),
        )
        row = cur.fetchone()
        return IntentResolution.from_row(row) if row else None

    def record_success(
        self,
        intent_text: str,
        url: str,
        action: str,
        resolved_call: str,
        resolved_selector: str = "",
        attributes_at_record: Optional[dict] = None,
    ) -> None:
        """Insert or bump an entry after a successful resolve."""
        sig = normalize_url(url)
        now = datetime.now(timezone.utc).isoformat()
        attrs_json = json.dumps(attributes_at_record or {}, ensure_ascii=False)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO intent_resolutions
                    (intent_text, url_signature, action, resolved_call,
                     resolved_selector, confidence, usage_count, success_count,
                     last_used, created_at, attributes_at_record, status)
                VALUES (?, ?, ?, ?, ?, 1.0, 1, 1, ?, ?, ?, 'active')
                ON CONFLICT(intent_text, url_signature, action) DO UPDATE SET
                    resolved_call    = excluded.resolved_call,
                    resolved_selector= excluded.resolved_selector,
                    usage_count      = usage_count + 1,
                    success_count    = success_count + 1,
                    last_used        = excluded.last_used,
                    confidence       = MIN(1.0, confidence + 0.05)
                """,
                (intent_text, sig, action, resolved_call,
                 resolved_selector, now, now, attrs_json),
            )

    def record_heal(
        self,
        intent_text: str,
        url: str,
        action: str,
        new_call: str,
        attributes_at_heal: Optional[dict] = None,
    ) -> None:
        """Update an existing entry after a healing event changed the call."""
        sig = normalize_url(url)
        now = datetime.now(timezone.utc).isoformat()
        attrs_json = json.dumps(attributes_at_heal or {}, ensure_ascii=False)
        with self._conn:
            self._conn.execute(
                """
                UPDATE intent_resolutions
                SET resolved_call = ?,
                    attributes_at_heal = ?,
                    last_used = ?,
                    usage_count = usage_count + 1,
                    confidence = MAX(0.1, confidence - 0.1)
                WHERE intent_text = ? AND url_signature = ? AND action = ?
                """,
                (new_call, attrs_json, now, intent_text, sig, action),
            )

    def record_failure(self, intent_text: str, url: str, action: str) -> None:
        """Decrement confidence; mark stale below 0.2."""
        sig = normalize_url(url)
        with self._conn:
            self._conn.execute(
                """
                UPDATE intent_resolutions
                SET confidence = confidence - 0.2,
                    usage_count = usage_count + 1
                WHERE intent_text = ? AND url_signature = ? AND action = ?
                """,
                (intent_text, sig, action),
            )
            self._conn.execute(
                """
                UPDATE intent_resolutions SET status = 'stale'
                WHERE confidence < 0.2 AND status = 'active'
                """
            )

    # ------------------------------------------------------------------
    def count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM intent_resolutions")
        return cur.fetchone()[0]

    def export_jsonl(self, path: str) -> int:
        """Dump active rows to JSONL for human review or git tracking."""
        cur = self._conn.execute(
            "SELECT * FROM intent_resolutions WHERE status = 'active'"
        )
        n = 0
        with open(path, "w", encoding="utf-8") as f:
            for row in cur:
                obj = {k: row[k] for k in row.keys()}
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                n += 1
        return n

    def import_legacy_recipes(self, jsonl_path: str) -> int:
        """Bulk-import the JSONL error-pattern recipes into legacy_recipes table."""
        if not os.path.exists(jsonl_path):
            return 0
        n = 0
        with self._conn:
            with open(jsonl_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self._conn.execute(
                        """
                        INSERT OR REPLACE INTO legacy_recipes
                            (recipe_id, trigger_family, trigger_code,
                             trigger_pattern, trigger_framework,
                             solution_strategy, solution_selector, solution_js,
                             priority, usage_count, success_count,
                             last_used, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            r.get("recipe_id", ""),
                            r.get("trigger_family", ""),
                            r.get("trigger_code", ""),
                            r.get("trigger_pattern", ""),
                            r.get("trigger_framework", ""),
                            r.get("solution_strategy", ""),
                            r.get("solution_selector", ""),
                            r.get("solution_js", ""),
                            int(r.get("priority", 0) or 0),
                            int(r.get("usage_count", 0) or 0),
                            int(r.get("success_count", 0) or 0),
                            r.get("last_used", ""),
                            r.get("status", "active"),
                            r.get("created_at", ""),
                        ),
                    )
                    n += 1
        logger.info("Imported %d legacy recipes from %s", n, jsonl_path)
        return n

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
