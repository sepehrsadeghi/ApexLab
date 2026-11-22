from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from Backend.database import get_db
from Backend.models import TestResult, User, utc_now
from Backend.Auth.security import get_current_user
from Backend.Tests.schemas import TestResultCreate, TestResultResponse

router = APIRouter(prefix="/tests", tags=["Test results"])


@router.post("/results", response_model=TestResultResponse, status_code=201)
def save_test_result(
    payload: TestResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = TestResult(
        user_id=current_user.id,
        test_code=payload.test_code.strip().upper(),
        score=payload.score,
        accuracy=payload.accuracy,
        duration_ms=payload.duration_ms,
        started_at=payload.started_at,
        completed_at=payload.completed_at or utc_now(),
        metrics=payload.metrics,
        raw_data=payload.raw_data,
        notes=payload.notes,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.get("/results/me", response_model=list[TestResultResponse])
def get_my_test_results(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(TestResult)
        .filter(TestResult.user_id == current_user.id)
        .order_by(TestResult.completed_at.desc())
        .limit(limit)
        .all()
    )
