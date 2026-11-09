"""Start an isolated localhost n8n demo and configure the real HeatBrief workflow."""

import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".automation"
CONFIG = LOCAL / "local-config.json"
N8N_VERSION = "2.46.6"
N8N = LOCAL / "runtime/node_modules/n8n/bin/n8n"
BASE_URL = "http://localhost:5678"


def runtime_environment():
    return {
        **os.environ,
        "N8N_USER_FOLDER": str(LOCAL / "state"),
        "N8N_HOST": "localhost",
        "N8N_LISTEN_ADDRESS": "127.0.0.1",
        "N8N_PORT": "5678",
        "N8N_PROTOCOL": "http",
        "N8N_EDITOR_BASE_URL": BASE_URL,
        "N8N_WEBHOOK_URL": BASE_URL + "/",
        # This new instance is bound to loopback and uses local HTTP only.
        "N8N_SECURE_COOKIE": "false",
        "N8N_DIAGNOSTICS_ENABLED": "false",
        "N8N_VERSION_NOTIFICATIONS_ENABLED": "false",
        "N8N_RUNNERS_MODE": "internal",
        "PYTHONIOENCODING": "utf-8",
        "NO_PROXY": "localhost,127.0.0.1,::1",
    }


def write_config(config):
    CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")


def available(client, url):
    try:
        return client.get(url, timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


def wait_ready(client, url, process, timeout=75):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Service exited. Check .automation/logs for details.")
        if available(client, url):
            return
        time.sleep(1)
    raise RuntimeError("Service did not become ready. Check .automation/logs for details.")


def background(arguments, name, env):
    logs = LOCAL / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / f"{name}.log").open("ab") as output:
        return subprocess.Popen(
            arguments,
            cwd=ROOT,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )


def wait_webhook(client):
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        response = client.post(BASE_URL + "/webhook/heatbrief", json={})
        if response.status_code in (401, 403):
            return
        time.sleep(1)
    raise RuntimeError("The published webhook is not ready. See .automation/logs/n8n.log")


