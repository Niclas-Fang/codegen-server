"""RAG / Graph-RAG tests."""

from tests.runner import BaseRunner, expects, SkipTest


class TestRAG(BaseRunner):

    @expects("pass")
    def test_01_rag_enabled(self):
        """use_rag=true falls back when no index exists."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=True, use_graph_rag=False)
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_02_graph_rag_enabled(self):
        """use_graph_rag=true falls back when no index exists."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=True, use_graph_rag=True)
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_03_rag_project_path_isolation(self):
        """Nonexistent project_path doesn't break request."""
        data = self._chat({"prompt": "def process():", "suffix": ""},
                          use_rag=True, use_graph_rag=True,
                          project_path="/nonexistent/project")
        assert len(data["response"]["text"]) > 0
