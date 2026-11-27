"""Deterministic M11 rules. No model or network calls are made here."""

import os
from pathlib import Path
from typing import Literal, Self, get_args

import yaml  # type: ignore[import-untyped]
from pydantic import Field, NonNegativeFloat, NonNegativeInt, model_validator

from contracts.common import Dimension, Record, Text
from contracts.profile import Profile
from contracts.scores import DimensionScore
from contracts.verdict import (
    Flip,
    Gate,
    GateName,
    Outcome,
    Sensitivity,
    Thresholds,
    Verdict,
    Versions,
    WhatIf,
)

DIMENSIONS: tuple[Dimension, ...] = get_args(Dimension)
Goal = Literal["startup", "portfolio", "course_project"]


class GateConfig(Record):
    min_sources: int = Field(ge=1)
    min_platforms: int = Field(ge=1)
    duplicate_diff_min: float = Field(ge=0, le=5)


class ChallengeConfig(Record):
    penalty: float = Field(gt=0)
    max_penalty: float = Field(gt=0)
    conf_penalty: float = Field(ge=0, le=1)


class SensitivityConfig(Record):
    weight_delta: float = Field(gt=0, lt=1)
    score_delta: float = Field(gt=0, le=5)


class WhatIfConfig(Record):
    step: float = Field(gt=0, le=5)


class AbstainConfig(Record):
    max_abstained: int = Field(ge=0, le=5)


class VerdictConfig(Record):
    version: str = Field(min_length=1)
    weights: dict[Goal, dict[Dimension, float]]
    thresholds: Thresholds
    gates: GateConfig
    challenge: ChallengeConfig
    sensitivity: SensitivityConfig
    whatif: WhatIfConfig
    abstain: AbstainConfig

    @model_validator(mode="after")
    def valid_weights(self) -> Self:
        if set(self.weights) != set(get_args(Goal)):
            raise ValueError("all three goal presets are required")
        for preset in self.weights.values():
            if set(preset) != set(DIMENSIONS) or any(v < 0 for v in preset.values()):
                raise ValueError("each preset must have six nonnegative weights")
            if abs(sum(preset.values()) - 100) > 1e-8:
                raise ValueError("each preset must sum to 100")
            if any(v <= 0 or v >= 100 for v in preset.values()):
                raise ValueError("each preset needs positive weights below 100")
        return self


class EvaluationInput(Record):
    idea_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    profile: Profile
    scores: list[DimensionScore] = Field(min_length=6, max_length=6)
    independent_sources: NonNegativeInt
    platforms: NonNegativeInt
    estimated_build_hours: NonNegativeFloat
    risk_blocker: Text | None = None
    duplicate_product: Text | None = None
    accepted_objections: list[Dimension] = Field(default_factory=list)

    @model_validator(mode="after")
    def all_dimensions_once(self) -> Self:
        if {s.dimension for s in self.scores} != set(DIMENSIONS):
            raise ValueError("scores must cover each dimension once")
        if self.platforms > self.independent_sources:
            raise ValueError("platform count cannot exceed independent source count")
        return self


def load_config(path: str | Path | None = None) -> VerdictConfig:
    """Read each time so a changed mounted ConfigMap version takes effect."""
    location = Path(path or os.getenv("VERDICT_CONFIG_PATH") or
                    Path(__file__).resolve().parents[3] / "k8s" / "base" / "config" / "verdict.yaml")
    with location.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    return VerdictConfig.model_validate(data)


def available_hours(profile: Profile) -> int:
    return profile.hours_per_week * profile.weeks_available * profile.team_size


