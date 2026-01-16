from pydantic import BaseModel, field_validator


class UserRegisterRequest(BaseModel):
    first_name: str
    last_name: str
    username: str
    password: str
    confirm_password: str
    network_id: int
    church_id: int

    @field_validator('username')
    def username_length(cls, v: str) -> str:
        if not 5 <= len(v) <= 20:
            raise ValueError("Username must be between 5 and 20 characters")
        return v

    @field_validator('password')
    def password_length(cls, v: str) -> str:
        if not 5 <= len(v) <= 20:
            raise ValueError("Password must be between 5 and 20 characters")
        return v


class UserRegisterResponse(BaseModel):
    user_id: int
    message: str


class UserLoginResponse(BaseModel):
    message: str


class UserLogoutResponse(BaseModel):
    message: str


class UserMeResponse(BaseModel):
    id: int
    username: str
    first_name: str | None
    last_name: str | None
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password", "confirm_new_password")
    def password_length(cls, v: str) -> str:
        if not 5 <= len(v) <= 20:
            raise ValueError("Password must be between 5 and 20 characters")
        return v


class ChangePasswordResponse(BaseModel):
    message: str
