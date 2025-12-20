from pydantic import BaseModel, ConfigDict


# Response Schemas
class ChurchActivitySchema(BaseModel):
    id: int
    name: str
    slug: str
    model_config = ConfigDict(from_attributes=True)
