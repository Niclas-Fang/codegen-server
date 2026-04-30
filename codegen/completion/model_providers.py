import os
import requests
from typing import List, Dict, Any, Optional

DEFAULT_TIMEOUT = 30

SUPPORTED_MODELS = {
    "deepseek": {
        "models": [
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "deepseek-chat",
            "deepseek-reasoner",
        ],
        "default": "deepseek-chat",
        "description": {
            "deepseek-v4-pro": "DeepSeek-V4 Pro，1.6T MoE，1M 上下文，旗舰推理与编码",
            "deepseek-v4-flash": "DeepSeek-V4 Flash，284B MoE，1M 上下文，高性价比",
            "deepseek-chat": "DeepSeek-V3.2 通用对话，128K 上下文，即将路由到 V4 Flash",
            "deepseek-reasoner": "DeepSeek-V3.2 推理模型，深度思考模式",
        },
    },
    "openai": {
        "models": [
            "gpt-5.4",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o4-mini",
            "o3-pro",
        ],
        "default": "gpt-4o",
        "description": {
            "gpt-5.4": "GPT-5.4 旗舰推理与编码模型",
            "gpt-4.1": "GPT-4.1 最强非推理模型，1M 上下文",
            "gpt-4.1-mini": "GPT-4.1 Mini 轻量非推理模型",
            "gpt-4o": "GPT-4o 优化版，速度快，推荐使用",
            "gpt-4o-mini": "GPT-4o Mini 轻量快速版",
            "gpt-4-turbo": "GPT-4 Turbo，128K 上下文，即将退役",
            "o4-mini": "OpenAI o4-mini 轻量推理模型",
            "o3-pro": "OpenAI o3-pro 深度推理模型",
        },
    },
    "anthropic": {
        "models": [
            "claude-opus-4-7-20260416",
            "claude-sonnet-4-6-20250217",
            "claude-haiku-4-5-20251001",
        ],
        "default": "claude-sonnet-4-6-20250217",
        "description": {
            "claude-opus-4-7-20260416": "Claude Opus 4.7 旗舰，87.6% SWE-bench，1M 上下文",
            "claude-sonnet-4-6-20250217": "Claude Sonnet 4.6 主力，最佳性价比",
            "claude-haiku-4-5-20251001": "Claude Haiku 4.5 轻量快速，200K 上下文",
        },
    },
    "zhipu": {
        "models": [
            "glm-5",
            "glm-4.7",
            "glm-4.7-flash",
            "glm-4-plus",
            "glm-4-flash",
            "GLM-Z1-32B-0414",
        ],
        "default": "glm-4-flash",
        "description": {
            "glm-5": "GLM-5 旗舰，744B/40B MoE，200K 上下文，开源 SOTA",
            "glm-4.7": "GLM-4.7 Agentic Coding 模型，SWE-bench 73.8%",
            "glm-4.7-flash": "GLM-4.7 Flash 免费混合思考，MIT 开源",
            "glm-4-plus": "GLM-4 Plus 增强版通用模型，推荐用于代码补全",
            "glm-4-flash": "GLM-4 Flash 快速响应，免费调用",
            "GLM-Z1-32B-0414": "GLM-Z1 推理模型 32B，128K 上下文，极致性价比",
        },
    },
}


def validate_model(provider: str, model: str) -> str:
    """验证模型名称，返回验证后的模型名称"""
    provider = provider.lower()
    if provider not in SUPPORTED_MODELS:
        raise ValueError(
            f"不支持的模型提供者: {provider}。支持: {list(SUPPORTED_MODELS.keys())}"
        )

    supported = SUPPORTED_MODELS[provider]["models"]
    if model not in supported:
        raise ValueError(
            f"Provider '{provider}' 不支持模型 '{model}'。支持的模型: {supported}"
        )
    return model


def get_default_model(provider: str) -> str:
    """获取提供者的默认模型"""
    provider = provider.lower()
    if provider not in SUPPORTED_MODELS:
        raise ValueError(f"不支持的模型提供者: {provider}")
    return SUPPORTED_MODELS[provider]["default"]


def get_all_models() -> Dict[str, Dict[str, Any]]:
    """获取所有支持的模型信息"""
    return SUPPORTED_MODELS


class BaseProvider:
    """模型提供者基类"""

    def chat(self, messages: List[Dict[str, str]], model: str, max_tokens: int) -> str:
        raise NotImplementedError

    def get_api_key(self) -> str:
        raise NotImplementedError


