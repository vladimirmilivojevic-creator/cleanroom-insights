"""Pydantic v2 schemas: what the API accepts and returns."""

from datetime import datetime
from typing import Any, Literal

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain import MODULES

Role = Literal["admin", "trainer", "trainee"]


class ORMModel(BaseModel):
    # from_attributes: build from SQLAlchemy objects; validate_by_name: also accept plain field names
    model_config = ConfigDict(from_attributes=True, validate_by_name=True)


# --- auth & users -------------------------------------------------------------


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool


class MeOut(UserOut):
    organization_id: int
    organization_name: str = Field(validation_alias=AliasPath("organization", "name"))


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    full_name: str = Field(min_length=2, max_length=200)
    role: Role
    password: str = Field(min_length=8, max_length=72)  # bcrypt uses at most 72 bytes


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


# --- training content -----------------------------------------------------------


class StepOut(BaseModel):
    code: str
    title: str


class DeviationOut(BaseModel):
    code: str
    title: str
    severity: str


class ModuleOut(BaseModel):
    code: str
    title: str
    description: str
    steps: list[StepOut]
    deviations: list[DeviationOut]


# --- sessions & events -----------------------------------------------------------


def _check_module(code: str) -> str:
    if code not in MODULES:
        raise ValueError(f"Unknown module '{code}'")
    return code


class SessionCreate(BaseModel):
    module: str
    trainee_id: int | None = None  # trainers must set it, trainees start their own session

    _validate_module = field_validator("module")(_check_module)


class SimulationCreate(BaseModel):
    module: str
    trainee_id: int
    skill: float | None = Field(default=None, ge=0, le=1)  # 0 = beginner, 1 = expert

    _validate_module = field_validator("module")(_check_module)


class EventIn(BaseModel):
    """An event as sent by the VR headset."""

    kind: Literal["step", "deviation"]
    step: str
    deviation: str | None = None

    @model_validator(mode="after")
    def deviation_matches_kind(self) -> "EventIn":
        if self.kind == "deviation" and not self.deviation:
            raise ValueError("A deviation event needs a 'deviation' code")
        if self.kind == "step" and self.deviation:
            raise ValueError("A step event must not have a 'deviation' code")
        return self


class EventOut(ORMModel):
    id: int
    kind: str
    step: str
    deviation: str | None
    severity: str | None
    penalty: int
    created_at: datetime


class SessionOut(ORMModel):
    id: int
    module: str
    status: str
    trainee_id: int
    trainee_name: str = Field(validation_alias=AliasPath("trainee", "full_name"))
    started_at: datetime
    finished_at: datetime | None
    score: int | None
    passed: bool | None


class SessionDetail(SessionOut):
    events: list[EventOut] = []
    certificate_code: str | None = None


# --- certificates, audit, analytics ----------------------------------------------


class CertificateOut(ORMModel):
    code: str
    module: str
    score: int
    issued_at: datetime
    valid_until: datetime
    trainee_id: int
    trainee_name: str = Field(validation_alias=AliasPath("trainee", "full_name"))


class CertificateVerification(CertificateOut):
    organization_name: str
    valid: bool


class AuditOut(ORMModel):
    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any]
    created_at: datetime
    hash: str


class AuditVerification(BaseModel):
    valid: bool
    checked: int
    broken_at_id: int | None = None


class Overview(BaseModel):
    trainees: int
    completed_sessions: int
    running_sessions: int
    pass_rate: float  # percent
    average_score: float
    valid_certificates: int


class HeatmapCell(BaseModel):
    step: str
    deviation: str
    count: int


class Heatmap(BaseModel):
    module: str
    steps: list[StepOut]
    deviations: list[DeviationOut]
    cells: list[HeatmapCell]


class TraineeProgress(BaseModel):
    trainee_id: int
    trainee_name: str
    sessions: int
    average_score: float | None
    last_score: int | None
    passed_sessions: int
    certified_modules: list[str]


class TraineeDetail(BaseModel):
    trainee: UserOut
    sessions: list[SessionOut]
    certificates: list[CertificateOut]
