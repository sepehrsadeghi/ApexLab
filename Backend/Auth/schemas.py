from typing import Literal, Annotated
from pydantic import BaseModel, Field, StringConstraints


class RegisterSchema(BaseModel):
    first_name: Annotated[
        str,
        StringConstraints(
            min_length=2,
            max_length=50,
            strip_whitespace=True
        )
    ]

    last_name: Annotated[
        str,
        StringConstraints(
            min_length=2,
            max_length=50,
            strip_whitespace=True
        )
    ]

    username: Annotated[
        str,
        StringConstraints(
            min_length=4,
            max_length=20,
            strip_whitespace=True,
            pattern=r"^[a-zA-Z0-9_.-]+$"
        )
    ]

    password: str = Field(min_length=8, max_length=128)

    gender: Literal[
        "male",
        "female",
        "other",
        "prefer_not_to_say"
    ]


class LoginSchema(BaseModel):
    username: Annotated[
        str,
        StringConstraints(
            min_length=4,
            max_length=20,
            strip_whitespace=True
        )
    ]

    password: str = Field(min_length=8, max_length=128)