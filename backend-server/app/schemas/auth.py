from pydantic import BaseModel, ConfigDict, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: str | None = None
    role: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"  # "admin" o "user"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)