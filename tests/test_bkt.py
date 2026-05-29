from agency.core.services.bkt import apply_events, default_skill_state, update_bkt, BKTParams


def test_bkt_increases_on_correct():
    p = update_bkt(0.2, True, BKTParams())
    assert p > 0.2


def test_apply_events_updates_summary():
    mastery = {"algebra": default_skill_state()}
    events = [{"topic": "algebra", "correct": False}, {"topic": "algebra", "correct": True}]
    mastery, summary = apply_events(mastery, events)
    assert "algebra" in summary["topic_mastery"]
    assert summary["topic_mastery"]["algebra"] >= 0.0
