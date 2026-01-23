from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models import UserRole
from app.schemas.auth import UsernameBase
from app.schemas.networks import NetworkSchema, ChurchSchema


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


class AccessItem(BaseModel):
    access_id: int
    name: str
    slug: str


class NetworkAccess(AccessItem):
    network_id: int


class ChurchAccess(AccessItem):
    church_id: int


class ChurchActivityAccess(AccessItem):
    church_activity_id: int


class AllAccessResponse(BaseModel):
    networks: list[NetworkAccess]
    churches: list[ChurchAccess]
    church_activities: list[ChurchActivityAccess]


class UserAccountResponse(UserAccountBase):
    id: int
    role: UserRole
    network: NetworkSchema
    church: ChurchSchema
    created_at: datetime


class UserWithAccessesResponse(UserAccountResponse):
    accesses: AllAccessResponse
