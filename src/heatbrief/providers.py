import asyncio
import os
from contextlib import asynccontextmanager

from heatbrief.errors import HeatBriefError
from heatbrief.mcp_client import call_env_params, mock_session


class MockProvider:
    mode = "mock"

    def __init__(self, session):
        self.session = session

    async def measure(self, location, request):
        async with asyncio.timeout(15):
            return await call_env_params(
                self.session,
                {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "date_time": {
                        "start_date": request.date.isoformat(),
                        "start_time": request.time.strftime("%H:%M"),
                        "filter_type": 1,
                    },
                },
            )


async def measure_with_retry(provider, location, request, attempts=3, base_delay=0.1):
    """Retry transient failures only, bounded by attempts and the comparison's total timeout."""
    for attempt in range(attempts):
        try:
            return await provider.measure(location, request)
        except (TimeoutError, HeatBriefError) as exc:
            transient = isinstance(exc, TimeoutError) or exc.code in {"rate_limited", "timeout"}
            if not transient:
                raise
            if attempt == attempts - 1:
                if isinstance(exc, TimeoutError):
                    raise HeatBriefError(
                        "timeout", "MCP timed out after bounded retries", 504
                    ) from exc
                raise
            await asyncio.sleep(base_delay * 2**attempt)


@asynccontextmanager
async def provider_session(mode: str | None = None):
    mode = mode or os.getenv("HEATBRIEF_MODE", "mock")
    if mode == "mock":
        async with mock_session() as session:
            yield MockProvider(session)
    elif mode == "live":
        if not os.getenv("FORTYGUARD_API_KEY") or not os.getenv("FORTYGUARD_MCP_URL"):
            raise HeatBriefError(
                "missing_credentials",
                "Set FORTYGUARD_API_KEY and FORTYGUARD_MCP_URL after confirming provider access.",
                503,
            )
        raise HeatBriefError(
            "live_integration_unverified",
            "Live comparison is gated until FortyGuard transport and measurement schema "
            "are verified. "
            "See docs/integration.md. No mock fallback was used.",
            503,
        )
    else:
        raise HeatBriefError("invalid_mode", "HEATBRIEF_MODE must be mock or live", 503)
