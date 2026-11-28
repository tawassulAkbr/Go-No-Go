import argparse
from uuid import uuid4
from . import Plan, collect

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--query", default="")
parser.add_argument("--limit", type=int, default=500)
parser.add_argument("--run-id", default=str(uuid4()))
print(collect(Plan(**vars(parser.parse_args()))))
