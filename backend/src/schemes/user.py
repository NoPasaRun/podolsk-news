from pydantic import BaseModel


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class Me(BaseModel):
    id: int
    email: str | None
    name: str | None
    avatar: str | None
