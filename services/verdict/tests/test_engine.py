from copy import deepcopy

import pytest
from pydantic import ValidationError

from contracts.profile import Profile
from contracts.scores import DimensionScore
from services.verdict.src.engine import (
    EvaluationInput,
    apply_challenge,
    check_gates,
    confidence,
    decide,
    load_config,
    sensitivity,
    weighted_score,
    what_would_make_go,
)

DIMENSIONS = (
    "demand_pain", "competition", "differentiation", "feasibility", "risk", "learning"
)


def case(values=(3.5, 2.0, 3.0, 4.0, 3.5, 4.5), **overrides):
    scores = [
        DimensionScore(
            dimension=dimension, score=value,
            confidence=0.8 if dimension == "risk" else 0.9,
            evidence_ids=[f"card{i}#c1"], features={}, reason="Cited score",
            rubric_version="v1", model="fixture",
        )
        for i, (dimension, value) in enumerate(zip(DIMENSIONS, values, strict=True))
    ]
    data = dict(
        idea_id="idea-1", run_id="run-1", version=1,
        profile=Profile(user_id="student", skills=["python"], hours_per_week=20,
                        weeks_available=10, team_size=1, compute="laptop",
                        goal="portfolio", interests=["education"]),
        scores=scores, independent_sources=5, platforms=2,
        estimated_build_hours=100, risk_blocker=None, duplicate_product=None,
        accepted_objections=[],
    )
    data.update(overrides)
    return EvaluationInput(**data)


def test_worked_example_and_weight_sensitivity():
    config = load_config()
    request = case()
    result = decide(request, config)
    assert result.verdict == "GO"
    assert result.score == pytest.approx(70.5)
    assert result.stability == "BORDERLINE"
    assert result.sensitivity.runs == 14
    assert any(f.verdict == "PIVOT" and "feasibility" in f.change for f in result.sensitivity.flips)
    lower_feasibility = dict(config.weights["portfolio"])
    lower_feasibility["feasibility"] = 20
    for dimension in DIMENSIONS:
        if dimension != "feasibility":
            lower_feasibility[dimension] *= 80 / 75
    assert weighted_score(request.scores, lower_feasibility) == pytest.approx(69.8666667)
    changed = deepcopy(request)
    changed.scores[1].score = 3.0
    improved = decide(changed, config)
    assert improved.score == pytest.approx(73.5)
    assert weighted_score(changed.scores, lower_feasibility) == pytest.approx(73.0666667)
    assert improved.stability == "STABLE"


@pytest.mark.parametrize(
    "changes,gate,detail",
    [
        ({"independent_sources": 1, "platforms": 1}, "evidence", "missing_sources"),
        ({"estimated_build_hours": 240}, "feasibility", "hours_gap"),
        ({"risk_blocker": "licence restriction"}, "risk", "blocker"),
        ({"duplicate_product": "ExistingApp", "values": (3.5, 2, 2.5, 4, 3.5, 4.5)}, "duplicate", "product"),
    ],
)
def test_gate_reasons(changes, gate, detail):
    failed = check_gates(case(**changes), load_config())
    assert failed[gate].status == "fail"
    assert detail in failed[gate].detail


def test_gate_order_stops_at_first_failure():
    gates = check_gates(case(independent_sources=1, platforms=1, estimated_build_hours=500,
                             risk_blocker="blocked", duplicate_product="clone"), load_config())
    assert list(gates) == ["evidence"]


def test_evidence_failure_explains_missing_counts():
    result = decide(case(independent_sources=1, platforms=1), load_config())
    assert result.verdict == "INSUFFICIENT_EVIDENCE"
    assert "2 more independent sources" in result.missing_evidence[0]
    assert "1 more platforms" in result.missing_evidence[0]


def test_config_rejects_missing_presets_dimensions_and_wrong_total():
    original = load_config().model_dump()
    missing_goal = deepcopy(original)
    del missing_goal["weights"]["startup"]
    with pytest.raises(ValidationError, match="goal presets"):
        type(load_config()).model_validate(missing_goal)
    missing_dimension = deepcopy(original)
    del missing_dimension["weights"]["startup"]["risk"]
    with pytest.raises(ValidationError, match="six nonnegative weights"):
        type(load_config()).model_validate(missing_dimension)
    wrong_total = deepcopy(original)
    wrong_total["weights"]["startup"]["risk"] = 16
    with pytest.raises(ValidationError, match="sum to 100"):
        type(load_config()).model_validate(wrong_total)
    degenerate = deepcopy(original)
    for dimension in DIMENSIONS:
        degenerate["weights"]["startup"][dimension] = 0
    degenerate["weights"]["startup"]["demand_pain"] = 100
    with pytest.raises(ValidationError, match="positive weights below 100"):
        type(load_config()).model_validate(degenerate)


def test_duplicate_dimension_input_is_rejected():
    data = case().model_dump()
    data["scores"][1]["dimension"] = "demand_pain"
    with pytest.raises(ValidationError, match="each dimension once"):
        EvaluationInput.model_validate(data)


def test_gate_facts_reject_impossible_counts_and_blank_blockers():
    with pytest.raises(ValidationError, match="platform count cannot exceed"):
        case(independent_sources=1, platforms=2)
    with pytest.raises(ValidationError):
        case(risk_blocker="   ")


