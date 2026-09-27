import asyncio
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
import secrets
from typing import Any
import uuid

from fastapi import APIRouter, Cookie, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pymongo.errors import DuplicateKeyError

from lib.db import db
from lib.dates import today_iso
from lib.catalog import build_catalog
from models.domain import (
    AuthCredentials,
    AuthResponse,
    CompareRequest,
    Condition,
    ConflictAnalysis,
    Dashboard,
    DocumentUpdate,
    EligibilityResult,
    Evidence,
    Profile,
    ProfileUpdate,
    RegisterRequest,
    Scholarship,
    StageResult,
    StudentDocument,
    TrackingItem,
    TrackingUpdate,
    User,
)

router = APIRouter()
SESSION_COOKIE = "vidyadwar_session"
DEMO_EMAIL = "aarav.demo@vidyadwar.app"
DOCUMENT_TYPES = {
    "Marksheet": "Academic",
    "Income Certificate": "Financial",
    "Domicile Certificate": "Identity",
    "Bank Details": "Payment",
    "Category Certificate": "Eligibility",
}
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_UPLOADS = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}
TRACKING_STAGES = (
    "Discovered",
    "Eligibility Checked",
    "Documents",
    "Compatibility Reviewed",
    "Applied",
)
TRACKING_STAGE_RANK = {stage: index for index, stage in enumerate(TRACKING_STAGES)}
logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _scholarship_seed() -> list[dict[str, Any]]:
    return build_catalog(today_iso())


def _upload_path(stored_filename: str) -> Path:
    upload_root = UPLOAD_DIR.resolve()
    candidate = (upload_root / stored_filename).resolve()
    if candidate.parent != upload_root:
        raise HTTPException(status_code=400, detail="Invalid stored document path")
    return candidate


def _valid_file_signature(extension: str, content: bytes) -> bool:
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension in (".jpg", ".jpeg"):
        return content.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    return False


async def _remove_upload(stored_filename: str | None) -> None:
    if not stored_filename:
        return
    path = _upload_path(stored_filename)
    if path.is_file():
        await asyncio.to_thread(path.unlink)


async def _ensure_student_documents(user_id: str) -> None:
    required_for: dict[str, list[str]] = {}
    for scholarship in _scholarship_seed():
        for name in scholarship["required_documents"]:
            required_for.setdefault(name, []).append(scholarship["id"])

    for name, scholarship_ids in required_for.items():
        document = {
            "id": f"{user_id}-{name.lower().replace(' ', '-')}",
            "user_id": user_id,
            "name": name,
            "type": DOCUMENT_TYPES.get(name, "Supporting"),
            "available": False,
            "required_for": scholarship_ids,
            "extracted_value": None,
            "extraction_status": "Not uploaded",
        }
        await db.student_documents.update_one(
            {"user_id": user_id, "name": name},
            {"$setOnInsert": document},
            upsert=True,
        )


