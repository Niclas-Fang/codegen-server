"""FIM (Fill-in-the-Middle) completion tests."""

from tests.runner import BaseRunner, expects


class TestFIM(BaseRunner):

    # ── error cases (always pass) ────────────────────────────

    @expects("pass")
    def test_01_fim_missing_prompt(self):
        """POST /completion without 'prompt' → 400 INVALID_PARAMS."""
        d = self._assert_error(
            self._post(f"{self.base_url}/api/v1/completion", {"suffix": "x"}),
            "INVALID_PARAMS")
        assert "prompt" in d["error"]

    @expects("pass")
    def test_02_fim_missing_suffix(self):
        """POST /completion without 'suffix' → 400 INVALID_PARAMS."""
        d = self._assert_error(
            self._post(f"{self.base_url}/api/v1/completion", {"prompt": "x"}),
            "INVALID_PARAMS")
        assert "suffix" in d["error"]

    @expects("pass")
    def test_03_fim_malformed_json(self):
        """POST /completion with bad JSON → 400 INVALID_JSON."""
        import requests
        resp = requests.post(f"{self.base_url}/api/v1/completion",
                             data="not json",
                             headers={"Content-Type": "application/json"}, timeout=5)
        self._assert_error(resp, "INVALID_JSON")

    @expects("pass")
    def test_04_fim_empty_input_rejected(self):
        """POST /completion with empty strings → 400 or 500 failure."""
        resp = self._post(f"{self.base_url}/api/v1/completion",
                          {"prompt": "", "suffix": ""})
        assert resp.status_code in (400, 500)
        assert resp.json()["success"] is False

    # ── integration (needs DEEPSEEK_API_KEY) ─────────────────

    @expects("pass")
    def test_05_fim_minimal_request(self):
        """Minimal FIM request returns suggestion with text+label."""
        prompt = "int main() {\n  int a=10;\n  "
        suffix = "\n  return 0;\n}"
        data = self._fim({"prompt": prompt, "suffix": suffix})
        s = data["suggestion"]
        assert len(s["text"]) > 0
        assert len(s["label"]) > 0
        self._check_syntax(prompt, s["text"], suffix, "fim minimal")

    @expects("pass")
    def test_06_fim_full_request(self):
        """Full FIM with includes, functions, max_tokens → 200 ok."""
        prompt = "int main() {\n  int a=10;\n  "
        suffix = "\n  return 0;\n}"
        data = self._fim({
            "prompt": prompt, "suffix": suffix,
            "includes": ["#include <iostream>"],
            "other_functions": [{"name": "f", "signature": "void f()"}],
            "max_tokens": 100,
        })
        assert len(data["suggestion"]["text"]) > 0
        self._check_syntax(prompt, data["suggestion"]["text"], suffix, "fim full")

    @expects("pass")
    def test_07_fim_truncates_long_prompt(self):
        """Prompt > 4000 chars is handled without crash."""
        long_p = "int main() {\n" + "  // x\n" * 1000
        self._fim({"prompt": long_p, "suffix": "\n}"})

    @expects("pass")
    def test_08_fim_truncates_many_includes(self):
        """20 includes → truncated to MAX_INCLUDES=10, still succeeds."""
        incs = [f"#include <h{i}.h>" for i in range(20)]
        self._fim({"prompt": "int main() {\n  ", "suffix": "\n}", "includes": incs})

    @expects("pass")
    def test_09_fim_response_structure(self):
        """FIM response has text, label with correct types."""
        data = self._fim({"prompt": "int x = ", "suffix": ";\n"})
        s = data["suggestion"]
        assert isinstance(s["text"], str)
        assert isinstance(s["label"], str)
        assert len(s["text"]) <= 500

    @expects("pass")
    def test_10_fim_respects_max_tokens(self):
        """Small max_tokens yields short response."""
        data = self._fim({"prompt": "int main() {\n  int a=10;\n  ",
                          "suffix": "\n  return 0;\n}", "max_tokens": 20})
        assert len(data["suggestion"]["text"]) < 200

    @expects("pass")
    def test_11_fim_handles_only_prompt(self):
        """minimal prompt with empty suffix still works."""
        self._fim({"prompt": "def foo():", "suffix": ""})
