from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, EmailStr, model_validator
import uuid


Status = Literal["MATCH", "FAIL", "REVIEW", "NOT_AVAILABLE"]
StageStatus = Literal["Compatible", "Review", "Conflict", "Not Determined"]


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str
    email: EmailStr


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(AuthCredentials):
    full_name: str = Field(min_length=2, max_length=80)
    confirm_password: str = Field(min_length=6)


class Profile(BaseModel):
    user_id: str
    full_name: str = "Student"
    course: str = ""
    branch: str = ""
    year: str = ""
    marks: float = 0
    education_level: Literal["Class 10", "Class 12", "Diploma", "Undergraduate Degree", "Postgraduate Degree", "Other"] = "Undergraduate Degree"
    score_type: Literal["Percentage", "Grade", "SGPA", "CGPA"] = "Percentage"
    score_value: str = ""
    score_scale: str = "100"
    state: str = ""
    category: str = "Not specified"
    gender: str = "Prefer not to say"
    disability_status: str = "No"
    annual_income: float = 0
    income_certificate: bool = False
    receiving_scholarship: bool = False
    receiving_stipend: bool = False
    other_benefit: bool = False

    @model_validator(mode="after")
    def fill_legacy_score(self):
        if not self.score_value:
            self.score_value = f"{self.marks:g}"
        return self


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    course: str
    branch: str
    year: str
    marks: float = Field(ge=0, le=100)
    education_level: Literal["Class 10", "Class 12", "Diploma", "Undergraduate Degree", "Postgraduate Degree", "Other"] = "Undergraduate Degree"
    score_type: Literal["Percentage", "Grade", "SGPA", "CGPA"] = "Percentage"
    score_value: str = ""
    score_scale: str = "100"
    state: str
    category: str
    gender: str
    disability_status: str
    annual_income: float = Field(ge=0)
    income_certificate: bool
    receiving_scholarship: bool
    receiving_stipend: bool
    other_benefit: bool


class Condition(BaseModel):
    key: str
    label: str
    required: str
    status: Status
    student_value: str
    explanation: str


class Evidence(BaseModel):
    source_name: str
    source_url: str
    rule_text: str
    clause: str | None = None
    date_checked: str
    verification_status: Literal["Verified", "Needs Review", "Demo Rule", "Unavailable"]


class ScholarshipRule(BaseModel):
    course: str | None = None
    minimum_marks: float | None = None
    income_limit: float | None = None
    state: str | None = None
    category: str | None = None
    important_condition: str
    details_verified: bool = False
    academic_score_type: str = "Percentage"


class Scholarship(BaseModel):
    id: str
    name: str
    short_description: str
    provider: str
    category: str
    course: str
    education_level: str
    state: str
    eligibility_summary: str
    income_criteria: str
    academic_criteria: str
    benefit: str
    portal: str
    source_type: str
    rule: ScholarshipRule
    required_documents: list[str]
    deadline: str
    official_source: str
    official_source_url: str
    official_url: str
    discovery_source: str | None = None
    last_verified_date: str
    data_status: Literal["Verified Official", "Prototype", "Needs Review"]
    keywords: list[str] = Field(default_factory=list)
    restrictions: str
    evidence: Evidence
    conflict_rules: list[dict]
    demo_record: bool = True


class EligibilityResult(BaseModel):
    scholarship: Scholarship
    conditions: list[Condition]
    overall_status: Literal["ELIGIBLE", "REVIEW", "NOT_ELIGIBLE"]
    documents_ready: int
    documents_total: int
    next_action: str


class StudentDocument(BaseModel):
    id: str
    name: str
    type: str
    available: bool
    required_for: list[str]
    updated_at: datetime | None = None
    uploaded_at: datetime | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    has_file: bool = False
    extracted_value: str | None = None
    extraction_status: Literal["Verified", "Manual review", "Not uploaded"] = "Not uploaded"


class DocumentUpdate(BaseModel):
    available: bool


class CompareRequest(BaseModel):
    scholarship_ids: list[str] = Field(min_length=2, max_length=2)


class StageResult(BaseModel):
    id: str
    label: str
    status: StageStatus
    summary: str
    why: str
    evidence: Evidence | None = None


class ConflictAnalysis(BaseModel):
    id: str
    student_name: str
    scholarship_a: Scholarship
    scholarship_b: Scholarship
    stages: list[StageResult]
    overall_status: StageStatus
    recommendation: str
    disclaimer: str


class TrackingUpdate(BaseModel):
    stage: Literal["Discovered", "Eligibility Checked", "Documents", "Compatibility Reviewed", "Applied"]


class TrackingItem(BaseModel):
    scholarship_id: str
    scholarship_name: str
    stage: str
    updated_at: datetime | None = None


class Dashboard(BaseModel):
    profile: Profile
    scholarships: list[EligibilityResult]
    documents: list[StudentDocument]
    tracking: list[TrackingItem]
    next_actions: list[str]
    matched_count: int
    eligible_count: int
    review_count: int
    action_count: int
    documents_ready: int
    documents_total: int


class AuthResponse(BaseModel):
    user: User
    profile: Profile
    demo_mode: bool = False
