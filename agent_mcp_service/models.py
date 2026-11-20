from pydantic import BaseModel, Field


class UserInput(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=50,
        description="User's full name"
    )

    age: int = Field(
        ge=18,
        le=100,
        description="User's age"
    )

    city: str | None = Field(
        default=None,
        max_length=50,
        description="User's city"
    )