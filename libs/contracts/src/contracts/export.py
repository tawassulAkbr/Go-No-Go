"""Export the public wire schemas to the supplied directory."""

import argparse
import json
from pathlib import Path

from . import Card, DimensionScore, Evidence, Profile, Trace, Verdict


def export(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for model in (Profile, Card, Evidence, DimensionScore, Verdict, Trace):
        path = directory / f"{model.__name__}.json"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(model.model_json_schema(), handle, indent=2)
            handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    export(parser.parse_args().directory)
