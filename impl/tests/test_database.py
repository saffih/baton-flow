import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flow_runtime.database import Database, DatabaseError


class DatabaseTaskTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def test_add_and_get_task(self):
        tid = self.db.add_task("do the thing", priority="high", title="T")
        task = self.db.get_task(tid)
        self.assertEqual(task["content"], "do the thing")
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["priority"], "high")
        self.assertTrue(task["unique_id"])

    def test_update_task(self):
        tid = self.db.add_task("x")
        self.db.update_task(tid, status="in-progress", assignee="alice")
        task = self.db.get_task(tid)
        self.assertEqual(task["status"], "in-progress")
        self.assertEqual(task["assignee"], "alice")

    def test_mark_done(self):
        tid = self.db.add_task("x")
        self.db.mark_task_done(tid, "finished")
        task = self.db.get_task(tid)
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["outcome"], "finished")
        self.assertIsNotNone(task["done_at"])

    def test_mark_done_threshold(self):
        tid = self.db.add_task("x")
        with self.assertRaises(DatabaseError):
            self.db.mark_task_done(tid, "short", outcome_length_threshold=100)

    def test_mark_acknowledged(self):
        tid = self.db.add_task("x")
        self.db.mark_task_acknowledged(tid, "wontfix")
        self.assertEqual(self.db.get_task(tid)["status"], "ack")

    def test_list_tasks_filters(self):
        self.db.add_task("a", priority="high")
        self.db.add_task("b", priority="low")
        done = self.db.add_task("c")
        self.db.mark_task_done(done, "done")
        self.assertEqual(len(self.db.list_tasks()), 3)  # all non-archived regardless of status
        self.assertEqual(len(self.db.list_tasks(status="done")), 1)
        self.assertEqual(len(self.db.list_tasks(priority="high")), 1)
        self.assertEqual(len(self.db.list_tasks(limit=1)), 1)

    def test_unknown_column_rejected(self):
        with self.assertRaises(DatabaseError):
            self.db.add_task("x", nonexistent_col="boom")

    def test_metadata_dict_encoded(self):
        tid = self.db.add_task("x", metadata={"k": "v"})
        self.assertEqual(self.db.get_task(tid)["metadata"], '{"k": "v"}')


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def test_reserve_is_atomic(self):
        tid = self.db.add_task("x")
        self.assertTrue(self.db.reserve_task(tid, "sessA"))
        self.assertFalse(self.db.reserve_task(tid, "sessB"))
        self.assertTrue(self.db.is_task_taken(tid))

    def test_release_only_by_holder(self):
        tid = self.db.add_task("x")
        self.db.reserve_task(tid, "sessA")
        self.assertFalse(self.db.release_task(tid, "sessB"))
        self.assertTrue(self.db.release_task(tid, "sessA"))
        self.assertFalse(self.db.is_task_taken(tid))
        # now re-reservable
        self.assertTrue(self.db.reserve_task(tid, "sessB"))


class HintReportTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def test_hint_crud(self):
        hid = self.db.add_hint("test always", priority="high")
        self.assertEqual(self.db.get_hint(hid)["content"], "test always")
        self.db.update_hint(hid, status="disabled")
        self.assertEqual(self.db.get_hint(hid)["status"], "disabled")
        self.assertEqual(len(self.db.list_hints(status="disabled")), 1)

    def test_report_append(self):
        rid = self.db.add_report({"title": "WIP", "content": "start", "is_wip": 1, "task_id": 1})
        self.assertTrue(self.db.append_to_report(rid, " more"))
        self.assertEqual(self.db.get_report(rid)["content"], "start more")

    def test_report_requires_title(self):
        with self.assertRaises(DatabaseError):
            self.db.add_report({"content": "no title"})

    def test_wip_lookup_by_task(self):
        self.db.add_report({"title": "W", "is_wip": 1, "task_id": 42})
        self.assertIsNotNone(self.db.get_wip_report_by_task_id(42))
        self.assertIsNone(self.db.get_wip_report_by_task_id(999))


class UiAndHealthTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def test_ui_counts(self):
        self.db.add_task("a")
        self.db.add_task("b")
        d = self.db.add_task("c")
        self.db.mark_task_done(d, "x")
        self.assertEqual(self.db.get_task_count_for_ui(status="pending"), 2)
        self.assertEqual(self.db.get_task_count_for_ui(status="done"), 1)
        self.assertEqual(self.db.get_task_count_for_ui(), 3)
        self.assertEqual(len(self.db.get_tasks_for_ui(status="pending")), 2)

    def test_health(self):
        h = self.db.health_check()
        self.assertEqual(h["status"], "healthy")
        self.assertEqual(h["tables_missing"], [])

    def test_config_roundtrip(self):
        self.db.set_config("theme", "dark")
        self.assertEqual(self.db.get_config("theme"), "dark")
        self.db.set_config("theme", "light")
        self.assertEqual(self.db.get_config("theme"), "light")

    def test_session_register_and_list(self):
        self.db.register_session("s1", "alpha", pid=123)
        self.assertEqual(len(self.db.list_sessions("active")), 1)
        self.assertEqual(self.db.get_session("alpha")["pid"], 123)


if __name__ == "__main__":
    unittest.main()