def cli(node, arguments, env):
    result = subprocess.run(
        [node, str(N8N), *arguments],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    with (LOCAL / "logs/setup.log").open("a", encoding="utf-8") as output:
        output.write(result.stdout + "\n")
    if result.returncode:
        raise RuntimeError(f"n8n {arguments[0]} failed. See .automation/logs/setup.log")
    if arguments[0].startswith("import:") and "Successfully imported" not in result.stdout:
        raise RuntimeError(f"n8n {arguments[0]} was not imported. See .automation/logs/setup.log")


def main():
    LOCAL.mkdir(parents=True, exist_ok=True)
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Install Node.js 24 or newer first.")
    if not N8N.exists():
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise RuntimeError("npm is required to install the local n8n runtime.")
        print(f"Installing project-local n8n {N8N_VERSION}...", flush=True)
        subprocess.run(
            [
                npm,
                "install",
                "--prefix",
                str(LOCAL / "runtime"),
                f"n8n@{N8N_VERSION}",
                "--omit=dev",
                "--no-fund",
                "--no-audit",
                "--registry=https://registry.npmjs.org",
            ],
            check=True,
            cwd=ROOT,
        )

    config = (
        json.loads(CONFIG.read_text())
        if CONFIG.exists()
        else {
            "owner_email": "demo@heatbrief.test",
            "owner_password": secrets.token_urlsafe(24) + "aA9!",
            "webhook_key": secrets.token_hex(32),
            "workflow_id": "heatbriefDemo001",
            "configured": False,
        }
    )
    write_config(config)
    local_env = dotenv_values(ROOT / ".env")
    if not local_env.get("HEATBRIEF_API_TOKEN"):
        raise RuntimeError("Configure the local .env API token before starting automation.")
    env = runtime_environment()
    with httpx.Client(trust_env=False, timeout=30) as client:
        if not available(client, "http://127.0.0.1:8000/health"):
            api = background(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "heatbrief.api:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--env-file",
                    ".env",
                ],
                "heatbrief-api",
                env,
            )
            wait_ready(client, "http://127.0.0.1:8000/health", api)
            config["api_pid"] = api.pid

        n8n_process = None
        if not available(client, BASE_URL + "/healthz"):
            n8n_process = background([node, str(N8N), "start"], "n8n", env)
            wait_ready(client, BASE_URL + "/healthz", n8n_process)
            config["n8n_pid"] = n8n_process.pid
        elif not config["configured"]:
            raise RuntimeError(
                "Port 5678 is already in use. Stop that instance before initial setup."
            )

        if not config["configured"]:
            print("Configuring the isolated local n8n owner and workflow...", flush=True)
            response = client.post(
                BASE_URL + "/rest/owner/setup",
                json={
                    "email": config["owner_email"],
                    "firstName": "HeatBrief",
                    "lastName": "Demo",
                    "password": config["owner_password"],
                },
            )
            if response.status_code not in (200, 201):
                # A previous interrupted setup may already have created this same local owner.
                login = client.post(
                    BASE_URL + "/rest/login",
                    json={
                        "emailOrLdapLoginId": config["owner_email"],
                        "password": config["owner_password"],
                    },
                )
                if login.status_code != 200:
                    raise RuntimeError(f"Local owner setup failed ({response.status_code}).")
            assert n8n_process is not None
            n8n_process.terminate()
            n8n_process.wait(timeout=30)

            credentials = [
                {
                    "id": "heatbriefWebhook",
                    "name": "HeatBrief webhook key",
                    "type": "httpHeaderAuth",
                    "data": {"name": "X-HeatBrief-Webhook-Key", "value": config["webhook_key"]},
                },
                {
                    "id": "heatbriefBridge",
                    "name": "HeatBrief API automation token",
                    "type": "httpHeaderAuth",
                    "data": {
                        "name": "Authorization",
                        "value": "Bearer " + local_env["HEATBRIEF_API_TOKEN"],
                    },
                },
            ]
            credentials_path = LOCAL / "import-credentials.json"
            credentials_path.write_text(json.dumps(credentials), encoding="utf-8")
            try:
                cli(node, ["import:credentials", "--input=" + str(credentials_path)], env)
            finally:
                credentials_path.unlink(missing_ok=True)
            workflow = json.loads((ROOT / "workflows/client-briefing.json").read_text())
            workflow.update(id=config["workflow_id"], versionId=str(uuid.uuid4()))
            for name, credential_id, credential_name in [
                ("Receive briefing request", "heatbriefWebhook", "HeatBrief webhook key"),
                ("Create and save briefing", "heatbriefBridge", "HeatBrief API automation token"),
            ]:
                entry = next(item for item in workflow["nodes"] if item["name"] == name)
                entry["credentials"] = {
                    "httpHeaderAuth": {
                        "id": credential_id,
                        "name": credential_name,
                    }
                }
            workflow_path = LOCAL / "import-workflow.json"
            workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
            cli(node, ["import:workflow", "--input=" + str(workflow_path)], env)
            cli(node, ["publish:workflow", "--id=" + config["workflow_id"]], env)
            n8n_process = background([node, str(N8N), "start"], "n8n", env)
            wait_ready(client, BASE_URL + "/healthz", n8n_process)
            config.update(configured=True, n8n_pid=n8n_process.pid)

        wait_webhook(client)
        write_config(config)
        (LOCAL / "local-login.txt").write_text(
            f"LOCAL HEATBRIEF DEMO ONLY\nURL: {BASE_URL}\nEmail: {config['owner_email']}\n"
            f"Password: {config['owner_password']}\n\n"
            "This file is ignored by Git. It is not a FortyGuard or cloud account.\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "automation": "ready",
                    "editor": BASE_URL + "/workflow/" + config["workflow_id"],
                    "test_command": "uv run python scripts/test-automation.py",
                    "local_login_file": ".automation/local-login.txt",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.SubprocessError, httpx.HTTPError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
