"""Build and launch the local browser workspace with its existing automation."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8001"


def main():
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("Install Node.js 24+ to build the workspace.")
    web = ROOT / "web"
    if not (web / "node_modules/vite").exists():
        subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=web, check=True)
    sources = [
        *list((web / "src").rglob("*")),
        *list((web / "public").rglob("*")),
        web / "package.json",
        web / "package-lock.json",
        web / "index.html",
        web / "vite.config.ts",
        web / "tsconfig.json",
    ]
    built = web / "dist/index.html"
    if not built.exists() or any(
        path.is_file() and path.stat().st_mtime > built.stat().st_mtime for path in sources
    ):
        subprocess.run([npm, "run", "build"], cwd=web, check=True)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/start-automation.py")], cwd=ROOT, check=True
    )
    local = ROOT / ".automation"
    (local / "logs").mkdir(parents=True, exist_ok=True)
    with httpx.Client(trust_env=False, timeout=2) as client:
        try:
            response = client.get(URL + "/api/status")
            ready = (
                response.status_code == 200
                and response.json().get("service") == "heatbrief-workspace"
            )
        except (httpx.HTTPError, ValueError):
            ready = False
        if not ready:
            with (local / "logs/workspace.log").open("ab") as output:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "heatbrief.workspace:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8001",
                        "--env-file",
                        ".env",
                        "--reload",
                        "--reload-dir",
                        "src/heatbrief",
                    ],
                    cwd=ROOT,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    start_new_session=os.name != "nt",
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
            (local / "workspace-process.json").write_text(
                json.dumps({"pid": process.pid, "url": URL})
            )
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Workspace exited. Check .automation/logs/workspace.log")
                try:
                    if client.get(URL + "/api/status").status_code == 200:
                        ready = True
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            if not ready:
                raise RuntimeError("Workspace did not start. Check .automation/logs/workspace.log")
    print(json.dumps({"workspace": "ready", "url": URL, "mode": "local"}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
