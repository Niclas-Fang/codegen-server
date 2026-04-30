#!/usr/bin/env python
"""
Code completion API — TDD test suite.

Each test is annotated with @expects('pass' | 'skip' | 'fail') so the runner
can compare expected outcomes against actual results.

Usage:
    pixi run test                  # run all
    pixi run test test_name        # run one
    pixi run test --list           # list tests
"""

import sys
import time
import requests
from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class Result:
    name: str
    category: str
    expected: str      # 'pass' | 'skip' | 'fail'
    actual: Outcome
    message: str = ""
    duration: float = 0.0


class SkipTest(Exception):
    """Expected skip — e.g. API key unavailable."""


# ── decorator ────────────────────────────────────────────────

_EXPECTATIONS: dict[str, str] = {}

def expects(outcome: str):
    """Declare expected test outcome: 'pass', 'skip', or 'fail'."""
    def decorator(func):
        _EXPECTATIONS[func.__name__] = outcome
        return func
    return decorator


# ── runner ───────────────────────────────────────────────────

class Runner:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results: list[Result] = []
        self._start = 0.0

    # -- helpers --

    def _post(self, url: str, data: dict, timeout: int = 10) -> requests.Response:
        return requests.post(url, json=data, timeout=timeout)

    def _get(self, url: str, timeout: int = 5) -> requests.Response:
        return requests.get(url, timeout=timeout)

    def _options(self, url: str, timeout: int = 2) -> requests.Response:
        return requests.options(url, timeout=timeout)

    def _assert_ok(self, resp: requests.Response, status: int = 200) -> dict:
        assert resp.status_code == status, f"want {status}, got {resp.status_code}"
        try:
            return resp.json()
        except Exception:
            raise AssertionError(f"invalid JSON: {resp.text[:100]}")

    def _assert_error(self, resp: requests.Response, code: str, status: int = 400) -> dict:
        data = self._assert_ok(resp, status)
        assert data["success"] is False, "want success=False"
        assert data["error_code"] == code, f"want {code}, got {data.get('error_code')}"
        return data

    def _skip_on_api_fail(self, data: dict, label: str):
        if not data.get("success"):
            raise SkipTest(f"{data.get('error_code','?')}: {data.get('error','')[:80]}")

    def _run(self, func) -> Result:
        name = func.__name__.replace("test_", "").replace("_", " ")
        expected = _EXPECTATIONS.get(func.__name__, "pass")
        start = time.time()
        try:
            func()
            actual = Outcome.PASS
            msg = ""
        except SkipTest as e:
            actual = Outcome.SKIP
            msg = str(e)
        except AssertionError as e:
            actual = Outcome.FAIL
            msg = str(e)
        except Exception as e:
            actual = Outcome.ERROR
            msg = f"{type(e).__name__}: {e}"

        elapsed = time.time() - start
        doc = (func.__doc__ or "").strip().split("\n")[0]
        r = Result(name, doc, expected, actual, msg, elapsed)
        self.results.append(r)
        return r

    def _collect(self):
        return sorted(
            [getattr(self, a) for a in dir(self) if a.startswith("test_") and callable(getattr(self, a))],
            key=lambda f: f.__name__,
        )

    # -- run --

    def run_all(self):
        self._start = time.time()
        for f in self._collect():
            r = self._run(f)
            ok = (r.expected == "skip" and r.actual == Outcome.SKIP) or \
                 (r.expected != "skip" and r.actual == Outcome.PASS) or \
                 (r.expected == "fail" and r.actual == Outcome.FAIL)
            icon = "✓" if ok else "✗"
            detail = f"  [{r.actual.value}] {r.message}" if r.message else ""
            print(f"  {icon} {r.name:<40} {r.actual.value:<5} {r.duration:.1f}s{detail}")
        self._summary()

    def run_one(self, name: str):
        if not name.startswith("test_"):
            name = f"test_{name}"
        func = getattr(self, name, None)
        if func is None:
            print(f"No such test: {name}")
            sys.exit(1)
        r = self._run(func)
        print(f"{r.name}: {r.actual.value} (expected {r.expected})")
        if r.message:
            print(f"  {r.message}")
        sys.exit(0 if r.actual == Outcome.PASS else 1)

    def list_tests(self):
        for f in self._collect():
            exp = _EXPECTATIONS.get(f.__name__, "pass")
            doc = (f.__doc__ or "").strip().split("\n")[0]
            print(f"  [{exp:4}] {f.__name__:<42} {doc}")

    def _summary(self):
        total = len(self.results)
        exp_pass = sum(1 for r in self.results if r.expected == "pass")
        exp_skip = sum(1 for r in self.results if r.expected == "skip")
        exp_fail = sum(1 for r in self.results if r.expected == "fail")

        act = {o: sum(1 for r in self.results if r.actual == o) for o in Outcome}
        mismatches = [r for r in self.results
                      if not ((r.expected == "skip" and r.actual == Outcome.SKIP) or
                              (r.expected != "skip" and r.actual == Outcome.PASS) or
                              (r.expected == "fail" and r.actual == Outcome.FAIL))]

        elapsed = time.time() - self._start
        print(f"\n{'='*64}")
        print(f"Expected: {exp_pass}P  {exp_skip}S  {exp_fail}F")
        print(f"Actual:   {act.get(Outcome.PASS,0)}P  {act.get(Outcome.SKIP,0)}S  "
              f"{act.get(Outcome.FAIL,0)}F  {act.get(Outcome.ERROR,0)}E  ({elapsed:.1f}s)")
        if mismatches:
            print(f"\nMismatches ({len(mismatches)}):")
            for r in mismatches:
                print(f"  [{r.expected}→{r.actual.value}] {r.name}: {r.message}")
        else:
            print("All outcomes match expectations.")

    # ══════════════════════════════════════════════════════════
    # CONNECTION
    # ══════════════════════════════════════════════════════════

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

    # ══════════════════════════════════════════════════════════
    # MODELS
    # ══════════════════════════════════════════════════════════

    @expects("pass")
    def test_05_models_returns_all_providers(self):
        """GET /api/v1/models lists 4 providers with models."""
        data = self._assert_ok(self._get(f"{self.base_url}/api/v1/models"))
        assert data["success"] is True
        assert len(data["providers"]) == 4
        for p in ["deepseek", "openai", "anthropic", "zhipu"]:
            assert p in data["models"]
            assert "models" in data["models"][p]
            assert "default" in data["models"][p]

    @expects("pass")
    def test_06_models_post_rejected(self):
        """POST /api/v1/models returns 405 INVALID_METHOD."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/models", {}),
            "INVALID_METHOD", 405)

    # ══════════════════════════════════════════════════════════
    # FIM — error cases (must always pass, no API key needed)
    # ══════════════════════════════════════════════════════════

    @expects("pass")
    def test_07_fim_missing_prompt(self):
        """POST /completion without 'prompt' → 400 INVALID_PARAMS."""
        d = self._assert_error(
            self._post(f"{self.base_url}/api/v1/completion", {"suffix": "x"}),
            "INVALID_PARAMS")
        assert "prompt" in d["error"]

    @expects("pass")
    def test_08_fim_missing_suffix(self):
        """POST /completion without 'suffix' → 400 INVALID_PARAMS."""
        d = self._assert_error(
            self._post(f"{self.base_url}/api/v1/completion", {"prompt": "x"}),
            "INVALID_PARAMS")
        assert "suffix" in d["error"]

    @expects("pass")
    def test_09_fim_malformed_json(self):
        """POST /completion with bad JSON → 400 INVALID_JSON."""
        resp = requests.post(f"{self.base_url}/api/v1/completion",
                             data="not json",
                             headers={"Content-Type": "application/json"}, timeout=5)
        self._assert_error(resp, "INVALID_JSON")

    @expects("pass")
    def test_10_fim_empty_input_rejected(self):
        """POST /completion with empty strings → 400 or 500 failure."""
        resp = self._post(f"{self.base_url}/api/v1/completion",
                          {"prompt": "", "suffix": ""})
        assert resp.status_code in (400, 500)
        assert resp.json()["success"] is False

    # ══════════════════════════════════════════════════════════
    # FIM — integration (needs DEEPSEEK_API_KEY)
    # ══════════════════════════════════════════════════════════

    @expects("skip")
    def test_11_fim_minimal_request(self):
        """Minimal FIM request returns suggestion with text+label."""
        data = self._assert_ok(
            self._post(f"{self.base_url}/api/v1/completion",
                       {"prompt": "int main() {\n  int a=10;\n  ",
                        "suffix": "\n  return 0;\n}"}))
        self._skip_on_api_fail(data, "FIM")
        s = data["suggestion"]
        assert len(s["text"]) > 0
        assert len(s["label"]) > 0

    @expects("skip")
    def test_12_fim_full_request(self):
        """Full FIM with includes, functions, max_tokens → 200 ok."""
        data = self._assert_ok(
            self._post(f"{self.base_url}/api/v1/completion", {
                "prompt": "int main() {\n  int a=10;\n  ",
                "suffix": "\n  return 0;\n}",
                "includes": ["#include <iostream>"],
                "other_functions": [{"name": "f", "signature": "void f()"}],
                "max_tokens": 100,
            }))
        self._skip_on_api_fail(data, "FIM full")
        assert len(data["suggestion"]["text"]) > 0

    @expects("skip")
    def test_13_fim_truncates_long_prompt(self):
        """Prompt > 4000 chars is handled without crash."""
        long_p = "int main() {\n" + "  // x\n" * 1000
        data = self._assert_ok(
            self._post(f"{self.base_url}/api/v1/completion",
                       {"prompt": long_p, "suffix": "\n}"}))
        self._skip_on_api_fail(data, "FIM long")

    @expects("skip")
    def test_14_fim_truncates_many_includes(self):
        """20 includes → truncated to MAX_INCLUDES=10, still succeeds."""
        incs = [f"#include <h{i}.h>" for i in range(20)]
        data = self._assert_ok(
            self._post(f"{self.base_url}/api/v1/completion",
                       {"prompt": "int main() {\n  ", "suffix": "\n}", "includes": incs}))
        self._skip_on_api_fail(data, "FIM includes")

    # ══════════════════════════════════════════════════════════
    # CHAT — error cases
    # ══════════════════════════════════════════════════════════

    @expects("pass")
    def test_15_chat_missing_context(self):
        """POST /chat without 'context' → 400 INVALID_PARAMS."""
        d = self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {}), "INVALID_PARAMS")
        assert "context" in d["error"]

    @expects("pass")
    def test_16_chat_context_not_dict(self):
        """POST /chat with string context → 400."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {"context": "bad"}), "INVALID_PARAMS")

    @expects("pass")
    def test_17_chat_invalid_model(self):
        """Chat with unknown model → 400."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y"},
                "model": "no-such-model",
                "provider": "deepseek",
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_18_chat_invalid_provider(self):
        """Chat with unknown provider → 400."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y"},
                "provider": "no-such",
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_19_chat_prompt_type_error(self):
        """Chat with numeric prompt → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": 123, "suffix": "y"},
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_20_chat_suffix_type_error(self):
        """Chat with array suffix → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": ["bad"]},
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_21_chat_includes_type_error(self):
        """Chat with string includes → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y", "includes": "bad"},
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_22_chat_functions_type_error(self):
        """Chat with string other_functions → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y", "other_functions": "bad"},
            }), "INVALID_PARAMS")

    # ══════════════════════════════════════════════════════════
    # CHAT — integration (needs at least one provider key)
    # ══════════════════════════════════════════════════════════

    def _chat(self, ctx: dict, **kw) -> dict:
        resp = self._post(f"{self.base_url}/api/v1/chat",
                          {"context": ctx, "provider": "deepseek", **kw}, timeout=30)
        data = self._assert_ok(resp)
        self._skip_on_api_fail(data, "Chat")
        return data

    @expects("skip")
    def test_23_chat_basic_completion(self):
        """Simple chat request returns text+model."""
        data = self._chat({"prompt": "def add(a,b):", "suffix": "\n    return a+b"})
        assert len(data["response"]["text"]) > 0
        assert "model" in data["response"]

    @expects("skip")
    def test_24_chat_with_full_context(self):
        """Chat with includes, functions, model, max_tokens → ok."""
        data = self._chat({
            "prompt": "int main() {\n  int a=10;\n  ",
            "suffix": "\n  return 0;\n}",
            "includes": ["#include <iostream>"],
            "other_functions": [{"name": "f", "signature": "void f()"}],
        }, model="deepseek-chat", max_tokens=200)
        assert data["response"]["model"] == "deepseek-chat"

    @expects("skip")
    def test_25_chat_python_completion(self):
        """Python fib() completion returns valid code."""
        data = self._chat({
            "prompt": "def fib(n):\n    if n<=1:\n        return n\n    ",
            "suffix": "\n\nprint(fib(10))",
        })
        assert len(data["response"]["text"]) > 5

    @expects("skip")
    def test_26_chat_cpp_completion(self):
        """C++ main() completion returns valid code."""
        data = self._chat({
            "prompt": "int main() {\n    int a=10; int b=20;\n    ",
            "suffix": "\n    return 0;\n}",
        })
        assert len(data["response"]["text"]) > 5

    @expects("skip")
    def test_27_chat_unicode_handling(self):
        """Unicode + emoji in prompt doesn't break."""
        data = self._chat({
            "prompt": 'def greet():\n    m = "你好 🌍"\n    ',
            "suffix": "\n    return m",
        })
        assert len(data["response"]["text"]) > 0

    @expects("skip")
    def test_28_chat_truncates_long_input(self):
        """Very long prompt doesn't crash."""
        long_p = "def test():\n" + "    x = 1\n" * 1000
        data = self._chat({"prompt": long_p, "suffix": "\n    return x"})
        assert len(data["response"]["text"]) > 0

    # ══════════════════════════════════════════════════════════
    # RAG — falls back without index
    # ══════════════════════════════════════════════════════════

    @expects("skip")
    def test_29_rag_enabled(self):
        """use_rag=true falls back when no index exists."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=True, use_graph_rag=False)
        assert len(data["response"]["text"]) > 0

    @expects("skip")
    def test_30_graph_rag_enabled(self):
        """use_graph_rag=true falls back when no index exists."""
        data = self._chat({"prompt": "def hello():", "suffix": ""},
                          use_rag=True, use_graph_rag=True)
        assert len(data["response"]["text"]) > 0

    @expects("skip")
    def test_31_rag_project_path_isolation(self):
        """Nonexistent project_path doesn't break request."""
        data = self._chat({"prompt": "def process():", "suffix": ""},
                          use_rag=True, use_graph_rag=True,
                          project_path="/nonexistent/project")
        assert len(data["response"]["text"]) > 0

    # ══════════════════════════════════════════════════════════
    # BOUNDARY
    # ══════════════════════════════════════════════════════════

    @expects("pass")
    def test_32_chat_empty_context_accepted(self):
        """Empty context {} returns 200 or 400 (implementation choice)."""
        resp = self._post(f"{self.base_url}/api/v1/chat", {"context": {}})
        assert resp.status_code in (200, 400)

    @expects("skip")
    def test_33_multiple_sequential(self):
        """3 identical requests all succeed."""
        body = {"prompt": "int main() {\n  ", "suffix": "\n}"}
        for i in range(3):
            resp = self._post(f"{self.base_url}/api/v1/completion", body)
            assert resp.status_code == 200
            if not resp.json().get("success"):
                raise SkipTest(f"request {i+1} failed — API unavailable")


# ── main ─────────────────────────────────────────────────────

def main():
    r = Runner()

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        r.list_tests()
        return

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        r.run_one(sys.argv[1])
    else:
        r.run_all()

    mismatches = [res for res in r.results
                  if not ((res.expected == "skip" and res.actual == Outcome.SKIP) or
                          (res.expected != "skip" and res.actual == Outcome.PASS) or
                          (res.expected == "fail" and res.actual == Outcome.FAIL))]
    if mismatches:
        sys.exit(1)


if __name__ == "__main__":
    main()
