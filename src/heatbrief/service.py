import asyncio
from decimal import Decimal

from pydantic import ValidationError

from heatbrief.errors import HeatBriefError
from heatbrief.models import Measurement
from heatbrief.providers import measure_with_retry
from heatbrief.reporting import render_draft, render_report


async def build_briefing(request, provider, store):
    existing = store.claim(request, provider.mode)
    if existing:
        return {**existing, "replayed": True}
    try:
        async with asyncio.timeout(60):
            result = await compare(request, provider)
        store.complete(request.request_id, result)
        return result
    except BaseException:
        store.release(request.request_id)
        raise


async def compare(request, provider):
    readings, available, issues = [], [], []
    first_error = None
    for location in request.locations:
        row = location.model_dump()
        try:
            value = Measurement.model_validate(
                await measure_with_retry(provider, location, request)
            )
            if (value.latitude, value.longitude) != (location.latitude, location.longitude):
                raise HeatBriefError("evidence_mismatch", "Measurement coordinates do not match")
            if value.observed_at != request.timestamp:
                raise HeatBriefError("evidence_mismatch", "Measurement timestamp does not match")
            if value.mock != (provider.mode == "mock"):
                raise HeatBriefError("evidence_mismatch", "Measurement source mode does not match")
            row.update(value.model_dump(mode="json"))
            if value.temperature is None:
                raise HeatBriefError("missing_measurement", "Temperature measurement is missing")
            celsius = Decimal(str(value.temperature))
            if value.unit == "F":
                celsius = (celsius - Decimal(32)) * Decimal(5) / Decimal(9)
            row["temperature_c"] = float(celsius.quantize(Decimal("0.001")))
            available.append(row)
        except (HeatBriefError, ValidationError, TimeoutError) as exc:
            error = (
                exc
                if isinstance(exc, HeatBriefError)
                else HeatBriefError(
                    "invalid_response" if isinstance(exc, ValidationError) else "timeout",
                    "Missing/invalid measurement evidence"
                    if isinstance(exc, ValidationError)
                    else "Temperature tool timed out",
                    502,
                )
            )
            first_error = first_error or error
            row["temperature_c"] = None
            row["issue"] = str(error)
            issues.append(f"{location.name}: {error}")
        readings.append(row)
    if not available:
        raise first_error or HeatBriefError("no_measurements", "No temperature readings available")
    ranking = sorted(available, key=lambda item: (item["temperature_c"], item["name"]))
    lowest = ranking[0]["temperature_c"]
    comparison = {
        "mock": provider.mode == "mock",
        "incomplete": len(available) != len(readings),
        "lowest_c": lowest,
        "lowest_locations": [row["name"] for row in ranking if row["temperature_c"] == lowest],
        "spread_c": round(ranking[-1]["temperature_c"] - lowest, 3),
        "ranking": [{"name": r["name"], "temperature_c": r["temperature_c"]} for r in ranking],
    }
    limitations = issues + [
        "Only temperature is compared; this does not establish safety for outdoor work or events.",
        "Readings apply only to the stated coordinates and timestamp.",
        "Rankings use Celsius rounded to 0.001 degrees; displayed values use one decimal.",
    ]
    if comparison["mock"]:
        limitations.insert(
            0, "Mock data: all readings are fictional; live FortyGuard is unverified."
        )
    return {
        "request_id": request.request_id,
        "status": "draft_pending_review",
        "replayed": False,
        "request": request.model_dump(mode="json"),
        "comparison": comparison,
        "measurements": readings,
        "limitations": limitations,
        "report_markdown": render_report(request, comparison, readings, limitations),
        "follow_up_draft": render_draft(request, comparison),
    }
