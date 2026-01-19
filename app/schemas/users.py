from pydantic import BaseModel, ConfigDict
from app.models import UserRole
from app.schemas.auth import UsernameBase


# Shared Schemas
class GrantAccessBaseResponse(BaseModel):
    message: str
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class UserAccountBase(UsernameBase):
    first_name: str
    last_name: str
    # Username inherited from class

    model_config = ConfigDict(from_attributes=True)


# Request Schemas
class UserUpdateRequest(UserAccountBase):
    pass


class AdminUserUpdateRequest(UserUpdateRequest):
    role: UserRole
    network_id: int
    church_id: int


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


class NetworkAccess(BaseModel):
    id: int
    network_id: int
    network_name: str
    network_slug: str


class ChurchAccess(BaseModel):
    id: int
    church_id: int
    church_name: str
    church_slug: str


class ChurchActivityAccess(BaseModel):
    id: int
    church_activity_id: int
    church_activity_name: str
    church_activity_slug: str


class AllAccessResponse(BaseModel):
    networks: list[NetworkAccess]
    churches: list[ChurchAccess]
    church_activities: list[ChurchActivityAccess]


class UserAccountResponse(UserAccountBase):
    id: int
    role: UserRole
    network_id: int
    church_id: int
