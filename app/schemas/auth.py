from pydantic import BaseModel, model_validator, field_validator


class UserRegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str

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

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserRegisterResponse(BaseModel):
    user_id: int
    message: str


class UserLogoutRequest(BaseModel):
    refresh_token: str


class UserLogoutResponse(BaseModel):
    message: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password", "confirm_new_password")
    def password_length(cls, v: str) -> str:
        if not 5 <= len(v) <= 20:
            raise ValueError("Password must be between 5 and 20 characters")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordResponse(BaseModel):
    message: str
