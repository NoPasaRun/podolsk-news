from pydantic import BaseModel


class Me(BaseModel):
    id: int
    email: str | None
    name: str | None
    avatar: str | None
