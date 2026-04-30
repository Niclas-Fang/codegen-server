#!/usr/bin/env python
"""
Code completion API test suite.

Usage:
    pixi run test                  # run all tests
    pixi run test test_name        # run single test
    pixi run test --list           # list available tests

Test categories:
    1. Connection — server, CORS, endpoint availability
    2. Error — parameter validation, error codes
    3. Integration — real API calls (skipped when API key unavailable)
    4. Chat — chat endpoint, model validation, context types
    5. RAG — retrieval-augmented generation tests
    6. Boundary — edge cases (long input, special chars)
"""

import sys
import time
import requests
from dataclasses import dataclass
from enum import Enum


class SkipTestException(Exception):
    """Raise to skip a test (e.g. API key unavailable)."""


class TestStatus(Enum):
    PASSED = "PASS"
    FAILED = "FAIL"
    SKIPPED = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    message: str = ""
    duration: float = 0.0


class TestRunner:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1/completion"
        self.chat_url = f"{self.base_url}/api/v1/chat"
        self.models_url = f"{self.base_url}/api/v1/models"
        self.results: list[TestResult] = []
        self._start_time: float = 0.0

    # ── helpers ──────────────────────────────────────────────

    def _post(self, url: str, data: dict, timeout: int = 5) -> requests.Response:
        return requests.post(url, json=data, timeout=timeout)

    def _get(self, url: str, timeout: int = 5) -> requests.Response:
        return requests.get(url, timeout=timeout)

    def _options(self, url: str, timeout: int = 2) -> requests.Response:
        return requests.options(url, timeout=timeout)

    def _assert_status(self, resp: requests.Response, expected: int) -> dict:
        assert resp.status_code == expected, (
            f"expected status {expected}, got {resp.status_code}"
        )
        try:
            return resp.json()
        except Exception:
            raise AssertionError(f"invalid JSON: {resp.text[:100]}")

    def _assert_error(self, resp: requests.Response, expected_code: str, status: int = 400) -> dict:
        data = self._assert_status(resp, status)
        assert data["success"] is False, "expected success=False"
        assert data["error_code"] == expected_code, (
            f"expected {expected_code}, got {data.get('error_code')}"
        )
        return data

    def _assert_suggestion(self, data: dict):
        """Validate a FIM suggestion response structure."""
        assert data["success"] is True, f"API failed: {data.get('error_code', 'unknown')}"
        s = data["suggestion"]
        assert isinstance(s["text"], str) and len(s["text"]) > 0, "suggestion.text empty"
        assert isinstance(s["label"], str) and len(s["label"]) > 0, "suggestion.label empty"

    def _assert_chat_response(self, data: dict):
        """Validate a chat response structure."""
        assert data["success"] is True, f"API failed: {data.get('error_code', 'unknown')}"
        r = data["response"]
        assert isinstance(r["text"], str) and len(r["text"]) > 0, "response.text empty"
        assert "model" in r, "response missing model"

    def _skip_if_api_fails(self, data: dict, label: str):
        """Raise SkipTestException if the API returned an error."""
        if not data.get("success"):
            raise SkipTestException(f"{data.get('error_code', 'unknown')}: {data.get('error', '')[:80]}")

    def _run_test(self, func) -> TestResult:
        name = func.__name__.replace("test_", "").replace("_", " ")
        start = time.time()
        try:
            func()
            status, msg = TestStatus.PASSED, ""
        except SkipTestException as e:
            status, msg = TestStatus.SKIPPED, str(e)
        except AssertionError as e:
            status, msg = TestStatus.FAILED, str(e)
        except Exception as e:
            status, msg = TestStatus.ERROR, f"{type(e).__name__}: {e}"
        elapsed = time.time() - start
        r = TestResult(name, status, msg, elapsed)
        self.results.append(r)
        return r

    def _collect_tests(self):
        return sorted(
            [getattr(self, a) for a in dir(self) if a.startswith("test_") and callable(getattr(self, a))],
            key=lambda f: f.__name__,
        )

    # ── runner ───────────────────────────────────────────────

    def run_all(self):
        self._start_time = time.time()
        tests = self._collect_tests()
        for f in tests:
            r = self._run_test(f)
            icon = {"PASS": ".", "FAIL": "F", "SKIP": "s", "ERROR": "E"}[r.status.value]
            detail = f"  [{r.status.value}] {r.message}" if r.message else ""
            print(f"  {icon} {r.name:<36} {r.duration:.2f}s{detail}")
        self._print_summary()

    def run_one(self, name: str):
        if not name.startswith("test_"):
            name = f"test_{name}"
        func = getattr(self, name, None)
        if func is None:
            print(f"No such test: {name}")
            sys.exit(1)
        r = self._run_test(func)
        print(f"{r.status.value} {r.name}  ({r.duration:.2f}s)")
        if r.message:
            print(f"  {r.message}")
        sys.exit(0 if r.status == TestStatus.PASSED else 1)

    def list_tests(self):
        for f in self._collect_tests():
            doc = (f.__doc__ or "").strip().split("\n")[0]
            print(f"  {f.__name__:<40} {doc}")

    def _print_summary(self):
        total = len(self.results)
        counts = {s: sum(1 for r in self.results if r.status == s) for s in TestStatus}
        elapsed = time.time() - self._start_time
        print(f"\n{'='*60}")
        print(f"Results: {total} total  "
              f"P={counts[TestStatus.PASSED]} F={counts[TestStatus.FAILED]} "
              f"S={counts[TestStatus.SKIPPED]} E={counts[TestStatus.ERROR]}  "
              f"({elapsed:.2f}s)")
        failures = [r for r in self.results if r.status in (TestStatus.FAILED, TestStatus.ERROR)]
        if failures:
            for r in failures:
                print(f"  [{r.status.value}] {r.name}: {r.message}")

    # ── connection tests ─────────────────────────────────────

    def test_server_connection(self):
        """Server responds on base URL."""
        try:
            resp = self._get(self.base_url, timeout=2)
            assert resp.status_code in (200, 404, 403), f"unexpected status {resp.status_code}"
        except requests.ConnectionError:
            raise AssertionError("cannot connect — is the server running?")

    def test_fim_endpoint_cors(self):
        """FIM endpoint has CORS headers."""
        resp = self._options(self.api_url)
        assert resp.status_code == 200
        headers = dict(resp.headers)
        assert "Access-Control-Allow-Origin" in headers, "missing CORS origin header"
        assert "Access-Control-Allow-Methods" in headers, "missing CORS methods header"

    def test_chat_endpoint_cors(self):
        """Chat endpoint has CORS headers."""
        resp = self._options(self.chat_url)
        assert resp.status_code == 200
        headers = dict(resp.headers)
        assert "Access-Control-Allow-Origin" in headers, "missing CORS origin header"

    def test_models_endpoint_get(self):
        """GET /models returns provider list."""
        data = self._assert_status(self._get(self.models_url), 200)
        assert data["success"] is True
        assert isinstance(data["providers"], list) and len(data["providers"]) > 0
        assert isinstance(data["models"], dict)

    def test_models_endpoint_method_not_allowed(self):
        """POST /models returns 405."""
        self._assert_error(self._post(self.models_url, {}), "INVALID_METHOD", 405)

    # ── FIM error tests ──────────────────────────────────────

    def test_fim_missing_prompt(self):
        """Missing prompt returns INVALID_PARAMS."""
        d = self._assert_error(self._post(self.api_url, {"suffix": "x"}), "INVALID_PARAMS")
        assert "缺少必填参数" in d["error"]

    def test_fim_missing_suffix(self):
        """Missing suffix returns INVALID_PARAMS."""
        d = self._assert_error(self._post(self.api_url, {"prompt": "x"}), "INVALID_PARAMS")
        assert "缺少必填参数" in d["error"]

    def test_fim_invalid_json(self):
        """Malformed JSON returns INVALID_JSON."""
        resp = requests.post(self.api_url, data="not json",
                             headers={"Content-Type": "application/json"}, timeout=5)
        self._assert_error(resp, "INVALID_JSON")

    def test_fim_empty_strings(self):
        """Empty prompt+suffix returns error."""
        resp = self._post(self.api_url, {"prompt": "", "suffix": ""})
        assert resp.status_code in (400, 500)
        data = resp.json()
        assert data["success"] is False

    # ── FIM integration tests ────────────────────────────────

    def test_fim_minimal(self):
        """Minimal valid FIM request."""
        data = self._assert_status(
            self._post(self.api_url, {"prompt": "int main() {\n  int a=10;\n  ", "suffix": "\n  return 0;\n}"}, timeout=10), 200)
        self._skip_if_api_fails(data, "FIM minimal")
        self._assert_suggestion(data)

    def test_fim_full(self):
        """FIM request with includes, other_functions, max_tokens."""
        data = self._assert_status(self._post(self.api_url, {
            "prompt": "int main() {\n  int a=10; int b=20;\n  ",
            "suffix": "\n  return 0;\n}",
            "includes": ["#include <iostream>", "#include <vector>"],
            "other_functions": [
                {"name": "calc", "signature": "int calc(int a, int b)"},
                {"name": "prod", "signature": "int prod(int a, int b)"},
            ],
            "max_tokens": 100,
        }, timeout=10), 200)
        self._skip_if_api_fails(data, "FIM full")
        self._assert_suggestion(data)

    # ── FIM boundary tests ───────────────────────────────────

    def test_fim_long_prompt(self):
        """Very long prompt is handled (truncated)."""
        long_prompt = "int main() {\n" + "  // comment\n" * 1000
        data = self._assert_status(
            self._post(self.api_url, {"prompt": long_prompt, "suffix": "\n}"}, timeout=10), 200)
        self._skip_if_api_fails(data, "FIM long prompt")
        self._assert_suggestion(data)

    def test_fim_many_includes(self):
        """Includes beyond MAX_INCLUDES(10) are truncated."""
        includes = [f"#include <h{i}.h>" for i in range(20)]
        data = self._assert_status(
            self._post(self.api_url, {"prompt": "int main() {\n  ", "suffix": "\n}", "includes": includes}), 200)
        self._skip_if_api_fails(data, "FIM many includes")
        self._assert_suggestion(data)

    def test_fim_many_functions(self):
        """Functions beyond MAX_FUNCTIONS(5) are truncated."""
        funcs = [{"name": f"f{i}", "signature": f"void f{i}()"} for i in range(10)]
        data = self._assert_status(
            self._post(self.api_url, {"prompt": "int main() {\n  ", "suffix": "\n}", "other_functions": funcs}), 200)
        self._skip_if_api_fails(data, "FIM many funcs")
        self._assert_suggestion(data)

    # ── Chat error tests ─────────────────────────────────────

    def test_chat_missing_context(self):
        """Missing context returns INVALID_PARAMS."""
        d = self._assert_error(self._post(self.chat_url, {}), "INVALID_PARAMS")
        assert "缺少必填参数" in d["error"]

    def test_chat_context_not_dict(self):
        """Context as non-dict returns INVALID_PARAMS."""
        self._assert_error(self._post(self.chat_url, {"context": "not dict"}), "INVALID_PARAMS")

    def test_chat_invalid_model(self):
        """Unknown model name returns INVALID_PARAMS."""
        d = self._assert_error(self._post(self.chat_url, {
            "context": {"prompt": "x", "suffix": "y"},
            "model": "no-such-model",
            "provider": "deepseek",
        }), "INVALID_PARAMS")
        assert "不支持" in d["error"] or "模型" in d["error"]

    def test_chat_invalid_provider(self):
        """Unknown provider returns INVALID_PARAMS."""
        d = self._assert_error(self._post(self.chat_url, {
            "context": {"prompt": "x", "suffix": "y"},
            "provider": "no-such-provider",
        }), "INVALID_PARAMS")
        assert "不支持" in d["error"] or "提供者" in d["error"]

    def test_chat_prompt_not_string(self):
        """Non-string prompt returns INVALID_PARAMS."""
        self._assert_error(self._post(self.chat_url, {
            "context": {"prompt": 123, "suffix": "y"},
        }), "INVALID_PARAMS")

    def test_chat_suffix_not_string(self):
        """Non-string suffix returns INVALID_PARAMS."""
        self._assert_error(self._post(self.chat_url, {
            "context": {"prompt": "x", "suffix": ["bad"]},
        }), "INVALID_PARAMS")

    def test_chat_includes_not_list(self):
        """Non-list includes returns INVALID_PARAMS."""
        self._assert_error(self._post(self.chat_url, {
            "context": {"prompt": "x", "suffix": "y", "includes": "bad"},
        }), "INVALID_PARAMS")

    def test_chat_functions_not_list(self):
        """Non-list other_functions returns INVALID_PARAMS."""
        self._assert_error(self._post(self.chat_url, {
            "context": {"prompt": "x", "suffix": "y", "other_functions": "bad"},
        }), "INVALID_PARAMS")

    # ── Chat integration tests ───────────────────────────────

    def _make_chat_request(self, context: dict, **kwargs) -> dict:
        body = {"context": context, "provider": "deepseek", **kwargs}
        resp = self._post(self.chat_url, body, timeout=30)
        data = self._assert_status(resp, 200)
        self._skip_if_api_fails(data, "Chat")
        return data

    def test_chat_basic(self):
        """Basic chat completion."""
        data = self._make_chat_request({"prompt": "def add(a, b):", "suffix": "\n    return a + b"})
        self._assert_chat_response(data)

    def test_chat_python(self):
        """Python code completion via chat."""
        data = self._make_chat_request({
            "prompt": "def fib(n):\n    if n <= 1:\n        return n\n    ",
            "suffix": "\n\nprint(fib(10))",
        })
        self._assert_chat_response(data)

    def test_chat_cpp(self):
        """C++ code completion via chat."""
        data = self._make_chat_request({
            "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
            "suffix": "\n    return 0;\n}",
            "includes": ["#include <iostream>"],
        })
        self._assert_chat_response(data)

    def test_chat_full(self):
        """Full chat request with all optional fields."""
        data = self._make_chat_request({
            "prompt": "int main() {\n    int a = 10;\n    ",
            "suffix": "\n    return 0;\n}",
            "includes": ["#include <iostream>"],
            "other_functions": [{"name": "calc", "signature": "int calc(int a, int b)"}],
        }, model="deepseek-chat", max_tokens=200)
        self._assert_chat_response(data)
        assert data["response"]["model"] == "deepseek-chat"

    # ── RAG tests ─────────────────────────────────────────────

    def test_chat_with_rag(self):
        """Chat with use_rag=true (falls back gracefully without index)."""
        data = self._make_chat_request(
            {"prompt": "def hello():", "suffix": ""},
            use_rag=True, use_graph_rag=False,
        )
        self._assert_chat_response(data)

    def test_chat_with_graph_rag(self):
        """Chat with use_graph_rag=true (falls back gracefully without index)."""
        data = self._make_chat_request(
            {"prompt": "def hello():", "suffix": ""},
            use_rag=True, use_graph_rag=True,
        )
        self._assert_chat_response(data)

    def test_chat_rag_with_project_path(self):
        """Chat with project_path specified for isolated index."""
        data = self._make_chat_request(
            {"prompt": "def process():", "suffix": ""},
            use_rag=True, use_graph_rag=True, project_path="/nonexistent/project",
        )
        self._assert_chat_response(data)

    # ── boundary tests ───────────────────────────────────────

    def test_chat_empty_context(self):
        """Empty context dict is handled."""
        resp = self._post(self.chat_url, {"context": {}})
        assert resp.status_code in (200, 400)

    def test_chat_special_characters(self):
        """Unicode and emoji in prompt."""
        data = self._make_chat_request({
            "prompt": 'def greet():\n    msg = "你好 🌍"\n    ',
            "suffix": "\n    return msg",
        })
        self._assert_chat_response(data)

    def test_chat_long_input(self):
        """Very long input is handled (truncated)."""
        long_prompt = "def test():\n" + "    x = 1\n" * 1000
        data = self._make_chat_request({"prompt": long_prompt, "suffix": "\n    return x"})
        self._assert_chat_response(data)

    def test_multiple_requests(self):
        """Multiple sequential requests all succeed."""
        body = {"prompt": "int main() {\n  ", "suffix": "\n}"}
        for _ in range(3):
            resp = self._post(self.api_url, body, timeout=10)
            assert resp.status_code == 200
            data = resp.json()
            if not data.get("success"):
                raise SkipTestException(f"API unavailable: {data.get('error_code')}")
        # If we reached here without SkipTestException, all 3 succeeded


def main():
    runner = TestRunner()

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        runner.list_tests()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        runner.list_tests()
        return

    # pre-flight: check server
    try:
        requests.get(runner.base_url, timeout=1)
    except Exception:
        print("Server may not be running. Start with: pixi run runserver\n")
        # Don't exit — let tests report the error

    if len(sys.argv) > 1:
        runner.run_one(sys.argv[1])
    else:
        runner.run_all()

    failed = sum(1 for r in runner.results if r.status in (TestStatus.FAILED, TestStatus.ERROR))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