async def _ensure_tracking_stage(user_id: str, scholarship_id: str, new_stage: str) -> str:
    """Create or monotonically promote one user's tracking record."""
    if new_stage not in TRACKING_STAGE_RANK:
        raise ValueError(f"Unknown tracking stage: {new_stage}")

    key = {"user_id": user_id, "scholarship_id": scholarship_id}
    for _ in range(5):
        record = await db.tracking.find_one(key, {"stage": 1})
        if record is None:
            try:
                await db.tracking.insert_one({
                    **key,
                    "stage": new_stage,
                    "updated_at": datetime.now(timezone.utc),
                })
                return new_stage
            except DuplicateKeyError:
                continue

        current_stage = record.get("stage", "Discovered")
        if TRACKING_STAGE_RANK.get(current_stage, -1) >= TRACKING_STAGE_RANK[new_stage]:
            return current_stage

        result = await db.tracking.update_one(
            {**key, "stage": current_stage},
            {"$set": {"stage": new_stage, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.modified_count == 1:
            return new_stage

    raise RuntimeError("Tracking record changed too many times; retry the action")


async def _record_tracking_event(user_id: str, scholarship_id: str, stage: str) -> None:
    try:
        await _ensure_tracking_stage(user_id, scholarship_id, stage)
    except Exception:
        logger.exception("Could not record tracking event for user=%s scholarship=%s", user_id, scholarship_id)


async def _promote_ready_tracked_scholarships(user_id: str) -> None:
    tracked = await db.tracking.find({"user_id": user_id}, {"scholarship_id": 1}).to_list(100)
    tracked_ids = [item["scholarship_id"] for item in tracked]
    if not tracked_ids:
        return

    documents = await _documents(user_id)
    available_names = {document.name for document in documents if document.available}
    scholarships = await db.scholarships.find({"id": {"$in": tracked_ids}}).to_list(100)
    for scholarship in scholarships:
        required = scholarship.get("required_documents", [])
        if required and all(name in available_names for name in required):
            await _ensure_tracking_stage(user_id, scholarship["id"], "Documents")


async def ensure_demo_data() -> None:
    for item in _scholarship_seed():
        await db.scholarships.update_one({"id": item["id"]}, {"$set": item}, upsert=True)

    demo_user = {"id": "demo-aarav", "full_name": "Aarav", "email": DEMO_EMAIL, "password_hash": _hash_password("demo123")}
    await db.users.update_one({"id": demo_user["id"]}, {"$set": demo_user}, upsert=True)
    profile = Profile(user_id=demo_user["id"], full_name="Aarav", course="B.Tech", branch="Computer Engineering", year="2nd Year", marks=82, state="Maharashtra", category="Open", annual_income=210000, income_certificate=True)
    await db.profiles.update_one({"user_id": demo_user["id"]}, {"$setOnInsert": profile.model_dump()}, upsert=True)
    docs = [
        {"id": "doc-marksheet", "name": "Marksheet", "type": "Academic", "available": True, "required_for": ["national-stem", "maharashtra-support", "future-tech-merit", "inclusive-campus", "digital-learning"], "extracted_value": "82% • B.Tech Computer Engineering", "extraction_status": "Verified"},
        {"id": "doc-income", "name": "Income Certificate", "type": "Financial", "available": True, "required_for": ["national-stem", "maharashtra-support", "inclusive-campus", "digital-learning"], "extracted_value": "₹2.1 lakh annual family income", "extraction_status": "Verified"},
        {"id": "doc-domicile", "name": "Domicile Certificate", "type": "Identity", "available": False, "required_for": ["national-stem", "maharashtra-support"], "extracted_value": None, "extraction_status": "Not uploaded"},
        {"id": "doc-bank", "name": "Bank Details", "type": "Payment", "available": True, "required_for": ["national-stem", "maharashtra-support", "future-tech-merit", "digital-learning"], "extracted_value": "Verified manually", "extraction_status": "Manual review"},
        {"id": "doc-category", "name": "Category Certificate", "type": "Eligibility", "available": False, "required_for": ["inclusive-campus"], "extracted_value": None, "extraction_status": "Not uploaded"},
    ]
    for doc in docs:
        await db.student_documents.update_one({"id": doc["id"], "user_id": demo_user["id"]}, {"$setOnInsert": {**doc, "user_id": demo_user["id"]}}, upsert=True)
    for scholarship in _scholarship_seed():
        await db.tracking.update_one({"user_id": demo_user["id"], "scholarship_id": scholarship["id"]}, {"$setOnInsert": {"user_id": demo_user["id"], "scholarship_id": scholarship["id"], "stage": "Discovered", "updated_at": datetime.now(timezone.utc)}}, upsert=True)


async def _get_user(session: str | None) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Please sign in or load Demo Mode")
    record = await db.sessions.find_one({"token": session})
    if not record:
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"id": record["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _profile(session: str | None) -> tuple[dict, Profile]:
    user = await _get_user(session)
    record = await db.profiles.find_one({"user_id": user["id"]})
    if not record:
        record = Profile(user_id=user["id"], full_name=user["full_name"]).model_dump()
        await db.profiles.insert_one(record)
    return user, Profile(**record)


async def _all_scholarships() -> list[Scholarship]:
    records = await db.scholarships.find().to_list(100)
    return [Scholarship(**record) for record in records]


async def _documents(user_id: str) -> list[StudentDocument]:
    await _ensure_student_documents(user_id)
    records = await db.student_documents.find({"user_id": user_id}).sort("name", 1).to_list(100)
    return [StudentDocument(**record) for record in records]


def _condition_status(condition: str, profile: Profile, required: str, value: str) -> tuple[str, str]:
    if condition == "course":
        ok = profile.course.lower() == required.lower() or required.lower().startswith("any ")
        return ("MATCH" if ok else "FAIL", f"Your course is {profile.course}; this record requires {required}.")
    if condition == "marks":
        if profile.score_type != "Percentage":
            return "REVIEW", f"Your {profile.score_type} is {profile.score_value} on a {profile.score_scale}-point scale. This rule is stored as a percentage, and no official conversion formula is recorded."
        try:
            score = float(profile.score_value)
        except ValueError:
            return "NOT_AVAILABLE", "Enter a valid percentage to evaluate this academic condition."
        ok = score >= float(required)
        return ("MATCH" if ok else "FAIL", f"Your percentage is {score:g}%; the minimum is {required}%.")
    if condition == "income":
        ok = profile.annual_income <= float(required)
        return ("MATCH" if ok else "FAIL", f"Your annual income is ₹{profile.annual_income:,.0f}; the limit is ₹{float(required):,.0f}.")
    if condition == "state":
        ok = profile.state.lower() == required.lower()
        return ("MATCH" if ok else "FAIL", f"Your state is {profile.state}; this record requires {required}.")
    if condition == "category":
        if profile.category.lower() == "open" and profile.disability_status.lower() == "no":
            return "REVIEW", "A category or disability document is needed to confirm this condition."
        return "MATCH", f"Your profile indicates {profile.category}; confirm the supporting certificate."
    return "NOT_AVAILABLE", "This condition needs manual verification."


async def _eligibility(scholarship: Scholarship, profile: Profile, documents: list[StudentDocument]) -> EligibilityResult:
    rule = scholarship.rule
    conditions: list[Condition] = []
    if not rule.details_verified:
        conditions.append(Condition(key="official-verification", label="Official eligibility details", required="Verify on the official source", status="REVIEW", student_value="Profile saved", explanation="Eligibility details require official verification. Vidyadwar does not infer missing criteria."))
    else:
        structured_conditions = []
        if rule.course is not None:
            structured_conditions.append(("course", "Course", rule.course, profile.course or "Not provided"))
        if rule.minimum_marks is not None:
            score_display = f"{profile.score_value}%" if profile.score_type == "Percentage" else f"{profile.score_value} {profile.score_type} (scale {profile.score_scale})"
            structured_conditions.append(("marks", "Academic requirement", str(rule.minimum_marks), score_display))
        if rule.income_limit is not None:
            structured_conditions.append(("income", "Family income", str(rule.income_limit), f"₹{profile.annual_income:,.0f}"))
        for key, label, required, value in structured_conditions:
            status, explanation = _condition_status(key, profile, required, value)
            required_text = f"Minimum {required}%" if key == "marks" else required
            conditions.append(Condition(key=key, label=label, required=required_text, status=status, student_value=value, explanation=explanation))
    if rule.state:
        status, explanation = _condition_status("state", profile, rule.state, profile.state)
        conditions.append(Condition(key="state", label="State / domicile", required=rule.state, status=status, student_value=profile.state, explanation=explanation))
    if rule.category:
        status, explanation = _condition_status("category", profile, rule.category, profile.category)
        conditions.append(Condition(key="category", label="Category condition", required=rule.category, status=status, student_value=profile.category, explanation=explanation))
    if any(item.status == "FAIL" for item in conditions):
        overall = "NOT_ELIGIBLE"
    elif any(item.status in ("REVIEW", "NOT_AVAILABLE") for item in conditions):
        overall = "REVIEW"
    else:
        overall = "ELIGIBLE"
    available = sum(1 for doc in documents if doc.available and scholarship.id in doc.required_for)
    total = sum(1 for name in scholarship.required_documents if any(doc.name == name for doc in documents))
    total = max(total, len(scholarship.required_documents))
    next_action = "Ready to review" if available == total else f"Add {total - available} missing document" + ("s" if total - available != 1 else "")
    return EligibilityResult(scholarship=scholarship, conditions=conditions, overall_status=overall, documents_ready=available, documents_total=total, next_action=next_action)


@router.post("/auth/demo", response_model=AuthResponse)
async def demo_login(response: Response):
    user = await db.users.find_one({"email": DEMO_EMAIL})
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": user["id"], "created_at": datetime.now(timezone.utc)})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    profile = Profile(**(await db.profiles.find_one({"user_id": user["id"]})))
    return AuthResponse(user=User(id=user["id"], full_name=user["full_name"], email=user["email"]), profile=profile, demo_mode=True)


@router.post("/auth/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, response: Response):
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if await db.users.find_one({"email": str(payload.email)}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(full_name=payload.full_name, email=payload.email)
    await db.users.insert_one({**user.model_dump(), "password_hash": _hash_password(payload.password)})
    profile = Profile(user_id=user.id, full_name=user.full_name)
    await db.profiles.insert_one(profile.model_dump())
    await _ensure_student_documents(user.id)
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": user.id, "created_at": datetime.now(timezone.utc)})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    return AuthResponse(user=user, profile=profile)


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: AuthCredentials, response: Response):
    user = await db.users.find_one({"email": str(payload.email)})
    if not user or user.get("password_hash") != _hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": user["id"], "created_at": datetime.now(timezone.utc)})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    _, profile = await _profile(token)
    return AuthResponse(user=User(id=user["id"], full_name=user["full_name"], email=user["email"]), profile=profile)


@router.get("/auth/me", response_model=AuthResponse)
async def me(response: Response, vidyadwar_session: str | None = Cookie(default=None)):
    user, profile = await _profile(vidyadwar_session)
    return AuthResponse(user=User(id=user["id"], full_name=user["full_name"], email=user["email"]), profile=profile, demo_mode=user["email"] == DEMO_EMAIL)


@router.post("/auth/logout")
async def logout(response: Response, vidyadwar_session: str | None = Cookie(default=None)):
    if vidyadwar_session:
        await db.sessions.delete_one({"token": vidyadwar_session})
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/profile", response_model=Profile)
async def get_profile(vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    return profile


@router.put("/profile", response_model=Profile)
async def update_profile(payload: ProfileUpdate, vidyadwar_session: str | None = Cookie(default=None)):
    user, _ = await _profile(vidyadwar_session)
    profile_data = payload.model_dump()
    if not payload.score_value:
        profile_data["score_value"] = f"{payload.marks:g}"
    if payload.score_type == "Percentage":
        try:
            profile_data["marks"] = float(profile_data["score_value"])
        except ValueError:
            raise HTTPException(status_code=422, detail="Enter a valid percentage")
    updated = Profile(user_id=user["id"], **profile_data)
    await db.profiles.update_one({"user_id": user["id"]}, {"$set": updated.model_dump()}, upsert=True)
    await db.users.update_one({"id": user["id"]}, {"$set": {"full_name": updated.full_name}})
    return updated


@router.get("/scholarships", response_model=list[EligibilityResult])
async def scholarships(vidyadwar_session: str | None = Cookie(default=None)):
    if vidyadwar_session:
        _, profile = await _profile(vidyadwar_session)
    else:
        profile = Profile(**(await db.profiles.find_one({"user_id": "demo-aarav"})))
    docs = await _documents(profile.user_id)
    return [await _eligibility(item, profile, docs) for item in await _all_scholarships()]


@router.get("/scholarships/{scholarship_id}", response_model=EligibilityResult)
async def scholarship_detail(scholarship_id: str, vidyadwar_session: str | None = Cookie(default=None)):
    if vidyadwar_session:
        _, profile = await _profile(vidyadwar_session)
    else:
        profile = Profile(**(await db.profiles.find_one({"user_id": "demo-aarav"})))
    item = await db.scholarships.find_one({"id": scholarship_id})
    if not item:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    if vidyadwar_session:
        await _record_tracking_event(profile.user_id, scholarship_id, "Discovered")
    return await _eligibility(Scholarship(**item), profile, await _documents(profile.user_id))


@router.get("/documents", response_model=list[StudentDocument])
async def documents(vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    return await _documents(profile.user_id)


@router.patch("/documents/{document_id}", response_model=StudentDocument)
async def update_document(document_id: str, payload: DocumentUpdate, vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    result = await db.student_documents.find_one_and_update({"id": document_id, "user_id": profile.user_id}, {"$set": {"available": payload.available, "updated_at": datetime.now(timezone.utc), "extraction_status": "Manual review" if payload.available else "Not uploaded"}}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    if payload.available:
        try:
            await _promote_ready_tracked_scholarships(profile.user_id)
        except Exception:
            logger.exception("Could not promote document-ready tracking for user=%s", profile.user_id)
    return StudentDocument(**result)


@router.post("/documents/{document_id}/upload", response_model=StudentDocument)
async def upload_document(document_id: str, file: UploadFile = File(...), vidyadwar_session: str | None = Cookie(default=None)):
    user = await _get_user(vidyadwar_session)
    record = await db.student_documents.find_one({"id": document_id, "user_id": user["id"]})
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")

    original_filename = (file.filename or "document").replace("\\", "/").split("/")[-1][:255]
    extension = Path(original_filename).suffix.lower()
    content_type = (file.content_type or "").lower()
    if extension not in ALLOWED_UPLOADS or content_type not in ALLOWED_UPLOADS[extension]:
        await file.close()
        raise HTTPException(status_code=400, detail="Upload a PDF, JPG, JPEG, or PNG file")

    content = await file.read(MAX_UPLOAD_SIZE + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty")
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="The maximum file size is 5 MB")
    if not _valid_file_signature(extension, content):
        raise HTTPException(status_code=400, detail="The file content does not match its file type")

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    new_path = _upload_path(stored_filename)
    await asyncio.to_thread(UPLOAD_DIR.mkdir, parents=True, exist_ok=True)
    try:
        await asyncio.to_thread(new_path.write_bytes, content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="The document could not be stored") from exc

    uploaded_at = datetime.now(timezone.utc)
    try:
        result = await db.student_documents.find_one_and_update(
            {"id": document_id, "user_id": user["id"]},
            {"$set": {
                "available": True,
                "has_file": True,
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "mime_type": content_type,
                "file_size": len(content),
                "uploaded_at": uploaded_at,
                "updated_at": uploaded_at,
                "extraction_status": "Manual review",
            }},
            return_document=True,
        )
    except Exception:
        await _remove_upload(stored_filename)
        raise
    if not result:
        await _remove_upload(stored_filename)
        raise HTTPException(status_code=404, detail="Document not found")

    await _remove_upload(record.get("stored_filename"))
    try:
        await _promote_ready_tracked_scholarships(user["id"])
    except Exception:
        logger.exception("Could not promote document-ready tracking for user=%s", user["id"])
    return StudentDocument(**result)


@router.get("/documents/{document_id}/file")
async def view_document_file(document_id: str, vidyadwar_session: str | None = Cookie(default=None)):
    user = await _get_user(vidyadwar_session)
    record = await db.student_documents.find_one({"id": document_id, "user_id": user["id"]})
    if not record or not record.get("stored_filename"):
        raise HTTPException(status_code=404, detail="Uploaded document not found")
    path = _upload_path(record["stored_filename"])
    if not path.is_file():
        await db.student_documents.update_one(
            {"id": document_id, "user_id": user["id"]},
            {"$set": {"available": False, "has_file": False, "extraction_status": "Not uploaded"}, "$unset": {"stored_filename": "", "original_filename": "", "mime_type": "", "file_size": "", "uploaded_at": ""}},
        )
        raise HTTPException(status_code=404, detail="The uploaded file is no longer available")
    return FileResponse(path=path, media_type=record.get("mime_type"), filename=record.get("original_filename") or "document", content_disposition_type="inline")


@router.delete("/documents/{document_id}/file", response_model=StudentDocument)
async def remove_document_file(document_id: str, vidyadwar_session: str | None = Cookie(default=None)):
    user = await _get_user(vidyadwar_session)
    record = await db.student_documents.find_one({"id": document_id, "user_id": user["id"]})
    if not record:
        raise HTTPException(status_code=404, detail="Document not found")
    if not record.get("stored_filename"):
        return StudentDocument(**record)

    updated_at = datetime.now(timezone.utc)
    result = await db.student_documents.find_one_and_update(
        {"id": document_id, "user_id": user["id"]},
        {"$set": {"available": False, "has_file": False, "updated_at": updated_at, "extraction_status": "Not uploaded"}, "$unset": {"stored_filename": "", "original_filename": "", "mime_type": "", "file_size": "", "uploaded_at": ""}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    await _remove_upload(record.get("stored_filename"))
    return StudentDocument(**result)


@router.post("/conflicts/analyze", response_model=ConflictAnalysis)
async def analyze_conflict(payload: CompareRequest, vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    items = await _all_scholarships()
    selected = [next((item for item in items if item.id == item_id), None) for item_id in payload.scholarship_ids]
    if any(item is None for item in selected):
        raise HTTPException(status_code=404, detail="Select two scholarships from the knowledge base")
    first, second = selected[0], selected[1]
    pair_rule = next((rule for rule in first.conflict_rules if rule.get("with") == second.id), None)
    if not pair_rule:
        pair_rule = next((rule for rule in second.conflict_rules if rule.get("with") == first.id), None)
    evidence = first.evidence if pair_rule else None
    stages: list[StageResult] = []
    stage_defs = [("application", "Application", "Both records can be reviewed and submitted independently."), ("selection", "Selection", "Selection remains with each official authority."), ("acceptance", "Acceptance", "Review each award undertaking before accepting both."), ("disbursement", "Receiving / Disbursement", "Check whether both benefits can be received together."), ("recheck", "Next Academic Year Re-check", "Re-check current rules before the next academic year.")]
    for key, label, compatible_summary in stage_defs:
        if not pair_rule:
            status = "Not Determined" if key in ("acceptance", "disbursement") else "Compatible"
            why = "No structured relationship is recorded for this pair; manual verification is still recommended." if status == "Not Determined" else compatible_summary
            stages.append(StageResult(id=key, label=label, status=status, summary=why, why=why, evidence=None))
            continue
        if key == pair_rule["stage"]:
            stages.append(StageResult(id=key, label=label, status=pair_rule["status"], summary=pair_rule["summary"], why=pair_rule["why"], evidence=evidence))
        elif key == "acceptance" or key == "recheck":
            stages.append(StageResult(id=key, label=label, status="Review", summary="Review the undertaking and any updated annual terms.", why="The prototype record does not settle this stage. Confirm the latest award conditions before deciding.", evidence=evidence))
        else:
            stages.append(StageResult(id=key, label=label, status="Compatible", summary=compatible_summary, why=compatible_summary, evidence=evidence))
    overall = next((stage.status for stage in stages if stage.status == "Conflict"), next((stage.status for stage in stages if stage.status == "Review"), "Compatible"))
    recommendation = "You can continue preparing both applications, but verify the receiving rule before accepting overlapping benefits." if pair_rule else "No conflict relationship is established in the available records. Verify both official sources before accepting awards."
    for scholarship in (first, second):
        await _record_tracking_event(profile.user_id, scholarship.id, "Compatibility Reviewed")
    return ConflictAnalysis(id=f"{first.id}-{second.id}", student_name=profile.full_name, scholarship_a=first, scholarship_b=second, stages=stages, overall_status=overall, recommendation=recommendation, disclaimer="Vidyadwar provides decision-support information. Final eligibility, approval, verification and disbursement remain with the official scholarship authority.")


@router.get("/dashboard", response_model=Dashboard)
async def dashboard(vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    docs = await _documents(profile.user_id)
    results = [await _eligibility(item, profile, docs) for item in await _all_scholarships()]
    tracking_records = await db.tracking.find({"user_id": profile.user_id}).to_list(100)
    by_id = {item.id: item for item in await _all_scholarships()}
    tracking = [TrackingItem(scholarship_id=record["scholarship_id"], scholarship_name=by_id.get(record["scholarship_id"], Scholarship(**_scholarship_seed()[0])).name, stage=record["stage"], updated_at=record.get("updated_at")) for record in tracking_records]
    missing = [doc.name for doc in docs if not doc.available]
    next_actions = [f"Upload {missing[0]}." if missing else "Review your strongest scholarship match.", "Compare the National STEM and Maharashtra support records.", "Verify prototype rules on the official portals before applying."]
    return Dashboard(profile=profile, scholarships=results, documents=docs, tracking=tracking, next_actions=next_actions, matched_count=sum(item.overall_status != "NOT_ELIGIBLE" for item in results), eligible_count=sum(item.overall_status == "ELIGIBLE" for item in results), review_count=sum(item.overall_status == "REVIEW" for item in results), action_count=len(missing), documents_ready=sum(doc.available for doc in docs), documents_total=len(docs))


@router.get("/readiness")
async def readiness(vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    docs = await _documents(profile.user_id)
    ready = sum(doc.available for doc in docs)
    total = len(docs)
    if total == 0:
        overall_status = "Setup Required"
        message = "Complete document setup before checking application readiness."
    elif ready < total:
        overall_status = "Action Required"
        message = "Application ready after you complete your missing documents."
    else:
        overall_status = "Application Ready"
        message = "Your document set is ready for a final official review."
    return {"eligibility_checked": True, "documents_ready": ready, "documents_total": total, "compatibility_reviewed": False, "official_evidence_available": True, "overall_status": overall_status, "message": message, "missing_documents": [doc.name for doc in docs if not doc.available]}


@router.get("/action-plan")
async def action_plan(vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    docs = await _documents(profile.user_id)
    return {"actions": [{"id": "document", "title": f"Upload {next((doc.name for doc in docs if not doc.available), 'missing document')}", "description": "Complete the document checklist before moving to an official application.", "priority": "Now", "done": bool(docs) and all(doc.available for doc in docs)}, {"id": "compare", "title": "Review scholarship compatibility", "description": "Open the stage-aware graph for your two strongest matches.", "priority": "Next", "done": False}, {"id": "verify", "title": "Verify the official rule", "description": "Use the official portal link before accepting any award.", "priority": "Before applying", "done": False}], "student_name": profile.full_name}


@router.get("/tracking", response_model=list[TrackingItem])
async def tracking(vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    items = await _all_scholarships()
    records = await db.tracking.find({"user_id": profile.user_id}).to_list(100)
    names = {item.id: item.name for item in items}
    return [TrackingItem(scholarship_id=item["scholarship_id"], scholarship_name=names.get(item["scholarship_id"], "Scholarship"), stage=item["stage"], updated_at=item.get("updated_at")) for item in records]


@router.patch("/tracking/{scholarship_id}", response_model=TrackingItem)
async def update_tracking(scholarship_id: str, payload: TrackingUpdate, vidyadwar_session: str | None = Cookie(default=None)):
    _, profile = await _profile(vidyadwar_session)
    item = await db.scholarships.find_one({"id": scholarship_id})
    if not item:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    updated = datetime.now(timezone.utc)
    await db.tracking.update_one({"user_id": profile.user_id, "scholarship_id": scholarship_id}, {"$set": {"stage": payload.stage, "updated_at": updated}}, upsert=True)
    return TrackingItem(scholarship_id=scholarship_id, scholarship_name=item["name"], stage=payload.stage, updated_at=updated)
