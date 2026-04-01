"""
Pydantic request/response models extracted from server.py.
Import these in server.py and route modules.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class CrewAccessCreate(BaseModel):
    label: str
    truck_number: str
    division: str
    assignment: str = ""


class CrewAccessUpdate(BaseModel):
    label: str
    truck_number: str
    division: str
    assignment: str = ""


class MatchOverrideRequest(BaseModel):
    job_id: str
    service_type: str | None = None


class ManagementReviewRequest(BaseModel):
    submission_id: str
    job_id: str | None = None
    service_type: str
    category_scores: dict[str, float]
    comments: str = ""
    disposition: str
    flagged_issues: list[str] = Field(default_factory=list)


class OwnerReviewRequest(BaseModel):
    submission_id: str
    category_scores: dict[str, float]
    comments: str = ""
    final_disposition: str
    training_inclusion: str
    exclusion_reason: str = ""


class ExportRunRequest(BaseModel):
    dataset_type: str
    export_format: str


class UserCreateRequest(BaseModel):
    name: str
    email: str
    role: str = "management"
    title: str
    password: str
    is_active: bool = True


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class CrewLinkStatusUpdateRequest(BaseModel):
    enabled: bool


class RapidReviewRequest(BaseModel):
    submission_id: str
    overall_rating: str
    comment: str = ""
    issue_tag: str = ""
    annotation_count: int = 0
    entry_mode: str = "desktop"
    swipe_duration_ms: int = 0
    session_id: str = ""


class RapidReviewSessionStart(BaseModel):
    total_queue_size: int = 0
    entry_mode: str = "mobile"


class RapidReviewSessionEnd(BaseModel):
    session_id: str
    exit_reason: str = "manual"


class StandardItemRequest(BaseModel):
    title: str
    category: str
    audience: str = "crew"
    division_targets: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    notes: str = ""
    owner_notes: str = ""
    shoutout: str = ""
    image_url: str
    training_enabled: bool = True
    question_type: str = "multiple_choice"
    question_prompt: str = ""
    choice_options: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    is_active: bool = True


class StandardItemUpdateRequest(BaseModel):
    title: str | None = None
    category: str | None = None
    audience: str | None = None
    division_targets: list[str] | None = None
    checklist: list[str] | None = None
    notes: str | None = None
    owner_notes: str | None = None
    shoutout: str | None = None
    image_url: str | None = None
    training_enabled: bool | None = None
    question_type: str | None = None
    question_prompt: str | None = None
    choice_options: list[str] | None = None
    correct_answer: str | None = None
    is_active: bool | None = None


class TrainingSessionCreateRequest(BaseModel):
    access_code: str
    division: str = ""
    item_count: int = 5


class TrainingAnswerSubmission(BaseModel):
    item_id: str
    response: str
    time_seconds: float = 0


class TrainingSessionSubmitRequest(BaseModel):
    answers: list[TrainingAnswerSubmission]


class RubricCategoryInput(BaseModel):
    key: str
    label: str
    weight: float = Field(ge=0, le=1)
    max_score: int = Field(default=5, ge=1, le=10)


class RubricMatrixCreate(BaseModel):
    service_type: str
    division: str
    title: str
    min_photos: int = Field(default=3, ge=1, le=20)
    pass_threshold: int = Field(default=80, ge=1, le=100)
    hard_fail_conditions: list[str] = []
    categories: list[RubricCategoryInput] = Field(min_length=1, max_length=10)


class RubricMatrixUpdate(BaseModel):
    title: str | None = None
    division: str | None = None
    min_photos: int | None = None
    pass_threshold: int | None = None
    hard_fail_conditions: list[str] | None = None
    categories: list[RubricCategoryInput] | None = None
    is_active: bool | None = None
