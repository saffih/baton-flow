import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flow_runtime.database import Database
from flow_runtime.server import FlowAPI


class FlowAPITests(unittest.TestCase):
    def setUp(self):
        self.api = FlowAPI(Database(":memory:"))

    def dispatch(self, method, path, query=None, body=None):
        return self.api.dispatch(method, path, query or {}, body or {})

    def test_health(self):
        status, payload = self.dispatch("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "healthy")

    def test_create_and_get_task(self):
        status, payload = self.dispatch("POST", "/api/tasks", body={"content": "hello", "priority": "high"})
        self.assertEqual(status, 201)
        tid = payload["id"]
        status, task = self.dispatch("GET", f"/api/tasks/{tid}")
        self.assertEqual(status, 200)
        self.assertEqual(task["content"], "hello")

    def test_create_task_requires_content(self):
        status, payload = self.dispatch("POST", "/api/tasks", body={})
        self.assertEqual(status, 400)

    def test_list_tasks(self):
        self.dispatch("POST", "/api/tasks", body={"content": "a"})
        self.dispatch("POST", "/api/tasks", body={"content": "b"})
        status, payload = self.dispatch("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 2)

    def test_list_tasks_status_filter(self):
        self.dispatch("POST", "/api/tasks", body={"content": "a"})
        _, p = self.dispatch("POST", "/api/tasks", body={"content": "b"})
        self.dispatch("POST", f"/api/tasks/{p['id']}/done", body={"outcome": "x"})
        status, payload = self.dispatch("GET", "/api/tasks", query={"status": "done"})
        self.assertEqual(payload["total"], 1)

    def test_update_task(self):
        _, p = self.dispatch("POST", "/api/tasks", body={"content": "a"})
        status, task = self.dispatch("PUT", f"/api/tasks/{p['id']}", body={"status": "in-progress"})
        self.assertEqual(status, 200)
        self.assertEqual(task["status"], "in-progress")

    def test_mark_done(self):
        _, p = self.dispatch("POST", "/api/tasks", body={"content": "a"})
        status, task = self.dispatch("POST", f"/api/tasks/{p['id']}/done", body={"outcome": "shipped"})
        self.assertEqual(status, 200)
        self.assertEqual(task["status"], "done")

    def test_delete_archives(self):
        _, p = self.dispatch("POST", "/api/tasks", body={"content": "a"})
        status, payload = self.dispatch("DELETE", f"/api/tasks/{p['id']}")
        self.assertEqual(status, 200)
        self.assertTrue(payload["deleted"])
        # archived task no longer in default list
        _, listing = self.dispatch("GET", "/api/tasks")
        self.assertEqual(listing["total"], 0)

    def test_get_missing_task_404(self):
        status, _ = self.dispatch("GET", "/api/tasks/999")
        self.assertEqual(status, 404)

    def test_reports(self):
        status, payload = self.dispatch("POST", "/api/reports", body={"title": "W", "report_type": "wip"})
        self.assertEqual(status, 201)
        status, listing = self.dispatch("GET", "/api/reports")
        self.assertEqual(listing["total"], 1)

    def test_metrics(self):
        self.dispatch("POST", "/api/tasks", body={"content": "a"})
        status, payload = self.dispatch("GET", "/api/metrics")
        self.assertEqual(status, 200)
        self.assertEqual(payload["tasks"]["pending"], 1)

    def test_unknown_route_404(self):
        status, _ = self.dispatch("GET", "/api/nonsense")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
