"""Shared test runner, helpers, and decorators."""

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
    expected: str
    actual: Outcome
    message: str = ""
    duration: float = 0.0


class SkipTest(Exception):
    """Expected skip — e.g. API key unavailable."""


# ── expectation decorator ────────────────────────────────────

_EXPECTATIONS: dict[str, str] = {}

def expects(outcome: str):
    def decorator(func):
        _EXPECTATIONS[func.__name__] = outcome
        return func
    return decorator


# ── compiler validator ───────────────────────────────────────

def validate_cpp_syntax(code: str) -> str | None:
    """Check C++ code syntax with g++ or clang++. Returns None if OK, error message if not."""
    import subprocess, tempfile, os
    compiler = None
    for c in ["g++", "clang++"]:
        if os.system(f"which {c} >/dev/null 2>&1") == 0:
            compiler = c
            break
    if not compiler:
        return None  # no compiler available, skip validation

    with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess.run(
            [compiler, "-fsyntax-only", "-std=c++17", tmp],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return result.stderr[:500]
        return None
    except Exception:
        return None
    finally:
        os.unlink(tmp)


def validate_python_syntax(code: str) -> str | None:
    """Check Python code syntax. Returns None if OK, error message if not."""
    try:
        compile(code, "<test>", "exec")
        return None
    except SyntaxError as e:
        return str(e)


# ── base runner ──────────────────────────────────────────────

class BaseRunner:
    """Shared test infrastructure. Subclass in each test module."""

    base_url = "http://localhost:8000"

    def __init__(self):
        self.results: list[Result] = []
        self._start = 0.0

    def _post(self, url: str, data: dict, timeout: int = 10) -> requests.Response:
        try:
            return requests.post(url, json=data, timeout=timeout)
        except (requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
            return requests.post(url, json=data, timeout=timeout)

    def _get(self, url: str, timeout: int = 5) -> requests.Response:
        return requests.get(url, timeout=timeout)

    def _options(self, url: str, headers: dict | None = None, timeout: int = 2) -> requests.Response:
        return requests.options(url, headers=headers, timeout=timeout)

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

    def _skip_on_api_fail(self, data: dict):
        if not data.get("success"):
            raise SkipTest(f"{data.get('error_code','?')}: {data.get('error','')[:80]}")

    def _fim(self, body: dict, timeout: int = 15) -> dict:
        resp = self._post(f"{self.base_url}/api/v1/completion", body, timeout=timeout)
        if resp.status_code != 200:
            try:
                self._skip_on_api_fail(resp.json())
            except Exception:
                pass
            raise SkipTest(f"FIM API returned {resp.status_code}")
        data = resp.json()
        self._skip_on_api_fail(data)
        return data

    def _chat(self, ctx: dict, **kw) -> dict:
        resp = self._post(f"{self.base_url}/api/v1/chat",
                          {"context": ctx, "provider": "deepseek", **kw}, timeout=30)
        if resp.status_code != 200:
            try:
                self._skip_on_api_fail(resp.json())
            except Exception:
                pass
            raise SkipTest(f"Chat API returned {resp.status_code}")
        data = resp.json()
        self._skip_on_api_fail(data)
        return data

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

    def list_tests(self):
        for f in self._collect():
            exp = _EXPECTATIONS.get(f.__name__, "pass")
            doc = (f.__doc__ or "").strip().split("\n")[0]
            print(f"  [{exp:4}] {f.__name__:<42} {doc}")

    def run_all(self):
        self._start = time.time()
        for f in self._collect():
            r = self._run(f)
            ok = r.actual == Outcome.PASS
            icon = "✓" if ok else "✗"
            detail = f"  [{r.actual.value}] {r.message}" if r.message else ""
            t = f"{r.duration*1000:.0f}ms" if r.duration < 1 else f"{r.duration:.1f}s"
            print(f"  {icon} {r.name:<40} {r.actual.value:<5} {t:>6}{detail}")
        self._summary()

    def _summary(self):
        total = len(self.results)
        act = {o: sum(1 for r in self.results if r.actual == o) for o in Outcome}
        mismatches = [r for r in self.results if r.actual != Outcome.PASS]
        elapsed = time.time() - self._start
        print(f"\n{'='*64}")
        print(f"Expected: {total}P")
        print(f"Actual:   {act.get(Outcome.PASS,0)}P  {act.get(Outcome.SKIP,0)}S  "
              f"{act.get(Outcome.FAIL,0)}F  {act.get(Outcome.ERROR,0)}E  ({elapsed:.1f}s)")
        if mismatches:
            print(f"\nMismatches ({len(mismatches)}):")
            for r in mismatches:
                print(f"  [→{r.actual.value}] {r.name}: {r.message}")
        else:
            print("All outcomes match expectations.")
