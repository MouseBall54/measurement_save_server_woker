from pydantic import BaseModel, Field


class MeasurementPoint(BaseModel):
    metric_name: str = Field(..., min_length=1)
    metric_unit: str | None = None
    class_name: str = Field(..., min_length=1)
    measure_item: str = Field(..., min_length=1)
    measurable: bool = True
    x_index: int
    y_index: int
    x_0: float
    y_0: float
    x_1: float
    y_1: float
    value: float


class IngestRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    site_name: str = Field(..., min_length=1)
    node_name: str = Field(..., min_length=1)
    module_name: str = Field(..., min_length=1)
    recipe_name: str = Field(..., min_length=1)
    recipe_version: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)
    file_name: str = Field(..., min_length=1)
    lot_name: str | None = None
    wf_number: int | None = None
    measurements: list[MeasurementPoint]


class IngestResponse(BaseModel):
    status: str
    id: str
