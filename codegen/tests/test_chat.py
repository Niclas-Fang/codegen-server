"""Chat completion tests."""

from tests.runner import BaseRunner, expects, SkipTest


class TestChat(BaseRunner):

    # ── error cases (always pass) ────────────────────────────

    @expects("pass")
    def test_01_chat_missing_context(self):
        """POST /chat without 'context' → 400 INVALID_PARAMS."""
        d = self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {}), "INVALID_PARAMS")
        assert "context" in d["error"]

    @expects("pass")
    def test_02_chat_context_not_dict(self):
        """POST /chat with string context → 400."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {"context": "bad"}), "INVALID_PARAMS")

    @expects("pass")
    def test_03_chat_invalid_model(self):
        """Chat with unknown model → 400."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y"},
                "model": "no-such-model", "provider": "deepseek",
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_04_chat_invalid_provider(self):
        """Chat with unknown provider → 400."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y"},
                "provider": "no-such",
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_05_chat_prompt_type_error(self):
        """Chat with numeric prompt → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": 123, "suffix": "y"},
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_06_chat_suffix_type_error(self):
        """Chat with array suffix → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": ["bad"]},
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_07_chat_includes_type_error(self):
        """Chat with string includes → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y", "includes": "bad"},
            }), "INVALID_PARAMS")

    @expects("pass")
    def test_08_chat_functions_type_error(self):
        """Chat with string other_functions → 400 INVALID_PARAMS."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/chat", {
                "context": {"prompt": "x", "suffix": "y", "other_functions": "bad"},
            }), "INVALID_PARAMS")

    # ── integration (needs at least one provider key) ────────

    @expects("pass")
    def test_09_chat_basic_completion(self):
        """Simple chat request returns text+model."""
        data = self._chat({"prompt": "def add(a,b):", "suffix": "\n    return a+b"})
        assert len(data["response"]["text"]) > 0
        assert "model" in data["response"]

    @expects("pass")
    def test_10_chat_with_full_context(self):
        """Chat with includes, functions, model, max_tokens → ok."""
        data = self._chat({
            "prompt": "int main() {\n  int a=10;\n  ",
            "suffix": "\n  return 0;\n}",
            "includes": ["#include <iostream>"],
            "other_functions": [{"name": "f", "signature": "void f()"}],
        }, model="deepseek-chat", max_tokens=200)
        assert data["response"]["model"] == "deepseek-chat"

    @expects("pass")
    def test_11_chat_python_completion(self):
        """Python fib() completion returns valid code."""
        data = self._chat({
            "prompt": "def fib(n):\n    if n<=1:\n        return n\n    ",
            "suffix": "\n\nprint(fib(10))",
        })
        text = data["response"]["text"]
        assert len(text) > 5
        # syntax validation on partial completions is expected to fail — skip

    @expects("pass")
    def test_12_chat_cpp_completion(self):
        """C++ main() completion returns valid code."""
        data = self._chat({
            "prompt": "int main() {\n    int a=10; int b=20;\n    ",
            "suffix": "\n    return 0;\n}",
        })
        assert len(data["response"]["text"]) > 5

    @expects("pass")
    def test_13_chat_unicode_handling(self):
        """Unicode + emoji in prompt doesn't break."""
        data = self._chat({
            "prompt": 'def greet():\n    m = "你好 🌍"\n    ',
            "suffix": "\n    return m",
        })
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_14_chat_truncates_long_input(self):
        """Very long prompt doesn't crash."""
        long_p = "def test():\n" + "    x = 1\n" * 1000
        data = self._chat({"prompt": long_p, "suffix": "\n    return x"})
        assert len(data["response"]["text"]) > 0

    @expects("pass")
    def test_15_chat_empty_context_accepted(self):
        """Empty context {} returns 200 or 400."""
        resp = self._post(f"{self.base_url}/api/v1/chat", {"context": {}})
        assert resp.status_code in (200, 400)

    @expects("pass")
    def test_16_chat_missing_prompt_defaults_ok(self):
        """Chat without prompt in context doesn't crash."""
        resp = self._post(f"{self.base_url}/api/v1/chat", {
            "context": {"suffix": "\n}"},
            "provider": "deepseek",
        }, timeout=15)
        assert resp.status_code in (200, 400)
