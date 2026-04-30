"""
Model providers with unified API key handling and OpenAI-compatible base.
To add a new provider: add an entry to PROVIDER_CONFIG and SUPPORTED_MODELS.
"""

import os
import requests
from typing import List, Dict, Any

DEFAULT_TIMEOUT = 30

# ── provider configuration ──────────────────────────────────

PROVIDER_CONFIG = {
    "deepseek": {
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "api_key_env": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "api_url": "https://api.openai.com/v1/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-5.4",
    },
    "zhipu": {
        "api_url": "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions",
        "api_key_env": "ZHIPU_API_KEY",
        "default_model": "glm-5",
    },
    "anthropic": {
        "api_url": "https://api.anthropic.com/v1/messages",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-6-20250217",
    },
}

SUPPORTED_MODELS = {
    "deepseek": {
        "models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
        "description": {
            "deepseek-v4-pro": "DeepSeek-V4 Pro，1.6T MoE，1M 上下文，旗舰推理与编码",
            "deepseek-v4-flash": "DeepSeek-V4 Flash，284B MoE，1M 上下文，高性价比",
            "deepseek-chat": "DeepSeek-V3.2 通用对话，128K 上下文",
            "deepseek-reasoner": "DeepSeek-V3.2 推理模型",
        },
    },
    "openai": {
        "models": ["gpt-5.5", "gpt-5.4"],
        "description": {
            "gpt-5.5": "GPT-5.5 旗舰推理与编码模型，1M 上下文，82.7% Terminal-Bench",
            "gpt-5.4": "GPT-5.4 高性能推理模型，1M 上下文",
        },
    },
    "anthropic": {
        "models": ["claude-opus-4-7-20260416", "claude-sonnet-4-6-20250217"],
        "description": {
            "claude-opus-4-7-20260416": "Claude Opus 4.7 旗舰，87.6% SWE-bench，1M 上下文",
            "claude-sonnet-4-6-20250217": "Claude Sonnet 4.6 主力，最佳性价比",
        },
    },
    "zhipu": {
        "models": ["glm-5.1", "glm-5"],
        "description": {
            "glm-5.1": "GLM-5.1 全自治 Agent，8h 自主工作，SWE-Bench Pro 58.4",
            "glm-5": "GLM-5 旗舰，744B/40B MoE，200K 上下文，开源 SOTA",
        },
    },
}

# Set default model for each provider from PROVIDER_CONFIG
for _name, _cfg in PROVIDER_CONFIG.items():
    if _name in SUPPORTED_MODELS:
        SUPPORTED_MODELS[_name]["default"] = _cfg["default_model"]


# ── validation helpers ──────────────────────────────────────

def validate_model(provider: str, model: str) -> str:
    provider = provider.lower()
    if provider not in SUPPORTED_MODELS:
        raise ValueError(f"不支持的模型提供者: {provider}。支持: {list(SUPPORTED_MODELS.keys())}")
    supported = SUPPORTED_MODELS[provider]["models"]
    if model not in supported:
        raise ValueError(f"Provider '{provider}' 不支持模型 '{model}'。支持的模型: {supported}")
    return model


def get_default_model(provider: str) -> str:
    provider = provider.lower()
    if provider not in PROVIDER_CONFIG:
        raise ValueError(f"不支持的模型提供者: {provider}")
    return PROVIDER_CONFIG[provider]["default_model"]


def get_all_models() -> Dict[str, Dict[str, Any]]:
    return SUPPORTED_MODELS


# ── base providers ──────────────────────────────────────────

class BaseProvider:
    """模型提供者基类 — 统一 API key 获取."""

    provider: str = ""  # set by subclass

    def get_api_key(self) -> str:
        cfg = PROVIDER_CONFIG[self.provider]
        key = os.getenv(cfg["api_key_env"])
        if not key:
            raise ValueError(f"{cfg['api_key_env']} 环境变量未设置")
        return key

    def chat(self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000) -> str:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
    """OpenAI-compatible chat completions — used by DeepSeek, OpenAI, Zhipu."""

    def _parse_response(self, result: dict) -> str:
        """Extract content from response. Override for provider-specific parsing."""
        return result["choices"][0]["message"]["content"]

    def chat(self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000) -> str:
        cfg = PROVIDER_CONFIG[self.provider]
        model = model or cfg["default_model"]
        api_key = self.get_api_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {"model": model, "messages": messages, "max_tokens": max_tokens}

        try:
            resp = requests.post(cfg["api_url"], headers=headers, json=body, timeout=DEFAULT_TIMEOUT)
        except requests.exceptions.Timeout:
            raise Exception(f"{self.provider} API 调用超时")
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接到 {self.provider} API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"{self.provider} API 调用失败: {e}")

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                pass
            raise Exception(f"{self.provider} API 返回错误: {resp.status_code}" + (f" - {detail}" if detail else ""))

        result = resp.json()
        if "choices" not in result or not result["choices"]:
            return ""
        return self._parse_response(result)


class AnthropicProvider(BaseProvider):
    """Anthropic Messages API — different request/response format."""

    provider = "anthropic"

    def chat(self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000) -> str:
        cfg = PROVIDER_CONFIG[self.provider]
        model = model or cfg["default_model"]
        api_key = self.get_api_key()

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        system = ""
        user = ""
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "user":
                user = msg["content"]

        body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": user}]}
        if system:
            body["system"] = system

        try:
            resp = requests.post(cfg["api_url"], headers=headers, json=body, timeout=DEFAULT_TIMEOUT)
        except requests.exceptions.Timeout:
            raise Exception("Anthropic API 调用超时")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到 Anthropic API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Anthropic API 调用失败: {e}")

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except Exception:
                pass
            raise Exception(f"Anthropic API 返回错误: {resp.status_code}" + (f" - {detail}" if detail else ""))

        result = resp.json()
        if "content" not in result or not result["content"]:
            return ""
        return result["content"][0]["text"]


# ── concrete providers ──────────────────────────────────────

class DeepSeekProvider(OpenAICompatibleProvider):
    provider = "deepseek"


class OpenAIProvider(OpenAICompatibleProvider):
    provider = "openai"


class ZhipuProvider(OpenAICompatibleProvider):
    """智谱AI — OpenAI兼容，推理模型需回退到 reasoning_content."""

    provider = "zhipu"

    def _parse_response(self, result: dict) -> str:
        msg = result["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content", "")


# ── provider registry ───────────────────────────────────────

_PROVIDER_CLASSES = {
    "deepseek": DeepSeekProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "zhipu": ZhipuProvider,
}

_DEFAULT_PROVIDER = "deepseek"


def get_provider(name: str = None) -> BaseProvider:
    name = (name or _DEFAULT_PROVIDER).lower()
    cls = _PROVIDER_CLASSES.get(name)
    if not cls:
        raise ValueError(f"不支持的模型提供者: {name}")
    return cls()


def get_available_providers() -> List[str]:
    return list(_PROVIDER_CLASSES.keys())
