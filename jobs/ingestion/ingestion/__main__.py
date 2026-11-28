import argparse
from pathlib import Path
from .pipeline import SNAPSHOT, ingest

parser = argparse.ArgumentParser()
parser.add_argument("--from-snapshot", nargs="?", type=Path, const=SNAPSHOT)
print(ingest(parser.parse_args().from_snapshot))
