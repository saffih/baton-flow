import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flow_runtime.cli import main


@contextlib.contextmanager
def temp_db_env():
    """Point FLOW_DB_PATH at a throwaway file-backed DB for the duration."""
    with tempfile.TemporaryDirectory() as d:
        prev = os.environ.get("FLOW_DB_PATH")
        os.environ["FLOW_DB_PATH"] = os.path.join(d, "cli-test.db")
        try:
            yield
        finally:
            if prev is None:
                os.environ.pop("FLOW_DB_PATH", None)
            else:
                os.environ["FLOW_DB_PATH"] = prev


def run(argv):
    """Run the CLI, capturing stdout. Returns (exit_code, stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class CliTaskFlowTests(unittest.TestCase):
    def test_full_task_lifecycle(self):
        with temp_db_env():
            code, out = run(["add", "task", "build feature", "--priority", "high"])
            self.assertEqual(code, 0)
            self.assertIn("Created task 1", out)

            code, out = run(["list", "tasks"])
            self.assertIn("build feature", out)

            code, out = run(["mark", "task", "done", "1", "--outcome", "done it"])
            self.assertEqual(code, 0)

            code, out = run(["--json", "get", "task", "1"])
            data = json.loads(out)
            self.assertEqual(data["status"], "done")
            self.assertEqual(data["outcome"], "done it")

    def test_json_list(self):
        with temp_db_env():
            run(["add", "task", "a"])
            run(["add", "task", "b"])
            code, out = run(["--json", "list", "tasks"])
            data = json.loads(out)
            self.assertEqual(len(data), 2)

    def test_reserve_release_via_cli(self):
        with temp_db_env():
            run(["add", "task", "x"])
            code, _ = run(["reserve", "task", "1", "--session", "sessA"])
            self.assertEqual(code, 0)
            code, _ = run(["reserve", "task", "1", "--session", "sessB"])
            self.assertEqual(code, 1)  # already taken
            code, _ = run(["release", "task", "1", "--session", "sessA"])
            self.assertEqual(code, 0)

    def test_status_command(self):
        with temp_db_env():
            run(["add", "task", "a"])
            d, _ = run(["add", "task", "b"])
            run(["mark", "task", "done", "2", "--outcome", "y"])
            code, out = run(["--json", "status"])
            data = json.loads(out)
            self.assertEqual(data["pending"], 1)
            self.assertEqual(data["done"], 1)
            self.assertEqual(data["total_active"], 2)

    def test_health_command(self):
        with temp_db_env():
            code, out = run(["--json", "health", "check"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "healthy")

    def test_hint_and_report(self):
        with temp_db_env():
            code, _ = run(["add", "hint", "always test", "--priority", "high"])
            self.assertEqual(code, 0)
            code, out = run(["--json", "list", "hints"])
            self.assertEqual(len(json.loads(out)), 1)

            code, _ = run(["add", "report", "WIP", "--title", "WIP report", "--is_wip", "1"])
            self.assertEqual(code, 0)
            code, _ = run(["append", "report", "1", "--content", " progress"])
            self.assertEqual(code, 0)

    def test_get_missing_returns_1(self):
        with temp_db_env():
            code, _ = run(["get", "task", "999"])
            self.assertEqual(code, 1)

    def test_bad_column_returns_2(self):
        with temp_db_env():
            code, _ = run(["add", "task", "x", "--bogus", "v"])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
