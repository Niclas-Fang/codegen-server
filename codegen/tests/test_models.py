"""Models endpoint tests."""

from tests.runner import BaseRunner, expects


class TestModels(BaseRunner):

    @expects("pass")
    def test_01_models_returns_all_providers(self):
        """GET /api/v1/models lists 4 providers with models."""
        data = self._assert_ok(self._get(f"{self.base_url}/api/v1/models"))
        assert data["success"] is True
        assert len(data["providers"]) == 4
        for p in ["deepseek", "openai", "anthropic", "zhipu"]:
            assert p in data["models"]
            assert "models" in data["models"][p]
            assert "default" in data["models"][p]

    @expects("pass")
    def test_02_models_post_rejected(self):
        """POST /api/v1/models returns 405 INVALID_METHOD."""
        self._assert_error(
            self._post(f"{self.base_url}/api/v1/models", {}),
            "INVALID_METHOD", 405)

    @expects("pass")
    def test_03_models_have_descriptions(self):
        """Every model has a description string."""
        data = self._assert_ok(self._get(f"{self.base_url}/api/v1/models"))
        for p, info in data["models"].items():
            for m in info["models"]:
                assert m in info["description"], f"{p}/{m} missing description"
                assert len(info["description"][m]) > 10

    @expects("pass")
    def test_04_models_defaults_are_valid(self):
        """Provider defaults exist in their model list."""
        data = self._assert_ok(self._get(f"{self.base_url}/api/v1/models"))
        for p, info in data["models"].items():
            assert info["default"] in info["models"], f"{p} default {info['default']} not in list"

    @expects("pass")
    def test_05_health_lists_four_providers(self):
        """Health endpoint reports all 4 providers with configured flag."""
        data = self._assert_ok(self._get(f"{self.base_url}/api/v1/health"))
        for p in ["deepseek", "openai", "anthropic", "zhipu"]:
            assert p in data["providers"], f"missing {p}"
            assert "configured" in data["providers"][p]
            assert "default_model" in data["providers"][p]