def check_gates(request: EvaluationInput, config: VerdictConfig,
                scores: list[DimensionScore] | None = None) -> dict[GateName, Gate]:
    """Stop at the first failed hard gate, in the brief's specified order."""
    by_dimension = {s.dimension: s for s in (scores or request.scores)}
    gates: dict[GateName, Gate] = {}
    missing_sources = max(0, config.gates.min_sources - request.independent_sources)
    missing_platforms = max(0, config.gates.min_platforms - request.platforms)
    if missing_sources or missing_platforms:
        gates["evidence"] = Gate(status="fail", reason="Independent evidence is missing",
                                 detail={"missing_sources": missing_sources,
                                         "missing_platforms": missing_platforms})
        return gates
    gates["evidence"] = Gate(status="pass", reason="Evidence minimum met", detail={})

    gap = request.estimated_build_hours - available_hours(request.profile)
    if gap > 0:
        gates["feasibility"] = Gate(status="fail", reason="Estimated effort exceeds available hours",
                                    detail={"hours_gap": gap})
        return gates
    gates["feasibility"] = Gate(status="pass", reason="Effort fits available hours", detail={})

    if request.risk_blocker:
        gates["risk"] = Gate(status="fail", reason="Legal or safety blocker",
                             detail={"blocker": request.risk_blocker})
        return gates
    gates["risk"] = Gate(status="pass", reason="No named legal or safety blocker", detail={})

    differentiation = by_dimension["differentiation"]
    if request.duplicate_product and (
        differentiation.abstained or differentiation.score < config.gates.duplicate_diff_min
    ):
        gates["duplicate"] = Gate(status="fail", reason="Existing product has the same core features",
                                  detail={"product": request.duplicate_product})
        return gates
    gates["duplicate"] = Gate(status="pass", reason="No disqualifying duplicate", detail={})
    return gates


def weighted_score(scores: list[DimensionScore], weights: dict[Dimension, float]) -> float:
    active = [s for s in scores if not s.abstained]
    total_weight = sum(weights[s.dimension] for s in active)
    if not total_weight:
        return 0.0
    return sum(weights[s.dimension] * s.score for s in active) * 20 / total_weight


def confidence(scores: list[DimensionScore], n_sources: int) -> float:
    return 0.7 * sum(s.confidence for s in scores) / 6 + 0.3 * min(1, n_sources / 5)


def apply_challenge(scores: list[DimensionScore], objections: list[Dimension],
                    config: VerdictConfig) -> list[DimensionScore]:
    counts = {dimension: objections.count(dimension) for dimension in DIMENSIONS}
    adjusted: list[DimensionScore] = []
    for score in scores:
        count = counts[score.dimension]
        penalty = min(config.challenge.max_penalty, count * config.challenge.penalty)
        adjusted.append(score.model_copy(update={
            "score": max(0, score.score - penalty) if not score.abstained else 0,
            "confidence": max(0, score.confidence - count * config.challenge.conf_penalty)
            if not score.abstained else 0,
        }))
    return adjusted


def _base_decision(request: EvaluationInput, config: VerdictConfig,
                   scores: list[DimensionScore], weights: dict[Dimension, float]
                   ) -> tuple[Outcome, float | None, float, dict[GateName, Gate],
                              Dimension | None, list[str]]:
    gates = check_gates(request, config, scores)
    conf = confidence(scores, request.independent_sources)
    if (failed := next((name for name, gate in gates.items() if gate.status == "fail"), None)):
        if failed == "evidence":
            return ("INSUFFICIENT_EVIDENCE", None, conf, gates, None,
                    [f"Need {gates[failed].detail['missing_sources']} more independent sources and "
                     f"{gates[failed].detail['missing_platforms']} more platforms"])
        return ("NO-GO", None, conf, gates, None, [])

    abstained = sum(s.abstained for s in scores)
    if abstained > config.abstain.max_abstained:
        return ("INSUFFICIENT_EVIDENCE", None, conf, gates, None,
                ["two or more dimensions abstained; gather cited scores"])
    if conf < config.thresholds.min_confidence:
        return ("INSUFFICIENT_EVIDENCE", None, conf, gates, None,
                ["Overall confidence below minimum; gather stronger evidence"])

    total = weighted_score(scores, weights)
    by_dimension = {s.dimension: s for s in scores}
    floor_breaches = [dimension for dimension in DIMENSIONS[:5]
                      if not by_dimension[dimension].abstained
                      and by_dimension[dimension].score < config.thresholds.floor]
    if total >= config.thresholds.T_go and not floor_breaches:
        return ("GO", total, conf, gates, None, [])
    if total >= config.thresholds.T_no:
        weakest = floor_breaches[0] if floor_breaches else min(
            (s for s in scores if not s.abstained), key=lambda s: s.score).dimension
        return ("PIVOT", total, conf, gates, weakest, [])
    return ("NO-GO", total, conf, gates, None, [])


