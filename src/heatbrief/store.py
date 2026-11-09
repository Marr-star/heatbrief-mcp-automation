import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from heatbrief.errors import HeatBriefError


class Store:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "heatbrief.sqlite3"
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS briefings (
                request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                lease_expires REAL NOT NULL, result TEXT
            )""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def fingerprint(request, mode):
        payload = {"request": request.model_dump(mode="json"), "provider_mode": mode}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()

    def claim(self, request, mode):
        fingerprint = self.fingerprint(request, mode)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT fingerprint, lease_expires, result FROM briefings WHERE request_id=?",
                (request.request_id,),
            ).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise HeatBriefError(
                        "idempotency_conflict",
                        "Request ID already used with different content",
                        409,
                    )
                if row[2]:
                    return json.loads(row[2])
                if row[1] > time.time():
                    raise HeatBriefError("request_in_progress", "This request is processing", 409)
            db.execute(
                "INSERT OR REPLACE INTO briefings VALUES (?, ?, ?, NULL)",
                (request.request_id, fingerprint, time.time() + 90),
            )
        return None

    def complete(self, request_id, result):
        with self.connect() as db:
            db.execute(
                "UPDATE briefings SET result=?, lease_expires=0 WHERE request_id=?",
                (json.dumps(result, allow_nan=False), request_id),
            )

    def release(self, request_id):
        with self.connect() as db:
            db.execute("DELETE FROM briefings WHERE request_id=? AND result IS NULL", (request_id,))

    def get(self, request_id):
        with self.connect() as db:
            row = db.execute(
                "SELECT result FROM briefings WHERE request_id=? AND result IS NOT NULL",
                (request_id,),
            ).fetchone()
        if not row:
            raise HeatBriefError("not_found", "Completed briefing not found", 404)
        return json.loads(row[0])

    def review(self, request_id, review):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT result FROM briefings WHERE request_id=? AND result IS NOT NULL",
                (request_id,),
            ).fetchone()
            if not row:
                raise HeatBriefError("not_found", "Completed briefing not found", 404)
            result = json.loads(row[0])
            previous = result.get("review")
            if previous:
                if (previous["decision"], previous["reviewer"]) == (
                    review["decision"],
                    review["reviewer"],
                ):
                    return result
                raise HeatBriefError("review_conflict", "Briefing has already been reviewed", 409)
            result["review"] = review
            result["status"] = (
                "approved_for_manual_send" if review["decision"] == "approve" else "rejected"
            )
            db.execute(
                "UPDATE briefings SET result=? WHERE request_id=?",
                (json.dumps(result, allow_nan=False), request_id),
            )
            return result
