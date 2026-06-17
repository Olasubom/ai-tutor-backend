"""Lecturer course and module management routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.auth.models import User
from fastapi_app.auth.utils import get_current_user, require_role
from fastapi_app.database import get_db
from fastapi_app.schemas.lecturer_dashboard import (
    CourseCreate,
    CourseUpdate,
    ModuleCreate,
    ModuleReorderRequest,
    ModuleUpdate,
)
from fastapi_app.services import lecturer_course_service as svc

router = APIRouter(prefix="/lecturer/courses", tags=["Lecturer Courses"])


def _user(db: Session, current: dict) -> User:
    user = db.get(User, current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("")
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    user = _user(db, current)
    try:
        course = svc.create_course(
            db,
            user,
            code=payload.code,
            title=payload.title,
            description=payload.description,
            level=payload.level,
            college=payload.college,
            department=payload.department,
        )
        return svc.course_dict(course)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_courses(
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    return svc.list_lecturer_courses(db, _user(db, current))


@router.get("/{course_id}")
def get_course(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        return svc.get_course_with_modules(db, _user(db, current), course_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{course_id}")
def update_course(
    course_id: str,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        course = svc.update_course(db, _user(db, current), course_id, payload.model_dump(exclude_none=True))
        return svc.course_dict(course)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{course_id}")
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        svc.deactivate_course(db, _user(db, current), course_id)
        return {"message": "Course deactivated"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{course_id}/modules")
def add_module(
    course_id: str,
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        mod = svc.add_module(
            db,
            _user(db, current),
            course_id,
            title=payload.title,
            description=payload.description,
            order=payload.order,
            bloom_level=payload.bloom_level,
        )
        return svc.module_dict(mod, db)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{course_id}/modules")
def list_modules(
    course_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        data = svc.get_course_with_modules(db, _user(db, current), course_id)
        return data["modules"]
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{course_id}/modules/{module_id}")
def update_module(
    course_id: str,
    module_id: str,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        mod = svc.update_module(db, _user(db, current), course_id, module_id, payload.model_dump(exclude_none=True))
        return svc.module_dict(mod, db)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{course_id}/modules/{module_id}")
def delete_module(
    course_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        svc.delete_module(db, _user(db, current), course_id, module_id)
        return {"message": "Module deleted"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{course_id}/modules/{module_id}/reorder")
def reorder_module(
    course_id: str,
    module_id: str,
    payload: ModuleReorderRequest,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        svc.reorder_module(db, _user(db, current), course_id, module_id, payload.order)
        return {"message": "Module reordered"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


module_router = APIRouter(prefix="/lecturer", tags=["Lecturer Courses"])


@module_router.post("/modules/{module_id}/materials/{material_id}")
def link_material(
    module_id: str,
    material_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        link = svc.link_material(db, _user(db, current), module_id, material_id)
        return {"id": link.id, "module_id": link.module_id, "upload_id": link.upload_id}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@module_router.delete("/modules/{module_id}/materials/{material_id}")
def unlink_material(
    module_id: str,
    material_id: str,
    db: Session = Depends(get_db),
    current: Annotated[dict, Depends(require_role("lecturer", "admin"))] = None,
):
    try:
        svc.unlink_material(db, _user(db, current), module_id, material_id)
        return {"message": "Material unlinked"}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
