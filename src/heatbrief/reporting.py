import html
import re

from heatbrief.statistics import extrema_narrative


def text(value):
    """Keep user labels and questions literal when embedded in Markdown."""
    value = html.escape(str(value)).replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def narrative(comparison, focus="both"):
    return extrema_narrative(comparison, focus)


def render_report(request, comparison, readings, limitations):
    label = "Mock data — fictional demonstration" if comparison["mock"] else "Live data"
    lines = [
        "# HeatBrief | Temperature comparison",
        "",
        f"**{label}**",
        "",
        f"Request: `{request.request_id}` · Client: {text(request.client_name)}",
        f"Requested time: {request.timestamp.isoformat()} ({text(request.timezone)})",
        "",
        f"Business question: {text(request.question)}",
        "",
        "## Finding",
        "",
        text(narrative(comparison)),
        "",
        f"Temperature spread among available readings: {comparison['spread_c']:.1f} °C.",
        f"Coverage: {len(comparison['ranking'])}/{len(request.locations)} locations.",
        "",
        "## Evidence",
        "",
        "| Location | Coordinates | Temperature | Observed at | Source / evidence ID |",
        "|---|---|---|---|---|",
    ]
    for row in readings:
        value = row.get("temperature_c")
        temperature = f"{value:.1f} °C" if value is not None else "Unavailable"
        coordinates = f"{row['latitude']}, {row['longitude']}"
        lines.append(
            f"| {text(row['name'])} | {coordinates} | {temperature} | "
            f"{text(row.get('observed_at', 'Unavailable'))} | "
            f"{text(row.get('source', row.get('issue', 'Unavailable')))} / "
            f"{text(row.get('source_id', 'none'))} |"
        )
    lines += ["", "## Limitations", ""] + [f"- {text(item)}" for item in limitations]
    return "\n".join(lines) + "\n"


def render_draft(request, comparison):
    label = "[MOCK DATA] " if comparison["mock"] else ""
    incomplete = (
        "This comparison is incomplete; please review missing readings.\n\n"
        if comparison["incomplete"]
        else ""
    )
    return (
        "Status: DRAFT — HUMAN REVIEW REQUIRED\n"
        f"Subject: {label}Temperature comparison briefing\n\n"
        f"Hello {request.client_name},\n\n{label}{narrative(comparison)}\n"
        f"Requested time: {request.timestamp.isoformat()} ({request.timezone}).\n\n"
        f"{incomplete}Please review the attached briefing for sources and limitations. "
        "Temperature alone does not establish outdoor work or event safety.\n\n"
        "Prepared for review; no message has been sent.\n"
    )
