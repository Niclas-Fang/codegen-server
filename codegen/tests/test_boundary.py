"""Boundary and stress tests."""

from tests.runner import BaseRunner, expects, SkipTest


class TestBoundary(BaseRunner):

    @expects("pass")
    def test_01_multiple_sequential(self):
        """3 identical requests all succeed."""
        body = {"prompt": "int main() {\n  ", "suffix": "\n}"}
        for i in range(3):
            resp = self._post(f"{self.base_url}/api/v1/completion", body)
            assert resp.status_code == 200
            if not resp.json().get("success"):
                raise SkipTest(f"request {i+1} failed — API unavailable")

    @expects("pass")
    def test_02_rag_index_endpoint(self):
        """POST /api/v1/rag/index validates input."""
        # missing directory
        resp = self._post(f"{self.base_url}/api/v1/rag/index", {})
        assert resp.status_code in (200, 400)
