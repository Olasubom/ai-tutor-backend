from __future__ import annotations

import csv
import io
import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import AdminNucId, College, Course, Department
from fastapi_app.auth.memory import init_structured_memory
from fastapi_app.auth.models import User
from fastapi_app.auth.utils import get_current_user, require_role
from fastapi_app.database import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


class CollegeCreate(BaseModel):
    name: str


class DepartmentCreate(BaseModel):
    name: str
    college_id: str


class CourseCreate(BaseModel):
    course_code: str
    course_title: str
    department_id: str
    level: str
    credit_units: int = 3
    semester: str = "First"
    course_type: str = "Compulsory"
    description: Optional[str] = None


class CourseUpdate(BaseModel):
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    level: Optional[str] = None
    credit_units: Optional[int] = None
    semester: Optional[str] = None
    course_type: Optional[str] = None
    description: Optional[str] = None


class NucIdCreate(BaseModel):
    nuc_staff_id: str
    label: Optional[str] = None
    college: str
    department: str


def _course_dict(c: Course) -> dict:
    return {
        "id": c.id,
        "course_code": c.course_code,
        "course_title": c.course_title,
        "department_id": c.department_id,
        "level": c.level,
        "credit_units": c.credit_units,
        "semester": c.semester,
        "course_type": c.course_type,
        "description": c.description,
    }


