from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pwdlib import PasswordHash

from Backend.database import get_db
from Backend.Auth.schemas import LoginSchema

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

password_hasher = PasswordHash.recommended()


@router.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):

    result = db.execute(
        text("""
            SELECT id, first_name, last_name, username,
                   password_hash, gender, created_at
            FROM public.users
            WHERE LOWER(username) = LOWER(:username)
        """),
        {"username": data.username.strip()}
    )

    user = result.mappings().first()

    if user is None or not password_hasher.verify(
        data.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    return {
        "message": "Login successful",
        "user": {
            "id": str(user["id"]),
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "username": user["username"],
            "gender": user["gender"],
            "created_at": user["created_at"]
        }
    }