def test_weighted_score_and_abstention():
    request = case()
    config = load_config()
    weights = config.weights["portfolio"]
    assert weighted_score(request.scores, weights) == pytest.approx(70.5)
    request.scores[-1] = request.scores[-1].model_copy(update={
        "abstained": True, "score": 0, "confidence": 0, "evidence_ids": []})
    assert weighted_score(request.scores, weights) == pytest.approx((352.5 - 90) / 80 * 20)
    assert confidence(request.scores, 5) == pytest.approx(0.7 * (4 * 0.9 + 0.8) / 6 + 0.3)


def test_all_abstained_scores_have_zero_weighted_score():
    request = case()
    for item in request.scores:
        item.abstained = True
        item.score = 0
        item.confidence = 0
        item.evidence_ids = []
    assert weighted_score(request.scores, load_config().weights["portfolio"]) == 0
    assert decide(request, load_config()).verdict == "INSUFFICIENT_EVIDENCE"


def test_confidence_and_abstention_edges():
    config = load_config()
    request = case()
    for score in request.scores:
        score.confidence = 2 / 7
    assert confidence(request.scores, 5) == pytest.approx(0.5)
    assert decide(request, config).verdict != "INSUFFICIENT_EVIDENCE"
    request.scores[0].abstained = True
    request.scores[0].score = 0
    request.scores[0].confidence = 0
    request.scores[0].evidence_ids = []
    assert decide(request, config).verdict == "INSUFFICIENT_EVIDENCE"
    request.scores[1].abstained = True
    request.scores[1].score = 0
    request.scores[1].confidence = 0
    request.scores[1].evidence_ids = []
    assert "two or more" in decide(request, config).missing_evidence[0]


def test_thresholds_and_floor_edges():
    config = load_config()
    assert decide(case(values=(3.5,) * 6), config).verdict == "GO"
    assert decide(case(values=(3.5, 3.5, 3.5, 3.5, 3.5, 1.0)), config).verdict == "PIVOT"
    assert decide(case(values=(2.5,) * 6), config).verdict == "PIVOT"
    assert decide(case(values=(2.499,) * 6), config).verdict == "NO-GO"
    assert decide(case(values=(5, 5, 5, 1.5, 5, 5)), config).verdict == "GO"
    low_floor = decide(case(values=(2, 2, 2, 1.0, 2, 2)), config)
    assert low_floor.verdict == "NO-GO"
    high_floor = decide(case(values=(5, 5, 5, 1.0, 5, 5)), config)
    assert high_floor.verdict == "PIVOT" and high_floor.weakest_dimension == "feasibility"


@pytest.mark.parametrize(
    "value,expected",
    [(3.4995, "PIVOT"), (3.5, "GO"), (2.4995, "NO-GO"), (2.5, "PIVOT")],
)
def test_exact_threshold_edges(value, expected):
    assert decide(case(values=(value,) * 6), load_config()).verdict == expected


def test_learning_is_exempt_from_floor():
    assert decide(case(values=(5, 5, 5, 5, 5, 1)), load_config()).verdict == "GO"


def test_challenge_caps_penalty_per_dimension():
    request = case(accepted_objections=["risk", "risk", "risk"])
    changed = apply_challenge(request.scores, request.accepted_objections, load_config())
    risk = changed[4]
    assert risk.score == 2.5
    assert risk.confidence == pytest.approx(0.5)
    assert request.scores[4].score == 3.5


def test_duplicate_exception_and_determinism():
    config = load_config()
    request = case(values=(3.5, 2, 2.5, 4, 3.5, 4.5), duplicate_product="ExistingApp")
    assert decide(request, config).verdict == "NO-GO"
    request.scores[2].score = 3.0
    assert decide(request, config).verdict == "GO"
    assert decide(request, config).model_dump() == decide(request, config).model_dump()


def test_whatif_returns_smallest_stable_go_change():
    config = load_config()
    request = case(values=(3.5, 2, 3, 4, 3.5, 4.5))
    candidate = what_would_make_go(request, config)
    assert candidate is not None
    assert candidate.new_verdict == "GO"
    assert "+0.5" in candidate.change


def test_whatif_can_close_feasibility_hours_gap():
    config = load_config()
    candidate = what_would_make_go(case(values=(4,) * 6, estimated_build_hours=240), config)
    assert candidate is not None
    assert "40.0 hours" in candidate.change
    assert candidate.new_verdict == "GO"


def test_whatif_does_not_claim_hours_fix_is_enough_for_low_scores():
    assert what_would_make_go(case(values=(2,) * 6, estimated_build_hours=240), load_config()) is None


def test_sensitivity_has_14_runs_without_recursive_search():
    result = sensitivity(case(), load_config())
    assert result.runs == 14
    assert all(1 <= flip.run <= 14 for flip in result.flips)


def test_sensitivity_change_labels_follow_config():
    config = load_config()
    config.sensitivity.weight_delta = 0.1
    config.sensitivity.score_delta = 0.5
    report = sensitivity(case(), config)
    assert report.flips
    assert all("20%" not in flip.change and "score +1" not in flip.change
               for flip in report.flips)
