
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from Backend.database import get_db
from Backend.models import User
from Backend.Auth.schemas import RegisterSchema
from Backend.Auth.security import hash_password


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterSchema,
    db: Session = Depends(get_db),
):
    username = payload.username.strip().lower()

    existing_user = db.query(User).filter(
        User.username == username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این نام کاربری قبلاً ثبت شده است.",
        )

    user = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        username=username,
        password_hash=hash_password(payload.password),
        gender=payload.gender,
        age=payload.age,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="این نام کاربری قبلاً ثبت شده است.",
        )

    return {
        "message": "ثبت‌نام با موفقیت انجام شد.",
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "gender": user.gender,
            "age": user.age,
        },
    }
