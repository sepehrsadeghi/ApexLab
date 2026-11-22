
from typing import Literal, Annotated

from pydantic import BaseModel, Field, StringConstraints


class RegisterSchema(BaseModel):
    first_name: Annotated[
        str,
        StringConstraints(
            min_length=2,
            max_length=50,
            strip_whitespace=True,
        ),
    ]

    last_name: Annotated[
        str,
        StringConstraints(
            min_length=2,
            max_length=50,
            strip_whitespace=True,
        ),
    ]

    username: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=20,
            strip_whitespace=True,
            pattern=r"^[A-Za-z][A-Za-z0-9_]{2,19}$",
        ),
    ]

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    gender: Literal["male", "female"]

    age: int = Field(ge=5, le=100)


class LoginSchema(BaseModel):
    username: Annotated[
        str,
        StringConstraints(
            min_length=3,
            max_length=20,
            strip_whitespace=True,
        ),
    ]

    password: str = Field(
        min_length=8,
        max_length=128,
    )
