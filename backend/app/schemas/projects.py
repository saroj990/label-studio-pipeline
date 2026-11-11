from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    class_a: str = Field(default="accepted", min_length=1, max_length=64)
    class_b: str = Field(default="rejected", min_length=1, max_length=64)


class ProjectResponse(BaseModel):
    id: int
    name: str
    class_a: str
    class_b: str
    label_studio_project_id: int | None

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: int
    image_url: str
    filename: str | None
    label: str | None


class LabelRequest(BaseModel):
    choice: str


class TrainResponse(BaseModel):
    run_id: int
    status: str
    metrics: dict | None = None
    message: str | None = None
    model_filename: str | None = None
    model_path: str | None = None


class PredictResponse(BaseModel):
    prediction: str
    scores: dict[str, float]


class SaveModelRequest(BaseModel):
    run_id: int | None = None


class SavedModelResponse(BaseModel):
    run_id: int
    model_filename: str
    model_path: str
    saved: bool = True
