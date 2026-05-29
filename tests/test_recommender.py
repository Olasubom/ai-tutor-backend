from agency.core.services.recommender import hybrid_recommend


def test_hybrid_recommend_returns_ranked_items():
    catalog = [
        {
            "id": "a",
            "title": "Factoring",
            "topics": ["factoring"],
            "difficulty": "intermediate",
            "duration_minutes": 30,
            "popularity_score": 0.8,
        }
    ]
    ranked, path = hybrid_recommend(
        catalog=catalog,
        weak_topics=["factoring"],
        preferences=[],
        memory_snippets=[],
        limit=3,
    )
    assert len(ranked) == 1
    assert ranked[0].item_id == "a"
    assert len(path) >= 1


def test_hybrid_recommend_prioritizes_preferred_modality():
    catalog = [
        {
            "id": "video_1",
            "title": "Intro Video",
            "topics": ["factoring"],
            "modality": "video",
            "bloom_level": "understand",
            "difficulty": "easy",
            "duration_minutes": 10,
            "popularity_score": 0.5,
        },
        {
            "id": "text_1",
            "title": "Text Notes",
            "topics": ["factoring"],
            "modality": "text",
            "bloom_level": "understand",
            "difficulty": "easy",
            "duration_minutes": 10,
            "popularity_score": 0.5,
        },
    ]
    ranked, _ = hybrid_recommend(
        catalog=catalog,
        weak_topics=["factoring"],
        preferences=[],
        memory_snippets=[],
        preferred_modalities=["video"],
        limit=2,
    )
    assert ranked[0].item_id == "video_1"
