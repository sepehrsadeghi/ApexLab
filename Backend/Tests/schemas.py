from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class TestResultCreate(BaseModel):
    test_code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    score: float | None = None
    accuracy: float | None = Field(default=None, ge=0, le=100)
    duration_ms: int | None = Field(default=None, ge=0)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    raw_data: dict[str, Any] | list[Any] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class TestResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    test_code: str
    score: float | None
    accuracy: float | None
    duration_ms: int | None
    started_at: datetime | None
    completed_at: datetime
    metrics: dict[str, Any]
    raw_data: dict[str, Any] | list[Any] | None
    notes: str | None
