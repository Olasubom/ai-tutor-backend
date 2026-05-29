from agency.core.tools.database import Database, DatabaseConfig
from agency.core.tools.repository import LearnerRepository


def test_upsert_and_list_content_items(tmp_path):
    db_path = tmp_path / "content_repo.db"
    db = Database(DatabaseConfig(url=f"sqlite:///{db_path.as_posix()}"))
    repo = LearnerRepository(db)
    repo.create_tables()

    items = [
        {
            "id": "src_1",
            "title": "Factoring Video",
            "topic": "Factoring Quadratic Equations",
            "modality": "video",
            "source_type": "youtube",
            "provider": "YouTube",
            "source_url": "https://youtube.com/watch?v=abc",
        }
    ]
    written = repo.upsert_content_items(items)
    listed = repo.list_content_items(limit=10)
    assert written == 1
    assert len(listed) == 1
    assert listed[0]["id"] == "src_1"
    assert listed[0]["source_type"] == "youtube"