@router.post("/colleges")
def create_college(
    payload: CollegeCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    if db.scalar(select(College).where(College.name == payload.name.strip())):
        raise HTTPException(status_code=409, detail="College already exists")
    college = College(name=payload.name.strip())
    db.add(college)
    db.commit()
    db.refresh(college)
    return {"id": college.id, "name": college.name}


@router.get("/colleges")
def list_colleges(
    db: Annotated[Session, Depends(get_db)],
) -> List[dict]:
    rows = db.scalars(select(College).order_by(College.name)).all()
    return [{"id": c.id, "name": c.name} for c in rows]


@router.delete("/colleges/{college_id}")
def delete_college(
    college_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    college = db.get(College, college_id)
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    if db.scalars(select(Department).where(Department.college_id == college_id)).first():
        raise HTTPException(status_code=400, detail="Remove departments in this college first")
    db.delete(college)
    db.commit()
    return {"ok": True}


@router.post("/departments")
def create_department(
    payload: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    if not db.get(College, payload.college_id):
        raise HTTPException(status_code=404, detail="College not found")
    dept = Department(name=payload.name.strip(), college_id=payload.college_id)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return {"id": dept.id, "name": dept.name, "college_id": dept.college_id}


@router.get("/departments")
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    college_id: Optional[str] = Query(default=None),
) -> List[dict]:
    q = select(Department)
    if college_id:
        q = q.where(Department.college_id == college_id)
    rows = db.scalars(q.order_by(Department.name)).all()
    return [{"id": d.id, "name": d.name, "college_id": d.college_id} for d in rows]


@router.delete("/departments/{department_id}")
def delete_department(
    department_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if db.scalars(select(Course).where(Course.department_id == department_id)).first():
        raise HTTPException(status_code=400, detail="Remove courses in this department first")
    db.delete(dept)
    db.commit()
    return {"ok": True}


@router.post("/courses")
def create_course(
    payload: CourseCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    if not db.get(Department, payload.department_id):
        raise HTTPException(status_code=404, detail="Department not found")
    course = Course(
        course_code=payload.course_code.strip().upper(),
        course_title=payload.course_title.strip(),
        department_id=payload.department_id,
        level=payload.level,
        credit_units=payload.credit_units,
        semester=payload.semester,
        course_type=payload.course_type,
        description=payload.description,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return _course_dict(course)


@router.get("/courses")
def list_courses(
    db: Annotated[Session, Depends(get_db)],
    department_id: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
) -> List[dict]:
    q = select(Course)
    if department_id:
        q = q.where(Course.department_id == department_id)
    if level:
        q = q.where(Course.level == level)
    rows = db.scalars(q.order_by(Course.course_code)).all()
    return [_course_dict(c) for c in rows]


@router.put("/courses/{course_id}")
def update_course(
    course_id: str,
    payload: CourseUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return _course_dict(course)


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"ok": True}


@router.post("/courses/bulk-import")
async def bulk_import_courses(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
    file: UploadFile = File(...),
    department_id: str = Query(...),
) -> dict:
    if not db.get(Department, department_id):
        raise HTTPException(status_code=404, detail="Department not found")
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    for row in reader:
        code = (row.get("course_code") or row.get("code") or "").strip()
        title = (row.get("course_title") or row.get("title") or "").strip()
        if not code or not title:
            continue
        course = Course(
            course_code=code.upper(),
            course_title=title,
            department_id=department_id,
            level=str(row.get("level") or "200"),
            credit_units=int(row.get("credit_units") or row.get("units") or 3),
            semester=row.get("semester") or "First",
            course_type=row.get("course_type") or row.get("type") or "Compulsory",
            description=row.get("description"),
        )
        db.add(course)
        created += 1
    db.commit()
    return {"imported": created}


@router.post("/nuc-ids")
def create_nuc_id(
    payload: NucIdCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    staff_id = payload.nuc_staff_id.strip().upper()
    if db.scalar(select(AdminNucId).where(AdminNucId.nuc_staff_id == staff_id)):
        raise HTTPException(status_code=409, detail="NUC ID already exists")
    row = AdminNucId(
        nuc_staff_id=staff_id,
        label=payload.label,
        college=payload.college,
        department=payload.department,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "nuc_staff_id": row.nuc_staff_id, "status": row.status}


@router.get("/nuc-ids")
def list_nuc_ids(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> List[dict]:
    rows = db.scalars(select(AdminNucId).order_by(AdminNucId.added_at.desc())).all()
    return [
        {
            "id": r.id,
            "nuc_staff_id": r.nuc_staff_id,
            "label": r.label,
            "college": r.college,
            "department": r.department,
            "status": r.status,
            "added_at": r.added_at.isoformat(),
        }
        for r in rows
    ]


@router.patch("/nuc-ids/{nuc_id}/revoke")
def revoke_nuc_id(
    nuc_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    row = db.get(AdminNucId, nuc_id)
    if not row:
        raise HTTPException(status_code=404, detail="NUC ID not found")
    row.status = "revoked"
    db.commit()
    return {"ok": True}


@router.delete("/nuc-ids/{nuc_id}")
def delete_nuc_id(
    nuc_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    row = db.get(AdminNucId, nuc_id)
    if not row:
        raise HTTPException(status_code=404, detail="NUC ID not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/lecturers/pending")
def pending_lecturers(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> List[dict]:
    rows = db.scalars(
        select(User).where(User.role == "lecturer", User.lecturer_status == "pending_verification")
    ).all()
    return [
        {
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "nuc_staff_id": u.nuc_staff_id,
            "college": u.college,
            "department": u.department,
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.patch("/lecturers/{user_id}/approve")
def approve_lecturer(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    user = db.get(User, user_id)
    if not user or user.role != "lecturer":
        raise HTTPException(status_code=404, detail="Lecturer not found")
    user.is_verified = True
    user.lecturer_status = "approved"
    user.is_active = True
    db.commit()
    init_structured_memory(user.id, user.name)
    return {"ok": True}


@router.patch("/lecturers/{user_id}/reject")
def reject_lecturer(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    user = db.get(User, user_id)
    if not user or user.role != "lecturer":
        raise HTTPException(status_code=404, detail="Lecturer not found")
    user.lecturer_status = "rejected"
    user.is_active = False
    db.commit()
    return {"ok": True}


@router.get("/students")
def list_students(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
    department: Optional[str] = Query(default=None),
    college: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
) -> List[dict]:
    q = select(User).where(User.role == "student")
    if department:
        q = q.where(User.department == department)
    if college:
        q = q.where(User.college == college)
    if level:
        q = q.where(User.academic_level == level)
    rows = db.scalars(q.order_by(User.created_at.desc())).all()
    return [
        {
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "department": u.department,
            "college": u.college,
            "academic_level": u.academic_level,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.patch("/students/{user_id}/suspend")
def suspend_student(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    user = db.get(User, user_id)
    if not user or user.role != "student":
        raise HTTPException(status_code=404, detail="Student not found")
    user.is_active = False
    db.commit()
    return {"ok": True}


@router.delete("/students/{user_id}")
def delete_student(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    user = db.get(User, user_id)
    if not user or user.role != "student":
        raise HTTPException(status_code=404, detail="Student not found")
    if user.id == current["user_id"]:
        raise HTTPException(status_code=403, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "Student deleted"}


@router.get("/lecturers")
def list_lecturers(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_role("admin"))],
    status: Optional[str] = Query(default=None),
) -> List[dict]:
    q = select(User).where(User.role == "lecturer")
    if status:
        q = q.where(User.lecturer_status == status)
    rows = db.scalars(q.order_by(User.created_at.desc())).all()
    return [
        {
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "nuc_staff_id": u.nuc_staff_id,
            "college": u.college,
            "department": u.department,
            "lecturer_status": u.lecturer_status,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.delete("/lecturers/{user_id}")
def delete_lecturer(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[dict, Depends(require_role("admin"))],
) -> dict:
    user = db.get(User, user_id)
    if not user or user.role != "lecturer":
        raise HTTPException(status_code=404, detail="Lecturer not found")
    if user.id == current["user_id"]:
        raise HTTPException(status_code=403, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "Lecturer deleted"}
