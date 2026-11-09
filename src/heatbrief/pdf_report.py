"""Print-ready briefing from persisted evidence; no model-generated measurements."""

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from heatbrief.reporting import narrative


def make_pdf(result):
    output = BytesIO()
    styles = getSampleStyleSheet()
    ink, green = colors.HexColor("#183b30"), colors.HexColor("#2d6a4f")
    body = ParagraphStyle(
        "BriefBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=ink,
        spaceAfter=8,
    )
    small = ParagraphStyle("BriefSmall", parent=body, fontSize=8, leading=12)
    heading = ParagraphStyle(
        "BriefHeading",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=19,
        spaceBefore=14,
        spaceAfter=8,
    )
    title = ParagraphStyle("BriefTitle", parent=heading, fontSize=27, leading=32, spaceBefore=0)

    def p(value, style=body):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)

    request, comparison = result["request"], result["comparison"]
    label = "MOCK DATA - FICTIONAL DEMONSTRATION" if comparison["mock"] else "LIVE DATA"
    story = [
        p("HEATBRIEF / CLIENT BRIEFING", small),
        Spacer(1, 7 * mm),
        p("A clearer view of your locations.", title),
        p(label, small),
        Spacer(1, 4 * mm),
        p(f"Prepared for {request['client_name']}"),
        p(request["question"]),
        p(f"Requested: {request['date']} at {request['time']} ({request['timezone']})", small),
        p(f"Request ID: {result['request_id']}", small),
        p("Comparison", heading),
        p(narrative(comparison)),
        p(
            f"Spread: {comparison['spread_c']:.1f} °C | "
            f"Coverage: {len(comparison['ranking'])}/{len(request['locations'])} sites",
            small,
        ),
    ]
    rows = [[p("LOCATION", small), p("TEMPERATURE", small), p("COORDINATES", small)]]
    for item in result["measurements"]:
        temperature = item.get("temperature_c")
        rows.append(
            [
                p(item["name"], small),
                p(f"{temperature:.1f} °C" if temperature is not None else "Unavailable", small),
                p(f"{item['latitude']}, {item['longitude']}", small),
            ]
        )
    table = Table(rows, colWidths=[76 * mm, 37 * mm, 55 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2ed")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dae2da")),
            ]
        )
    )
    story += [table, p("Evidence and provenance", heading)]
    for item in result["measurements"]:
        story.append(
            KeepTogether(
                [
                    p(item["name"], body),
                    p(f"Observed: {item.get('observed_at', 'Unavailable')}", small),
                    p(f"Source: {item.get('source', item.get('issue', 'Unavailable'))}", small),
                    p(f"Evidence ID: {item.get('source_id', 'Unavailable')}", small),
                ]
            )
        )
    story += [p("Limitations", heading)]
    story += [p("- " + item, small) for item in result["limitations"]]
    story += [
        p("Client follow-up draft", heading),
        p(result["follow_up_draft"], small),
        p("Review status: " + result["status"].replace("_", " "), small),
    ]
    if result.get("review"):
        story.append(
            p(
                f"Reviewed by {result['review']['reviewer']} at {result['review']['reviewed_at']}",
                small,
            )
        )

    def page_frame(canvas, doc):
        canvas.setStrokeColor(green)
        canvas.setLineWidth(2)
        canvas.line(21 * mm, 282 * mm, 189 * mm, 282 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(ink)
        canvas.drawString(21 * mm, 13 * mm, "HeatBrief | " + label)
        canvas.drawRightString(189 * mm, 13 * mm, f"Page {doc.page}")

    document = SimpleDocTemplate(
        output,
        pagesize=(210 * mm, 297 * mm),
        rightMargin=21 * mm,
        leftMargin=21 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title="HeatBrief - Temperature briefing",
        author="HeatBrief",
    )
    document.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
    return output.getvalue()
