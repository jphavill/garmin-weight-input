from pydantic import BaseModel, Field


class WeightInput(BaseModel):
    weight: float


class ConvertLatestHikeToRuckRequest(BaseModel):
    pack_weight: float = Field(gt=0, le=100)
