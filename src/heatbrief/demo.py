"""Inclusive coverage and reproducible synthetic scenarios for the local demo."""

import hashlib
import math
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from heatbrief.errors import HeatBriefError

DEMO_ZONE = ZoneInfo("America/Phoenix")
DEMO_START = datetime(2025, 1, 1, 0, 0, tzinfo=DEMO_ZONE)
DEMO_END = datetime(2027, 12, 31, 23, 59, tzinfo=DEMO_ZONE)
REFERENCE = datetime(2025, 9, 20, 14, 0, tzinfo=DEMO_ZONE)
DEMO_TIME = {"date": "2025-09-20", "time": "14:00", "timezone": "America/Phoenix"}
DEMO_COVERAGE_MESSAGE = (
    "Synthetic demo readings are available from 2025-01-01 at 00:00 through "
    "2027-12-31 at 23:59 America/Phoenix, inclusive, at one-minute intervals. "
    "Use a valid, unambiguous local time and an IANA timezone. "
    "Live temperature data is not connected."
)
DEMO_COVERAGE = {
    "start": DEMO_START.isoformat(),
    "end": DEMO_END.isoformat(),
    "timezone": "America/Phoenix",
    "start_date": "2025-01-01",
    "start_time": "00:00",
    "end_date": "2027-12-31",
    "end_time": "23:59",
    "step_minutes": 1,
    "presets": [
        {"label": label, "date": day, "time": clock, "timezone": "America/Phoenix"}
        for label, day, clock in [
            ("Winter morning", "2025-01-15", "08:00"),
            ("Spring noon", "2026-04-15", "12:00"),
            ("Summer afternoon", "2026-07-15", "15:00"),
            ("Autumn evening", "2026-11-09", "18:00"),
            ("Late night", "2027-08-20", "23:30"),
            ("Original example", "2025-09-20", "14:00"),
        ]
    ],
}


def validate_demo_timestamp(value):
    if not DEMO_START <= value <= DEMO_END:
        raise HeatBriefError("unsupported_date", DEMO_COVERAGE_MESSAGE, 422)


def validate_demo_time(request):
    validate_demo_timestamp(request.timestamp)


def parse_demo_timestamp(date_time):
    """Keep the legacy input usable; explicit timezones describe the same instant."""
    try:
        if set(date_time) - {"start_date", "start_time", "timezone", "filter_type"}:
            raise ValueError("Unknown date/time fields")
        if type(date_time.get("filter_type")) is not int or date_time["filter_type"] != 1:
            raise ValueError("Use filter_type 1")
        raw = f"{date_time['start_date']} {date_time['start_time']}"
        local = datetime.strptime(raw, "%Y-%m-%d %H:%M")
        if local.strftime("%Y-%m-%d %H:%M") != raw:
            raise ValueError("Use YYYY-MM-DD and HH:MM")
        zone = ZoneInfo(date_time.get("timezone", "America/Phoenix"))
        candidates = set()
        for fold in (0, 1):
            utc = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            if utc.astimezone(zone).replace(tzinfo=None) == local:
                candidates.add(utc)
        if len(candidates) != 1:
            raise ValueError("Ambiguous or nonexistent local time")
        value = next(iter(candidates)).astimezone(zone)
        validate_demo_timestamp(value)
        return value
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError, HeatBriefError) as exc:
        raise ValueError("unsupported_date: " + DEMO_COVERAGE_MESSAGE) from exc


def synthetic_temperature(base, value, coordinates):
    """Fictional seasonal/daytime variation, anchored to the original sample."""
    local = value.astimezone(DEMO_ZONE)
    amplitude = {33.4484: 5.5, 33.4255: 7.0, 33.4942: 4.5}[coordinates[0]]

    def curve(stamp):
        season = 10 * math.cos(math.tau * (stamp.timetuple().tm_yday - 200) / 365.2425)
        hour = stamp.hour + stamp.minute / 60
        daytime = amplitude * math.cos(math.tau * (hour - 15) / 24)
        digest = hashlib.sha256(
            f"heatbrief-synthetic-v2:{stamp.date()}:{coordinates}".encode()
        ).digest()
        day_variation = int.from_bytes(digest[:2], "big") / 65535 * 3 - 1.5
        return season + daytime + day_variation

    return round(base + curve(local) - curve(REFERENCE), 1)
