from pathlib import Path

from agency.core.memory.learner_memory import LearnerMemory
from agency.core.context import reset_runtime


def test_update_learner_profile_and_get_relevant_memory(tmp_path: Path):
    reset_runtime()
    mem = LearnerMemory(tmp_path / "memory", short_term_max_turns=10)
    learner_id = "test-learner"

    mem.update_learner_profile(
        learner_id,
        [{"topic": "algebra", "correct": False}],
    )
    bundle = mem.get_relevant_memory(learner_id, "algebra practice", k=3)

    assert bundle["learner_id"] == learner_id
    assert len(bundle["recent_turns"]) >= 1
    assert "profile_highlights" in bundle
