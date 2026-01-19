from pydantic import BaseModel, ConfigDict
from app.models import UserRole


# Shared Schemas
class GrantAccessBaseResponse(BaseModel):
    message: str
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class UserBaseResponse(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    role: UserRole
    network_id: int
    church_id: int

    model_config = ConfigDict(from_attributes=True)

# Request Schemas


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
