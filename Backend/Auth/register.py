from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from pwdlib import PasswordHash

from Backend.database import get_db
from Backend.Auth.schemas import RegisterSchema

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

password_hasher = PasswordHash.recommended()


@router.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):

    # هش کردن رمز عبور
    hashed_password = password_hasher.hash(data.password)

    try:
        result = db.execute(
            text("""
                INSERT INTO public.users
                (first_name, last_name, username, password_hash, gender)
                VALUES
                (:first_name, :last_name, :username, :password_hash, :gender)
                RETURNING id, first_name, last_name, username, gender, created_at
            """),
            {
                "first_name": data.first_name,
                "last_name": data.last_name,
                "username": data.username.strip(),
                "password_hash": hashed_password,
                "gender": data.gender
            }
        )

        user = result.mappings().one()
        db.commit()

        return {
            "message": "Registration successful",
            "user": {
                "id": str(user["id"]),
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "username": user["username"],
                "gender": user["gender"],
                "created_at": user["created_at"]
            }
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This username is already taken"
        )

    except Exception:
        db.rollback()
        raise