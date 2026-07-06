from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course
from fastapi_app.auth.models import User
from fastapi_app.auth.utils import get_current_user, require_role
from fastapi_app.database import get_db
from fastapi_app.services import upload_service

router = APIRouter(prefix="/upload", tags=["Upload"])


def _get_user(db: Session, current: dict) -> User:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/material")
async def upload_material(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    course_id: str = Form(...),
    description: Optional[str] = Form(None),
    module_order: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(get_current_user)] = None,
):
    user = _get_user(db, current)
    if user.role not in {"lecturer", "admin"}:
        raise HTTPException(status_code=403, detail="Only lecturers and admins can upload materials")

    course = db.get(Course, course_id.strip())
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    content_type = upload_service.resolve_content_type(file.filename or "file", file.content_type)
    contents = await file.read()
    try:
        file_type, size_mb = upload_service.validate_upload(content_type, len(contents))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upload_id, file_path, safe_filename, r2_key = upload_service.save_material_file(contents, file.filename or "file")
    status = "approved" if user.role == "admin" else "pending_review"
    record = upload_service.create_material_record(
        upload_id=upload_id,
        safe_filename=safe_filename,
        original_name=file.filename or safe_filename,
        file_type=file_type,
        size_mb=size_mb,
        title=title.strip(),
        description=description,
        course_id=course.id,
        course_code=course.course_code,
        course_title=course.course_title,
        module_order=module_order,
        uploaded_by=user.id,
        uploaded_by_name=user.name,
        college=user.college,
        department=user.department,
        status=status,
        file_path=file_path,
        r2_key=r2_key,
    )
    upload_service.append_material(record)

    if status == "approved":
        background_tasks.add_task(upload_service.ingest_uploaded_material, record)

    return {
        "id": upload_id,
        "title": title.strip(),
        "course_id": course.id,
        "course_code": course.course_code,
        "file_type": file_type,
        "file_size_mb": round(size_mb, 2),
        "status": status,
        "message": (
            "Upload successful and published."
            if status == "approved"
            else "Upload successful. Pending admin review."
        ),
        "url": record["url"],
    }


@router.get("/material/{upload_id}/download")
async def download_material(
    upload_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(get_current_user)] = None,
):
    _get_user(db, current)
    record = upload_service.get_material(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Material not found")
    if record.get("status") != "approved" and record.get("uploaded_by") != current["user_id"] and current.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to download this material")
    file_path = upload_service.resolve_material_file_path(record)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=record.get("original_name") or "download")


@router.get("/materials")
def list_materials(
    status: Optional[str] = None,
    department: Optional[str] = None,
    subject: Optional[str] = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(get_current_user)] = None,
):
    user = _get_user(db, current)
    materials = upload_service.list_materials_for_user(
        role=user.role,
        user_id=user.id,
        status=status,
        department=department,
        subject=subject,
        uploader_id=user.id if mine else None,
    )
    return {"materials": materials, "total": len(materials)}


@router.get("/material/{upload_id}/embedding-status")
def material_embedding_status(
    upload_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(get_current_user)] = None,
):
    _get_user(db, current)
    from fastapi_app.services.module_embedding_service import get_embedding_status

    return get_embedding_status(upload_id, db)


@router.patch("/material/{upload_id}/approve")
def approve_material(
    upload_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("admin"))] = None,
):
    record = upload_service.update_material(
        upload_id,
        {
            "status": "approved",
            "approved_by": current["user_id"],
            "approved_at": upload_service._now(),
        },
    )
    if not record:
        raise HTTPException(status_code=404, detail="Material not found")
    background_tasks.add_task(upload_service.ingest_uploaded_material, record)
    return {"message": "Material approved and published", "id": upload_id}


class RejectMaterialRequest(BaseModel):
    reason: Optional[str] = None


@router.patch("/material/{upload_id}/reject")
def reject_material(
    upload_id: str,
    body: RejectMaterialRequest,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("admin"))] = None,
):
    record = upload_service.update_material(
        upload_id,
        {
            "status": "rejected",
            "rejection_reason": body.reason,
            "rejected_by": current["user_id"],
        },
    )
    if not record:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"message": "Material rejected", "id": upload_id}


@router.delete("/material/{upload_id}")
def delete_material(
    upload_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(get_current_user)] = None,
):
    user = _get_user(db, current)
    record = upload_service.get_material(upload_id)
    if not record:
        raise HTTPException(status_code=404, detail="Material not found")
    if record.get("uploaded_by") != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorised to delete this material")
    upload_service.delete_material(upload_id)
    return {"message": "Material deleted"}
