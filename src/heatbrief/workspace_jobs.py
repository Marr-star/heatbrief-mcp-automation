import json
from datetime import UTC, datetime

from heatbrief.errors import HeatBriefError
from heatbrief.store import Store


def now():
    return datetime.now(UTC).isoformat()


class JobStore(Store):
    def __init__(self, directory):
        super().__init__(directory)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS workspace_jobs (
                id TEXT PRIMARY KEY, state TEXT NOT NULL, payload TEXT NOT NULL
            )""")

    def create_job(self, request):
        job = {
            "id": request.request_id,
            "state": "queued",
            "request": request.model_dump(mode="json"),
            "created_at": now(),
            "events": [{"title": "Request received", "at": now()}],
            "result": None,
            "error": None,
            "elapsed_ms": None,
            "execution_id": None,
        }
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO workspace_jobs VALUES (?, ?, ?)",
                (job["id"], job["state"], json.dumps(job)),
            )
        return job

    def get_job(self, job_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM workspace_jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise HeatBriefError("not_found", "Workflow run not found", 404)
        return json.loads(row[0])

    def latest_job(self):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM workspace_jobs ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
        return json.loads(row[0]) if row else None

    def update_job(self, job_id, *, event=None, **updates):
        job = self.get_job(job_id)
        job.update(updates)
        if event:
            job["events"].append({"title": event, "at": now()})
        with self.connect() as db:
            db.execute(
                "UPDATE workspace_jobs SET state=?, payload=? WHERE id=?",
                (job["state"], json.dumps(job, allow_nan=False), job_id),
            )
        return job

    def recover_interrupted(self):
        with self.connect() as db:
            rows = db.execute(
                "SELECT id FROM workspace_jobs WHERE state IN ('queued','running')"
            ).fetchall()
        for (job_id,) in rows:
            self.update_job(
                job_id,
                state="failed",
                event="Run interrupted",
                error={
                    "error": "interrupted",
                    "message": "This run was interrupted. Retry the same request.",
                },
            )
