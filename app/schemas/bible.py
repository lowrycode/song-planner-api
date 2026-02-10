from pydantic import BaseModel, ConfigDict


class BiblePassageRequest(BaseModel):
    ref: str
    model_config = ConfigDict(from_attributes=True)


class BiblePassageResponse(BaseModel):
    text: str
    model_config = ConfigDict(from_attributes=True)
