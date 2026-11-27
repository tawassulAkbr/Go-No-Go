from pathlib import Path

import yaml

from services.verdict.src.engine import DIMENSIONS


def test_each_dimension_has_versioned_complete_rubric():
    root = Path(__file__).resolve().parents[3] / "rubrics"
    for dimension in DIMENSIONS:
        path = root / f"{dimension}@v1.yaml"
        rubric = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert rubric["dimension"] == dimension
        assert rubric["version"] == "v1"
        assert set(rubric["anchors"]) == set(range(6))
        assert set(rubric["examples"]) == set(range(6))
        assert rubric["features"]
        assert rubric["output_schema"] == "DimensionScore.json"
