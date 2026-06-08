from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi_app.services.memory_files import read_json, write_json


def ensure_lecturer_profile(
    lecturer_id: str,
    *,
    name: str,
    department_id: str,
    faculty_id: Optional[str] = None,
) -> dict:
    path = f"lecturers/{lecturer_id}.json"
    data = read_json(path, {"lecturer_id": lecturer_id, "students": [], "classes": []})
    data.update(
        {
            "lecturer_id": lecturer_id,
            "name": name,
            "department_id": department_id,
            "faculty_id": faculty_id or data.get("faculty_id"),
        }
    )
    write_json(path, data)
    return data


def enroll_student(
    learner_id: str,
    *,
    name: str,
    department_id: str,
    level: str,
) -> None:
    """Attach a learner to all lecturer profiles in the same department."""
    roster_path = f"rosters/{department_id}.json"
    roster = read_json(roster_path, [])
    entry = {
        "learner_id": learner_id,
        "name": name,
        "department": department_id,
        "level": level,
    }
    if not any(r.get("learner_id") == learner_id for r in roster):
        roster.append(entry)
        write_json(roster_path, roster)

    from pathlib import Path

    from fastapi_app.services.memory_files import MEMORY_ROOT

    lecturers_dir = MEMORY_ROOT / "lecturers"
    if not lecturers_dir.exists():
        return

    for file in lecturers_dir.glob("*.json"):
        lecturer = read_json(f"lecturers/{file.name}", {})
        if lecturer.get("department_id") != department_id:
            continue
        students: List[dict] = list(lecturer.get("students") or [])
        if any(s.get("learner_id") == learner_id for s in students):
            continue
        students.append(entry)
        lecturer["students"] = students
        write_json(f"lecturers/{file.name}", lecturer)
