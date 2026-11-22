
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Backend.database import get_db
from Backend.models import User
from Backend.Auth.schemas import LoginSchema
from Backend.Auth.security import (
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/login")
def login_user(
    payload: LoginSchema,
    db: Session = Depends(get_db),
):
    username = payload.username.strip().lower()

    user = db.query(User).filter(
        User.username == username
    ).first()

    if user is None or not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="نام کاربری یا رمز عبور اشتباه است.",
        )

    token = create_access_token(user.id)

    return {
        "message": "ورود موفقیت‌آمیز بود.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "gender": user.gender,
            "age": user.age,
        },
    }
