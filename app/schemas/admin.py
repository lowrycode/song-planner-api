from pydantic import BaseModel, ConfigDict


# Shared Schemas
class GrantAccessBaseResponse(BaseModel):
    message: str
    user_id: int
    model_config = ConfigDict(from_attributes=True)


# Request Schemas


# Response Schemas
class GrantNetworkAccessResponse(GrantAccessBaseResponse):
    network_id: int
    model_config = ConfigDict(from_attributes=True)
