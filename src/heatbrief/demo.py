"""Shared coverage of the fictional local demo; never change a user's requested time."""

from heatbrief.errors import HeatBriefError

DEMO_TIME = {"date": "2025-09-20", "time": "14:00", "timezone": "America/Phoenix"}
DEMO_COVERAGE_MESSAGE = (
    "This demo has fictional readings only for 2025-09-20 at 14:00 America/Phoenix. "
    "Use that date, time and timezone to test the automation. "
    "Live temperature data is not connected."
)


def validate_demo_time(request):
    if (
        request.date.isoformat() != DEMO_TIME["date"]
        or request.time.isoformat(timespec="minutes") != DEMO_TIME["time"]
        or request.timezone != DEMO_TIME["timezone"]
    ):
        raise HeatBriefError("unsupported_date", DEMO_COVERAGE_MESSAGE, 422)
