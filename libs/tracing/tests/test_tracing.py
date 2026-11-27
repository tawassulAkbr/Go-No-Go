import io
import json
import unittest
from contextlib import redirect_stdout

from tracing import trace_step


class TraceStepTests(unittest.TestCase):
    def test_prints_a_record_under_the_run_id(self):
        output = io.StringIO()
        with redirect_stdout(output):
            with trace_step("run-1", "gateway", "demo"):
                pass
        record = json.loads(output.getvalue())
        self.assertEqual(record["run_id"], "run-1")
        self.assertEqual(record["agent"], "gateway")
        self.assertEqual(record["kind"], "decision")


if __name__ == "__main__":
    unittest.main()