class DeepSeekProvider(BaseProvider):
    """DeepSeek 模型提供者"""

    API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEFAULT_MODEL = "deepseek-chat"

    def get_api_key(self) -> str:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 环境变量未设置")
        return api_key

    def chat(
        self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000
    ) -> str:
        model = model or self.DEFAULT_MODEL
        api_key = self.get_api_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {"model": model, "messages": messages, "max_tokens": max_tokens}

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=data, timeout=DEFAULT_TIMEOUT
            )

            if response.status_code != 200:
                error_msg = f"DeepSeek API 返回错误: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += (
                        f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                    )
                except:
                    pass
                raise Exception(error_msg)

            result = response.json()

            if "choices" not in result or not result["choices"]:
                return ""

            return result["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            raise Exception("DeepSeek API 调用超时")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到 DeepSeek API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API 调用失败: {str(e)}")


class OpenAIProvider(BaseProvider):
    """OpenAI 模型提供者"""

    API_URL = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4"

    def get_api_key(self) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 环境变量未设置")
        return api_key

    def chat(
        self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000
    ) -> str:
        model = model or self.DEFAULT_MODEL
        api_key = self.get_api_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {"model": model, "messages": messages, "max_tokens": max_tokens}

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=data, timeout=DEFAULT_TIMEOUT
            )

            if response.status_code != 200:
                error_msg = f"OpenAI API 返回错误: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += (
                        f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                    )
                except:
                    pass
                raise Exception(error_msg)

            result = response.json()

            if "choices" not in result or not result["choices"]:
                return ""

            return result["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            raise Exception("OpenAI API 调用超时")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到 OpenAI API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API 调用失败: {str(e)}")


class AnthropicProvider(BaseProvider):
    """Anthropic 模型提供者"""

    API_URL = "https://api.anthropic.com/v1/messages"
    DEFAULT_MODEL = "claude-3-sonnet-20240229"

    def get_api_key(self) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")
        return api_key

    def chat(
        self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000
    ) -> str:
        model = model or self.DEFAULT_MODEL
        api_key = self.get_api_key()

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        system_message = ""
        user_message = ""
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                user_message = msg["content"]

        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_message}],
        }

        if system_message:
            data["system"] = system_message

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=data, timeout=DEFAULT_TIMEOUT
            )

            if response.status_code != 200:
                error_msg = f"Anthropic API 返回错误: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += (
                        f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                    )
                except:
                    pass
                raise Exception(error_msg)

            result = response.json()

            if "content" not in result or not result["content"]:
                return ""

            return result["content"][0]["text"]

        except requests.exceptions.Timeout:
            raise Exception("Anthropic API 调用超时")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到 Anthropic API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Anthropic API 调用失败: {str(e)}")


class ZhipuProvider(BaseProvider):
    """智谱AI模型提供者 (兼容OpenAI)"""

    API_URL = "https://open.bigmodel.cn/api/coding/paas/v4/chat/completions"
    DEFAULT_MODEL = "glm-4-flash"

    def get_api_key(self) -> str:
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise ValueError("ZHIPU_API_KEY 环境变量未设置")
        return api_key

    def chat(
        self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000
    ) -> str:
        model = model or self.DEFAULT_MODEL
        api_key = self.get_api_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {"model": model, "messages": messages, "max_tokens": max_tokens}

        try:
            response = requests.post(
                self.API_URL, headers=headers, json=data, timeout=DEFAULT_TIMEOUT
            )

            if response.status_code != 200:
                error_msg = f"智谱AI API 返回错误: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += (
                        f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                    )
                except:
                    pass
                raise Exception(error_msg)

            result = response.json()

            if "choices" not in result or not result["choices"]:
                return ""

            message = result["choices"][0]["message"]
            content = message.get("content", "")
            if not content:
                content = message.get("reasoning_content", "")
            return content

        except requests.exceptions.Timeout:
            raise Exception("智谱AI API 调用超时")
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到智谱AI API")
        except requests.exceptions.RequestException as e:
            raise Exception(f"智谱AI API 调用失败: {str(e)}")


_PROVIDER_MAP = {
    "deepseek": DeepSeekProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "zhipu": ZhipuProvider,
}

_DEFAULT_PROVIDER = "deepseek"


def get_provider(name: str = None) -> BaseProvider:
    """获取模型提供者实例"""
    name = name or _DEFAULT_PROVIDER
    provider_class = _PROVIDER_MAP.get(name.lower())
    if not provider_class:
        raise ValueError(f"不支持的模型提供者: {name}")
    return provider_class()


def get_available_providers() -> List[str]:
    """获取可用的模型提供者列表"""
    return list(_PROVIDER_MAP.keys())
