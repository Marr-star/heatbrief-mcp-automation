"""Record executed CLI commands as a two-minute asciicast and offline HTML playback."""

import html
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
assets = root / "docs" / "assets"
assets.mkdir(parents=True, exist_ok=True)
events, transcript = [], []
started = time.monotonic()
recording_env = {
    **os.environ,
    "PYTHONIOENCODING": "utf-8",
    "HEATBRIEF_MODE": "mock",
    "HEATBRIEF_DATA_DIR": str(root / "data" / ("recording-" + uuid.uuid4().hex[:8])),
}


def emit(value, clear=False):
    display = ("\x1b[2J\x1b[H" if clear else "") + value
    events.append([round(time.monotonic() - started, 3), "o", display.replace("\n", "\r\n")])
    transcript.append(value)


def at(seconds):
    remaining = seconds - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)


def run(arguments, expected=0):
    emit("$ python -m heatbrief.cli " + " ".join(arguments) + "\n\n")
    process = subprocess.run(
        [sys.executable, "-m", "heatbrief.cli", *arguments],
        cwd=root,
        env=recording_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=65,
    )
    emit(process.stderr + process.stdout + f"\n[exit {process.returncode}]\n")
    if process.returncode != expected:
        raise RuntimeError(f"Unexpected command result: {process.returncode}")


emit(
    "HEATBRIEF | AI temperature analyst + client briefing\n\n"
    "SCRIPTED TERMINAL RECORDING — actual executed commands\n"
    "MOCK DATA: fictional temperatures, no FortyGuard calls.\n"
    "Success -> evidence -> duplicate replay -> graceful failure -> review.\n",
    clear=True,
)
at(8)
emit("1 / MCP discovery + point measurement\n\n", clear=True)
run(["ping"])
at(25)
emit("2 / Compare and save the briefing\n\n", clear=True)
run(["compare", "examples/request.json", "--out", "reports/demo-recording"])
at(45)
emit("3 / Evidence-backed report\n\n", clear=True)
report = (root / "reports/demo-recording/demo-phoenix-001/report.md").read_text(encoding="utf-8")
emit(report)
at(70)
emit("4 / Repeat the request: replay the saved result\n\n", clear=True)
run(["compare", "examples/request.json", "--out", "reports/demo-recording"])
at(90)
emit("5 / Graceful failure: timezone is missing\n\n", clear=True)
run(["compare", "examples/missing-timezone.json"], expected=2)
at(106)
emit("6 / Client handoff\n\n", clear=True)
emit(
    "Report + unsent follow-up are saved once per request ID.\n"
    "Status: draft_pending_review. Human review uses a separate API token.\n"
    "n8n workflow: workflows/client-briefing.json (runtime execution unverified).\n"
    "Live FortyGuard integration: gated until access and schema are verified.\n"
    "Temperature alone does not establish outdoor safety.\n"
)
at(120)
emit("\nDemo complete. No follow-up has been sent.\n")
header = {
    "version": 2,
    "width": 140,
    "height": 46,
    "timestamp": int(time.time() - 120),
    "duration": round(time.monotonic() - started, 3),
    "title": "HeatBrief — Mock MCP demo",
}
(assets / "demo.cast").write_text(
    "\n".join(json.dumps(item) for item in [header, *events]) + "\n", encoding="utf-8"
)
(assets / "demo-transcript.txt").write_text("\n".join(transcript), encoding="utf-8")
data = json.dumps({"events": events, "duration": header["duration"]}).replace("<", "\\u003c")
page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HeatBrief — terminal demo</title><style>body{margin:0;background:#101d2c;color:#eff4f7;font:16px system-ui;padding:32px}main{max-width:1200px;margin:auto}h1{margin:0 0 8px}p{color:#b8c9d7}button,select{padding:9px 14px;margin:0 8px 12px 0;background:#f5ad69;color:#142436;border:0;border-radius:6px;font:inherit}pre{height:65vh;overflow:auto;padding:24px;background:#08121e;border:1px solid #304557;border-radius:12px;font:13px/1.5 Consolas,monospace;white-space:pre}progress{width:100%;accent-color:#f5ad69}small{color:#b8c9d7}</style>
<main><h1>HeatBrief / 2 minute demo</h1><p>Actual CLI commands · Mock data · No outbound messages</p>
<button id="play">Play</button><button id="restart">Restart</button><select id="speed"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select><small id="time">0:00 / 2:00</small><progress id="progress" value="0" max="120"></progress><pre id="terminal"></pre><p>Recorded from the local Python/MCP demo. FortyGuard live calls and n8n runtime execution are unverified.</p></main>
<script id="recording" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('recording').textContent);const terminal=document.getElementById('terminal'),play=document.getElementById('play'),progress=document.getElementById('progress');let cursor=0,index=0,running=false,last=0;
function render(){while(index<data.events.length&&data.events[index][0]<=cursor){let text=data.events[index++][2];if(text.includes('\\x1b[2J'))terminal.textContent='';terminal.textContent+=text.replace(/\\x1b\\[[0-9;]*[A-Za-z]/g,'').replace(/\\r/g,'');terminal.scrollTop=terminal.scrollHeight;}progress.value=cursor;document.getElementById('time').textContent=Math.floor(cursor/60)+':'+String(Math.floor(cursor%60)).padStart(2,'0')+' / 2:00';}
function frame(now){if(running){cursor=Math.min(data.duration,cursor+(now-last)/1000*Number(document.getElementById('speed').value));render();if(cursor>=data.duration){running=false;play.textContent='Play';}}last=now;requestAnimationFrame(frame);}play.onclick=()=>{running=!running;play.textContent=running?'Pause':'Play';};document.getElementById('restart').onclick=()=>{cursor=0;index=0;terminal.textContent='';render();};progress.onclick=e=>{cursor=data.duration*(e.offsetX/progress.clientWidth);index=0;terminal.textContent='';render();};render();requestAnimationFrame(frame);
</script></html>""".replace("__DATA__", data)
(root / "docs" / "demo.html").write_text(page, encoding="utf-8")
print(
    json.dumps(
        {
            "recording": "docs/assets/demo.cast",
            "player": "docs/demo.html",
            "duration_seconds": header["duration"],
            "title": html.unescape(header["title"]),
        }
    )
)