def sensitivity(request: EvaluationInput, config: VerdictConfig,
                scores: list[DimensionScore] | None = None) -> Sensitivity:
    scores = scores or apply_challenge(request.scores, request.accepted_objections, config)
    weights = config.weights[request.profile.goal]
    original = _base_decision(request, config, scores, weights)[0]
    flips: list[Flip] = []
    run = 0
    for dimension in DIMENSIONS:
        for direction in (-1, 1):
            run += 1
            old = weights[dimension]
            new = old * (1 + direction * config.sensitivity.weight_delta)
            changed = {name: (new if name == dimension else weight * (100 - new) / (100 - old))
                       for name, weight in weights.items()}
            verdict = _base_decision(request, config, scores, changed)[0]
            if verdict != original:
                percent = direction * config.sensitivity.weight_delta * 100
                flips.append(Flip(run=run, change=f"{dimension} weight {percent:+g}%",
                                  verdict=verdict))
    least = min((s for s in scores if not s.abstained), key=lambda s: s.confidence)
    for direction in (-1, 1):
        run += 1
        changed_scores = [s.model_copy(update={"score": min(5, max(0, s.score +
                          direction * config.sensitivity.score_delta))}) if s.dimension == least.dimension
                          else s for s in scores]
        verdict = _base_decision(request, config, changed_scores, weights)[0]
        if verdict != original:
            delta = direction * config.sensitivity.score_delta
            flips.append(Flip(run=run, change=f"{least.dimension} score {delta:+g}",
                              verdict=verdict))
    return Sensitivity(runs=run, flipped=len(flips), flips=flips)


def what_would_make_go(request: EvaluationInput, config: VerdictConfig,
                       scores: list[DimensionScore] | None = None) -> WhatIf | None:
    scores = scores or apply_challenge(request.scores, request.accepted_objections, config)
    weights = config.weights[request.profile.goal]
    current = _base_decision(request, config, scores, weights)
    if current[0] == "GO" and not sensitivity(request, config, scores).flipped:
        return None
    failed = next((name for name, gate in current[3].items() if gate.status == "fail"), None)
    if failed == "feasibility":
        changed_request = request.model_copy(update={"estimated_build_hours":
                                             float(available_hours(request.profile))})
        outcome, total, *_ = _base_decision(changed_request, config, scores, weights)
        if outcome == "GO" and not sensitivity(changed_request, config, scores).flipped:
            assert total is not None
            return WhatIf(change=f"Reduce estimated effort by {current[3]['feasibility'].detail['hours_gap']} hours",
                          new_score=total, new_verdict="GO")
        return None
    if failed:
        return None
    step = config.whatif.step
    candidates: list[tuple[float, int, WhatIf]] = []
    for index, score in enumerate(scores):
        if score.abstained:
            continue
        target = (int(score.score / step) + 1) * step
        while target <= 5 + 1e-9:
            changed_scores = [item.model_copy(update={"score": min(5, target)})
                              if item.dimension == score.dimension else item for item in scores]
            outcome, total, *_ = _base_decision(request, config, changed_scores, weights)
            if outcome == "GO" and not sensitivity(request, config, changed_scores).flipped:
                assert total is not None
                candidates.append((target - score.score, index,
                                   WhatIf(change=f"Raise {score.dimension} by +{target - score.score:g} to {target:g}",
                                          new_score=total, new_verdict="GO")))
                break
            target += step
    return min(candidates, key=lambda item: (item[0], item[1]))[2] if candidates else None


def decide(request: EvaluationInput, config: VerdictConfig) -> Verdict:
    scores = apply_challenge(request.scores, request.accepted_objections, config)
    weights = config.weights[request.profile.goal]
    outcome, total, conf, gates, weakest, missing = _base_decision(request, config, scores, weights)
    report = sensitivity(request, config, scores) if outcome == "GO" else Sensitivity(
        runs=0, flipped=0, flips=[])
    candidate = what_would_make_go(request, config, scores)
    rubric_versions = sorted({s.rubric_version for s in scores})
    return Verdict(
        idea_id=request.idea_id, version=request.version, run_id=request.run_id,
        verdict=outcome, stability="BORDERLINE" if report.flipped else "STABLE",
        score=total, confidence=conf, gates=gates, weights=weights,
        thresholds=config.thresholds, scores=scores, weakest_dimension=weakest,
        what_would_make_go=[candidate] if candidate else [], sensitivity=report,
        versions=Versions(engine="v1", rubrics=",".join(rubric_versions),
                          profile_weights=config.version, config=config.version),
        missing_evidence=missing,
    )
