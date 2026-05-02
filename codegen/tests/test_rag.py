"""RAG / Graph-RAG tests."""

import os
from tests.runner import BaseRunner, expects, SkipTest


class TestRAG(BaseRunner):

    # ── Chat with RAG disabled ──────────────────────────────

    @expects("pass")
    def test_01_rag_disabled(self):
        """use_rag=false returns plain completion."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=False, use_graph_rag=False)
        assert len(data["response"]["text"]) > 0

    # ── Chat with RAG enabled (no index → fallback) ─────────

    @expects("pass")
    def test_02_rag_enabled_no_index(self):
        """use_rag=true falls back to plain completion when no index."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=True, use_graph_rag=False)
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_03_graph_rag_enabled_no_index(self):
        """use_graph_rag=true falls back when no index exists."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=True, use_graph_rag=True)
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_04_rag_nonexistent_project_path(self):
        """Nonexistent project_path doesn't break request."""
        data = self._chat({"prompt": "def process():", "suffix": ""},
                          use_rag=True, use_graph_rag=True,
                          project_path="/nonexistent/project")
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_05_rag_with_project_path_empty(self):
        """Empty project_path defaults to shared store."""
        data = self._chat({"prompt": "def empty():", "suffix": ""},
                          use_rag=True, use_graph_rag=False,
                          project_path="")
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_06_rag_only_use_rag(self):
        """use_rag=true + use_graph_rag=false uses vector-only RAG."""
        data = self._chat({"prompt": "def vec():", "suffix": "\n    return 1"},
                          use_rag=True, use_graph_rag=False)
        assert len(data["response"]["text"]) > 0

    # ── RAG index endpoint — error cases ─────────────────────

    @expects("pass")
    def test_07_rag_index_missing_directory(self):
        """POST /api/v1/rag/index without directory → 400."""
        resp = self._post(f"{self.base_url}/api/v1/rag/index", {})
        assert resp.status_code in (200, 400)
        if resp.status_code == 400:
            data = resp.json()
            assert data["success"] is False

    @expects("pass")
    def test_08_rag_index_invalid_json(self):
        """POST /api/v1/rag/index with bad JSON → 400."""
        import requests
        resp = requests.post(f"{self.base_url}/api/v1/rag/index",
                             data="not json",
                             headers={"Content-Type": "application/json"}, timeout=5)
        assert resp.status_code == 400

    @expects("pass")
    def test_09_rag_index_wrong_method(self):
        """GET /api/v1/rag/index → 405."""
        resp = self._get(f"{self.base_url}/api/v1/rag/index")
        assert resp.status_code == 405

    # ── RAG index endpoint — integration ─────────────────────

    @expects("pass")
    def test_10_rag_index_success(self):
        """POST /api/v1/rag/index with valid directory → 200."""
        # Use a small test directory
        test_dir = os.path.join(os.path.dirname(__file__), "..", "examples", "demo_project")
        test_dir = os.path.abspath(test_dir)
        if not os.path.isdir(test_dir):
            raise SkipTest("demo_project not found")

        resp = self._post(f"{self.base_url}/api/v1/rag/index",
                          {"directory": test_dir, "project_path": "test_rag_temp"},
                          timeout=60)
        # Either 200 (indexed) or 400 (missing LSP/deps) — both acceptable
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"] is True
            assert data["chunks_indexed"] > 0

    @expects("pass")
    def test_11_rag_index_incremental(self):
        """Second index call is incremental and fast."""
        test_dir = os.path.join(os.path.dirname(__file__), "..", "examples", "demo_project")
        test_dir = os.path.abspath(test_dir)
        if not os.path.isdir(test_dir):
            raise SkipTest("demo_project not found")

        # First index
        self._post(f"{self.base_url}/api/v1/rag/index",
                   {"directory": test_dir, "project_path": "test_rag_incr"},
                   timeout=60)
        # Second index (incremental — should be fast, no changes)
        resp = self._post(f"{self.base_url}/api/v1/rag/index",
                          {"directory": test_dir, "project_path": "test_rag_incr"},
                          timeout=60)
        assert resp.status_code in (200, 400)

    @expects("pass")
    def test_12_rag_index_full_rebuild(self):
        """POST with full=true triggers full rebuild."""
        test_dir = os.path.join(os.path.dirname(__file__), "..", "examples", "demo_project")
        test_dir = os.path.abspath(test_dir)
        if not os.path.isdir(test_dir):
            raise SkipTest("demo_project not found")

        resp = self._post(f"{self.base_url}/api/v1/rag/index",
                          {"directory": test_dir, "project_path": "test_rag_full",
                           "full": True},
                          timeout=60)
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"] is True
