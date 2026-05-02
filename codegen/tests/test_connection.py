"""Server connectivity, CORS, and health check tests."""

import requests
from tests.runner import BaseRunner, expects, Outcome, SkipTest


class TestConnection(BaseRunner):
    """Tests that don't require any API keys."""

    @expects("pass")
    def test_01_server_reachable(self):
        """GET / returns HTTP response (200/404 ok)."""
        try:
            resp = self._get(self.base_url, timeout=2)
            assert resp.status_code in (200, 404, 403)
        except requests.ConnectionError:
            raise AssertionError("server not reachable")

    @expects("pass")
    def test_02_fim_cors_headers(self):
        """OPTIONS /api/v1/completion returns CORS headers."""
        resp = self._options(f"{self.base_url}/api/v1/completion")
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    @expects("pass")
    def test_03_chat_cors_headers(self):
        """OPTIONS /api/v1/chat returns CORS headers."""
        resp = self._options(f"{self.base_url}/api/v1/chat")
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers

    @expects("pass")
    def test_04_health_endpoint(self):
        """GET /api/v1/health returns status ok."""
        data = self._assert_ok(self._get(f"{self.base_url}/api/v1/health"))
        assert data["status"] == "ok"
        assert isinstance(data["providers"], dict)

    @expects("pass")
    def test_05_cors_preflight(self):
        """CORS preflight with Origin returns allow-origin header."""
        resp = self._options(f"{self.base_url}/api/v1/completion",
                             headers={"Origin": "http://localhost:3000",
                                      "Access-Control-Request-Method": "POST",
                                      "Access-Control-Request-Headers": "Content-Type"})
        assert resp.status_code == 200
        assert resp.headers.get("Access-Control-Allow-Origin") is not None

    @expects("pass")
    def test_06_cors_on_error_responses(self):
        """Even non-200 responses include CORS headers."""
        resp = self._post(f"{self.base_url}/api/v1/completion",
                          {"prompt": "test", "suffix": "test"})
        assert "access-control-allow-origin" in resp.headers


if __name__ == "__main__":
    t = TestConnection()
    t.run_all()
    sys.exit(0 if not [r for r in t.results if r.actual not in (Outcome.PASS, Outcome.SKIP)] else 1)
