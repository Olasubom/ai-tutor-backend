from agency.core.routing import detect_routing_hint


def test_routes_study_plan_to_task_agent():
    hint = detect_routing_hint("Can you make a study plan for this week?")
    assert "TaskAgent" in hint


def test_routes_recommend():
    hint = detect_routing_hint("What should I study next?")
    assert "RecommendationAgent" in hint


def test_routes_progress():
    hint = detect_routing_hint("How am I doing on calculus?")
    assert "KnowledgeTracingAgent" in hint
