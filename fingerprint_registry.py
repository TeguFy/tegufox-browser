"""
Tegufox Fingerprint Registry

SQLite-backed store for fingerprint hashes a profile has emitted. Used by the
consistency engine's anti-correlation check: if two profiles share the same
canvas or webgl hash on the same domain, they've collided and the bot-defence
correlation heuristics will treat them as the same actor.

Schema is append-only — each time a browser session hits a domain and
produces a fingerprint, call `record()`. Hash values are client-provided
(usually SHA-256 of the raw surface).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

DEFAULT_DB_PATH = Path("tegufox-profile/fingerprints.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,
    domain TEXT,
    hash_canvas TEXT,
    hash_webgl TEXT,
    hash_tls_ja3 TEXT,
    seen_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_profile ON fingerprints(profile_name);
CREATE INDEX IF NOT EXISTS idx_hash_canvas ON fingerprints(hash_canvas);
CREATE INDEX IF NOT EXISTS idx_hash_webgl ON fingerprints(hash_webgl);
CREATE INDEX IF NOT EXISTS idx_hash_ja3 ON fingerprints(hash_tls_ja3);
"""


class FingerprintRegistry:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "FingerprintRegistry":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def record(
        self,
        profile_name: str,
        domain: Optional[str] = None,
        hash_canvas: Optional[str] = None,
        hash_webgl: Optional[str] = None,
        hash_tls_ja3: Optional[str] = None,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO fingerprints
                (profile_name, domain, hash_canvas, hash_webgl, hash_tls_ja3, seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (profile_name, domain, hash_canvas, hash_webgl, hash_tls_ja3, time.time()),
        )
        self._conn.commit()
        return cursor.lastrowid

    def find_collisions(
        self,
        profile_name: str,
        hash_canvas: Optional[str] = None,
        hash_webgl: Optional[str] = None,
        hash_tls_ja3: Optional[str] = None,
    ) -> List[str]:
        """Return distinct profile_names (other than `profile_name`) sharing any
        of the supplied hashes. Hashes that are None are ignored."""
        conditions = []
        params: list = []
        for col, val in (
            ("hash_canvas", hash_canvas),
            ("hash_webgl", hash_webgl),
            ("hash_tls_ja3", hash_tls_ja3),
        ):
            if val is not None:
                conditions.append(f"{col} = ?")
                params.append(val)

        if not conditions:
            return []

        where = " OR ".join(conditions)
        params.append(profile_name)

        rows = self._conn.execute(
            f"""
            SELECT DISTINCT profile_name
            FROM fingerprints
            WHERE ({where}) AND profile_name != ?
            """,
            params,
        ).fetchall()
        return [row["profile_name"] for row in rows]

    def find_collisions_for_profile(self, profile: dict) -> List[str]:
        """Convenience: look up a profile's declared fingerprint hashes from
        its `fingerprints` section and check for collisions."""
        fp = profile.get("fingerprints") or {}
        return self.find_collisions(
            profile_name=profile.get("name", ""),
            hash_canvas=fp.get("canvas"),
            hash_webgl=fp.get("webgl"),
            hash_tls_ja3=fp.get("ja3"),
        )

    def list_for_profile(self, profile_name: str) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM fingerprints WHERE profile_name = ? ORDER BY seen_at DESC",
            (profile_name,),
        ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM fingerprints").fetchone()[0]

    def export_json(self, output_path: Path) -> int:
        rows = self._conn.execute(
            "SELECT * FROM fingerprints ORDER BY id"
        ).fetchall()
        data = [dict(row) for row in rows]
        Path(output_path).write_text(json.dumps(data, indent=2))
        return len(data)

    def clear(self) -> None:
        self._conn.execute("DELETE FROM fingerprints")
        self._conn.commit()
