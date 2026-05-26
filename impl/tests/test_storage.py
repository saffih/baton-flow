import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flow_runtime.database import Database
from flow_runtime.storage import Storage, project_all, render_status


class StorageFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.storage = Storage(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_write_read_roundtrip(self):
        path = self.storage.write_file("tasks", 1, "# hello")
        self.assertTrue(os.path.exists(path))
        self.assertEqual(self.storage.read_file("tasks", 1), "# hello")

    def test_file_exists_and_delete(self):
        self.assertFalse(self.storage.file_exists("tasks", 5))
        self.storage.write_file("tasks", 5, "x")
        self.assertTrue(self.storage.file_exists("tasks", 5))
        self.assertTrue(self.storage.delete_file("tasks", 5))
        self.assertFalse(self.storage.file_exists("tasks", 5))

    def test_read_missing_returns_none(self):
        self.assertIsNone(self.storage.read_file("tasks", 999))

    def test_directory_layout(self):
        self.assertTrue(self.storage.get_table_directory("tasks").endswith("tasks"))
        self.assertTrue(self.storage.get_file_path("reports", 3).endswith("reports/3.md"))


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.storage = Storage(self.dir.name)
        self.db = Database(":memory:")

    def tearDown(self):
        self.dir.cleanup()

    def test_project_all_writes_markdown(self):
        t1 = self.db.add_task("task one", title="One", priority="high")
        self.db.add_task("task two")
        self.db.add_report({"title": "WIP", "content": "progress", "report_type": "wip"})

        result = project_all(self.db, self.storage)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["written"], 3)  # 2 tasks + 1 report

        md = self.storage.read_file("tasks", t1)
        self.assertIn("Task 1: One", md)
        self.assertIn("task one", md)
        self.assertTrue(os.path.exists(os.path.join(self.dir.name, "flow-status.md")))

    def test_one_way_projection_overwrites(self):
        tid = self.db.add_task("original")
        project_all(self.db, self.storage)
        # manual edit to markdown
        self.storage.write_file("tasks", tid, "MANUAL EDIT")
        # re-project: database wins, manual edit overwritten
        project_all(self.db, self.storage)
        self.assertIn("original", self.storage.read_file("tasks", tid))
        self.assertNotIn("MANUAL EDIT", self.storage.read_file("tasks", tid))

    def test_status_render(self):
        self.db.add_task("open task")
        status = render_status(self.db)
        self.assertIn("Flow Status", status)
        self.assertIn("open task", status)


if __name__ == "__main__":
    unittest.main()
