"""Lecturer course and module management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.admin.models import Course, Department
from fastapi_app.auth.models import User
from fastapi_app.models.lecturer_dashboard import CourseModule, ModuleMaterialLink
from fastapi_app.services import upload_service
from agency.core.tools.models import ContentItem


def _resolve_department_id(db: Session, user: User) -> Optional[str]:
    if not user.department:
        return None
    dept = db.scalars(select(Department).where(Department.name == user.department)).first()
    return dept.id if dept else None


def assert_lecturer_owns_course(db: Session, user: User, course: Course) -> None:
    if user.role == "admin":
        return
    if course.lecturer_id and course.lecturer_id == user.id:
        return
    dept_id = _resolve_department_id(db, user)
    if dept_id and course.department_id == dept_id and course.lecturer_id in (None, user.id):
        return
    raise PermissionError("Not authorized for this course")


def course_dict(c: Course) -> dict:
    return {
        "id": c.id,
        "code": c.course_code,
        "title": c.course_title,
        "description": c.description,
        "department_id": c.department_id,
        "level": c.level,
        "credit_units": c.credit_units,
        "semester": c.semester,
        "course_type": c.course_type,
        "lecturer_id": c.lecturer_id,
        "is_active": c.is_active,
    }


def create_course(
    db: Session,
    user: User,
    *,
    code: str,
    title: str,
    description: Optional[str],
    level: str,
    college: Optional[str] = None,
    department: Optional[str] = None,
) -> Course:
    del college
    dept_id = _resolve_department_id(db, user)
    if user.role == "admin" and department:
        dept = db.scalars(select(Department).where(Department.name == department)).first()
        if dept:
            dept_id = dept.id
    if not dept_id:
        raise ValueError("Department is required to create a course")

    course = Course(
        course_code=code.strip().upper(),
        course_title=title.strip(),
        description=description,
        department_id=dept_id,
        level=str(level),
        lecturer_id=user.id,
        is_active=True,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_lecturer_courses(db: Session, user: User) -> List[dict]:
    if user.role == "admin" and not user.department:
        rows = db.scalars(select(Course).where(Course.is_active == True).order_by(Course.course_code)).all()  # noqa: E712
    else:
        dept_id = _resolve_department_id(db, user)
        if not dept_id:
            return []
        rows = db.scalars(
            select(Course).where(
                Course.department_id == dept_id,
                Course.is_active == True,  # noqa: E712
            ).order_by(Course.course_code)
        ).all()
    return [course_dict(c) for c in rows]


def get_course_with_modules(db: Session, user: User, course_id: str) -> dict:
    course = db.get(Course, course_id)
    if not course or not course.is_active:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)
    modules = db.scalars(
        select(CourseModule).where(CourseModule.course_id == course_id).order_by(CourseModule.module_order)
    ).all()
    return {
        **course_dict(course),
        "modules": [module_dict(m, db) for m in modules],
    }


def update_course(db: Session, user: User, course_id: str, patch: dict) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)
    for key in ("course_code", "code"):
        if key in patch and patch[key]:
            course.course_code = str(patch[key]).strip().upper()
    if "title" in patch and patch["title"]:
        course.course_title = str(patch["title"]).strip()
    if "description" in patch:
        course.description = patch["description"]
    if "level" in patch and patch["level"]:
        course.level = str(patch["level"])
    db.commit()
    db.refresh(course)
    return course


def deactivate_course(db: Session, user: User, course_id: str) -> None:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)
    course.is_active = False
    db.commit()


def module_dict(m: CourseModule, db: Session) -> dict:
    links = db.scalars(select(ModuleMaterialLink).where(ModuleMaterialLink.module_id == m.id)).all()
    materials = []
    for link in links:
        mat = upload_service.get_material(link.upload_id)
        if mat:
            materials.append({**mat, "link_id": link.id})
    return {
        "id": m.id,
        "course_id": m.course_id,
        "title": m.title,
        "description": m.description,
        "order": m.module_order,
        "bloom_level": m.bloom_level,
        "materials": materials,
        "created_at": m.created_at.isoformat(),
    }


def add_module(db: Session, user: User, course_id: str, *, title: str, description: Optional[str], order: int, bloom_level: Optional[str]) -> CourseModule:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)
    mod = CourseModule(
        course_id=course_id,
        title=title.strip(),
        description=description,
        module_order=order,
        bloom_level=bloom_level,
    )
    db.add(mod)
    db.commit()
    db.refresh(mod)
    return mod


def update_module(db: Session, user: User, course_id: str, module_id: str, patch: dict) -> CourseModule:
    mod = db.get(CourseModule, module_id)
    if not mod or mod.course_id != course_id:
        raise ValueError("Module not found")
    course = db.get(Course, course_id)
    assert course is not None
    assert_lecturer_owns_course(db, user, course)
    if "title" in patch:
        mod.title = str(patch["title"]).strip()
    if "description" in patch:
        mod.description = patch["description"]
    if "order" in patch:
        mod.module_order = int(patch["order"])
    if "bloom_level" in patch:
        mod.bloom_level = patch["bloom_level"]
    db.commit()
    db.refresh(mod)
    return mod


def delete_module(db: Session, user: User, course_id: str, module_id: str) -> None:
    mod = db.get(CourseModule, module_id)
    if not mod or mod.course_id != course_id:
        raise ValueError("Module not found")
    course = db.get(Course, course_id)
    assert course is not None
    assert_lecturer_owns_course(db, user, course)
    db.delete(mod)
    db.commit()


def reorder_module(db: Session, user: User, course_id: str, module_id: str, new_order: int) -> None:
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)
    modules = db.scalars(
        select(CourseModule).where(CourseModule.course_id == course_id).order_by(CourseModule.module_order)
    ).all()
    target = next((m for m in modules if m.id == module_id), None)
    if not target:
        raise ValueError("Module not found")
    new_order = max(1, min(new_order, len(modules)))
    others = [m for m in modules if m.id != module_id]
    others.insert(new_order - 1, target)
    for idx, m in enumerate(others, start=1):
        m.module_order = idx
    db.commit()


def link_material(db: Session, user: User, module_id: str, upload_id: str) -> ModuleMaterialLink:
    mod = db.get(CourseModule, module_id)
    if not mod:
        raise ValueError("Module not found")
    course = db.get(Course, mod.course_id)
    assert course is not None
    assert_lecturer_owns_course(db, user, course)
    if not upload_service.get_material(upload_id):
        raise ValueError("Material not found")
    existing = db.scalars(
        select(ModuleMaterialLink).where(
            ModuleMaterialLink.module_id == module_id,
            ModuleMaterialLink.upload_id == upload_id,
        )
    ).first()
    if existing:
        return existing
    link = ModuleMaterialLink(module_id=module_id, upload_id=upload_id)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def unlink_material(db: Session, user: User, module_id: str, upload_id: str) -> None:
    mod = db.get(CourseModule, module_id)
    if not mod:
        raise ValueError("Module not found")
    course = db.get(Course, mod.course_id)
    assert course is not None
    assert_lecturer_owns_course(db, user, course)
    row = db.scalars(
        select(ModuleMaterialLink).where(
            ModuleMaterialLink.module_id == module_id,
            ModuleMaterialLink.upload_id == upload_id,
        )
    ).first()
    if row:
        db.delete(row)
        db.commit()


def list_course_materials(db: Session, user: User, course_id: str) -> List[dict]:
    """Approved ContentItem rows linked to a course (student curriculum modules)."""
    course = db.get(Course, course_id)
    if not course:
        raise ValueError("Course not found")
    assert_lecturer_owns_course(db, user, course)

    items = db.scalars(
        select(ContentItem)
        .where(
            ContentItem.course_id == course_id,
            ContentItem.status == "approved",
        )
        .order_by(ContentItem.module_order.asc().nullslast(), ContentItem.created_at.asc())
    ).all()
    return [
        {
            "id": item.item_id,
            "title": item.title,
            "description": (item.payload_json or {}).get("description"),
            "source_type": item.source_type,
            "module_order": item.module_order,
            "status": item.status,
            "embedding_status": item.embedding_status or "pending",
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]
