import hmac
import logging
import os
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from heatbrief.errors import HeatBriefError
from heatbrief.models import BriefingRequest
from heatbrief.providers import provider_session
from heatbrief.service import build_briefing
from heatbrief.store import Store

app = FastAPI(
    title="HeatBrief", version="0.1.0", description="Mock-first briefing drafts. No sending."
)
logger = logging.getLogger("heatbrief")


def authorize(provided: str | None, variable: str):
    expected = os.getenv(variable, "")
    if not expected or expected.startswith("replace-"):
        raise HeatBriefError(
            "not_configured", f"Configure {variable} before using this endpoint", 503
        )
    if not provided or not hmac.compare_digest(provided, f"Bearer {expected}"):
        raise HeatBriefError("unauthorized", "A valid Bearer token is required", 401)


def api_auth(authorization: str | None = Header(default=None)):
    authorize(authorization, "HEATBRIEF_API_TOKEN")


def review_auth(authorization: str | None = Header(default=None)):
    authorize(authorization, "HEATBRIEF_REVIEW_TOKEN")


def get_store():
    return Store(os.getenv("HEATBRIEF_DATA_DIR", "data"))


StoreDependency = Annotated[Store, Depends(get_store)]


@app.exception_handler(HeatBriefError)
async def domain_error(_request, exc):
    return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):
    errors = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_request",
            "message": "Clarify the listed request fields",
            "details": errors,
        },
    )


@app.exception_handler(TimeoutError)
async def timeout_error(_request, _exc):
    return JSONResponse(
        status_code=504,
        content={
            "error": "timeout",
            "message": "Briefing exceeded its time limit; retry the same request ID",
        },
    )


@app.exception_handler(Exception)
async def unexpected_error(_request, exc):
    logger.error("Briefing failed (%s)", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Briefing failed; inspect the local service configuration",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "mode": os.getenv("HEATBRIEF_MODE", "mock"), "live_verified": False}


@app.post("/briefings", dependencies=[Depends(api_auth)])
async def create_briefing(request: BriefingRequest, store: StoreDependency):
    async with provider_session() as provider:
        return await build_briefing(request, provider, store)


@app.get("/briefings/{request_id}", dependencies=[Depends(api_auth)])
def read_briefing(request_id: str, store: StoreDependency):
    return store.get(request_id)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=120)


@app.post("/briefings/{request_id}/review", dependencies=[Depends(review_auth)])
def review_briefing(request_id: str, review: Review, store: StoreDependency):
    return store.review(
        request_id,
        {
            **review.model_dump(),
            "reviewed_at": datetime.now(UTC).isoformat(),
        },
    )
