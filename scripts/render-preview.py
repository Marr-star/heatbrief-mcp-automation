"""Render an honest SVG preview from the generated sample briefing JSON."""

import html
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sample = json.loads((root / "examples/generated/demo-phoenix-001/briefing.json").read_text())
comparison = sample["comparison"]
rows = []
for index, item in enumerate(sample["measurements"]):
    y = 330 + index * 76
    lowest = item["name"] in comparison["lowest_locations"]
    color = "#78d4b8" if lowest else "#dce6ee"
    rows.append(f'''<g>
<text x="48" y="{y}" fill="{color}" font-size="19">{html.escape(item["name"])}</text>
<text x="48" y="{y + 24}" fill="#a6b8c9" font-size="12">{html.escape(item["source_id"])}</text>
<text x="455" y="{y}" fill="{color}" font-size="25" font-weight="700">{item["temperature_c"]:.1f} °C</text>
<text x="640" y="{y}" fill="#dce6ee" font-size="16">{item["latitude"]}, {item["longitude"]}</text>
<rect x="860" y="{y - 17}" width="195" height="12" rx="6" fill="#263d50"/>
<rect x="860" y="{y - 17}" width="{item["temperature_c"] / 40 * 195:.1f}" height="12" rx="6" fill="{color}"/>
</g>''')
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="670" viewBox="0 0 1120 670" role="img" aria-labelledby="title description">
<title id="title">HeatBrief sample temperature briefing</title>
<desc id="description">Mock data. Tempe Riverside has the lowest temperature at 34.1 Celsius. Three fictional readings, spread 2.6 degrees.</desc>
<rect width="1120" height="670" rx="20" fill="#102334"/>
<g font-family="Segoe UI, Arial, sans-serif">
<text x="40" y="45" fill="#efac72" font-size="15" letter-spacing="3">HEATBRIEF / CLIENT EVIDENCE</text>
<rect x="877" y="22" width="201" height="37" rx="18" fill="#543a28"/>
<text x="899" y="46" fill="#ffd1a8" font-size="16" font-weight="700">MOCK DATA</text>
<text x="40" y="96" fill="#f4f7fa" font-size="31" font-weight="700">Three locations. One traceable comparison.</text>
<text x="40" y="125" fill="#a6b8c9" font-size="16">2025-09-20 · 14:00 America/Phoenix · Fictional client demonstration</text>
<rect x="40" y="154" width="1040" height="104" rx="12" fill="#1c3345"/>
<text x="62" y="184" fill="#a6b8c9" font-size="14">LOWEST TEMPERATURE</text>
<text x="62" y="226" fill="#78d4b8" font-size="32" font-weight="700">34.1 °C</text>
<text x="226" y="222" fill="#f4f7fa" font-size="21">Tempe Riverside</text>
<text x="635" y="184" fill="#a6b8c9" font-size="14">SPREAD</text>
<text x="635" y="226" fill="#f4f7fa" font-size="29">2.6 °C</text>
<text x="880" y="184" fill="#a6b8c9" font-size="14">COVERAGE</text>
<text x="880" y="226" fill="#f4f7fa" font-size="29">3 / 3</text>
<text x="48" y="292" fill="#a6b8c9" font-size="13">LOCATION / EVIDENCE ID</text>
<text x="455" y="292" fill="#a6b8c9" font-size="13">TEMPERATURE</text>
<text x="640" y="292" fill="#a6b8c9" font-size="13">COORDINATES</text>
<text x="860" y="292" fill="#a6b8c9" font-size="13">0–40 °C SCALE</text>
{"".join(rows)}
<path d="M40 544 H1080" stroke="#365064"/>
<text x="40" y="574" fill="#dce6ee" font-size="15">Observed at: 2025-09-20T14:00:00-07:00 · Source: HeatBrief fictional fixture</text>
<text x="40" y="605" fill="#f3bc8d" font-size="15">All values are fictional. Temperature alone does not establish outdoor work or event safety.</text>
<text x="40" y="638" fill="#a6b8c9" font-size="14">Draft pending human review · Live FortyGuard integration is unverified · No follow-up has been sent</text>
</g></svg>"""
output = root / "docs/assets/report-preview.svg"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(svg, encoding="utf-8")
print(output.relative_to(root))
