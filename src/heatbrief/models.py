from datetime import UTC, date, datetime, time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class BriefingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,80}$")
    question: str = Field(min_length=10, max_length=1000)
    date: date
    time: time
    timezone: str = Field(min_length=1, max_length=100)
    locations: list[Location] = Field(min_length=2, max_length=10)
    client_name: str = Field(default="Demo client", min_length=1, max_length=120)

    @field_validator("time")
    @classmethod
    def local_minute(cls, value):
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ValueError("Provide local HH:MM without an offset; set timezone separately")
        return value

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Provide a valid IANA timezone, e.g. America/Phoenix") from exc
        return value

    @model_validator(mode="after")
    def unambiguous_request(self):
        coordinates = {(loc.latitude, loc.longitude) for loc in self.locations}
        names = {loc.name.casefold() for loc in self.locations}
        if len(coordinates) != len(self.locations) or len(names) != len(self.locations):
            raise ValueError("Each location must have a unique name and coordinates")
        local = datetime.combine(self.date, self.time)
        zone = ZoneInfo(self.timezone)
        candidates = set()
        for fold in (0, 1):
            aware = local.replace(tzinfo=zone, fold=fold)
            utc = aware.astimezone(UTC)
            if utc.astimezone(zone).replace(tzinfo=None) == local:
                candidates.add(utc)
        if len(candidates) != 1:
            raise ValueError(
                "Local time is ambiguous or nonexistent due to DST; choose another time"
            )
        return self

    @property
    def timestamp(self) -> datetime:
        return datetime.combine(self.date, self.time, tzinfo=ZoneInfo(self.timezone))


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    temperature: float | None = Field(default=None, allow_inf_nan=False)
    unit: Literal["C", "F"]
    observed_at: datetime
    source: str = Field(min_length=1, max_length=300)
    source_id: str = Field(min_length=1, max_length=300)
    mock: bool

    @field_validator("observed_at")
    @classmethod
    def aware_timestamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("Measurement timestamp must include a UTC offset")
        return value
