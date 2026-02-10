from pydantic import BaseModel, ConfigDict, Field, field_validator


class BiblePassageRequest(BaseModel):
    ref: str
    model_config = ConfigDict(from_attributes=True)


class BiblePassageResponse(BaseModel):
    text: str
    model_config = ConfigDict(from_attributes=True)


class GenerateThemesRequest(BaseModel):
    text: str = Field(min_length=5, max_length=5000)
    model_config = ConfigDict(from_attributes=True)

    @field_validator("text")
    @classmethod
    def strip_and_validate(cls, v: str):
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Text must contain at least 5 non-whitespace characters")
        return v


class GenerateThemesResponse(BaseModel):
    themes: str
    model_config = ConfigDict(from_attributes=True)
