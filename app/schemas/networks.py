from pydantic import BaseModel, ConfigDict


# Response Schemas
class NetworkSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class ChurchSchema(BaseModel):
    id: int
    name: str
    slug: str
    model_config = ConfigDict(from_attributes=True)
