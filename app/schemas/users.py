from pydantic import BaseModel, ConfigDict
from app.models import UserRole
from app.schemas.auth import UsernameBase


# Shared Schemas
class GrantAccessBaseResponse(BaseModel):
    message: str
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class UserAccountBase(UsernameBase):
    id: int
    first_name: str
    last_name: str
    # Username inherited from class
    network_id: int
    church_id: int

    model_config = ConfigDict(from_attributes=True)


# Request Schemas
class UserUpdateRequest(UserAccountBase):
    pass


class AdminUserUpdateRequest(UserUpdateRequest):
    role: UserRole


# Response Schemas
class GrantNetworkAccessResponse(GrantAccessBaseResponse):
    network_id: int
    model_config = ConfigDict(from_attributes=True)


class GrantChurchAccessResponse(GrantAccessBaseResponse):
    church_id: int
    model_config = ConfigDict(from_attributes=True)


class GrantChurchActivityAccessResponse(GrantAccessBaseResponse):
    activity_id: int
    model_config = ConfigDict(from_attributes=True)


class UserAccountResponse(UserAccountBase):
    role: UserRole
