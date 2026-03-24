import os
import requests
from typing import List, Dict, Any, Optional

DEFAULT_TIMEOUT = 30

SUPPORTED_MODELS = {
    "deepseek": {
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default": "deepseek-chat",
        "description": {
            "deepseek-chat": "DeepSeek-V3.2 通用对话模型，适合代码补全和日常对话",
            "deepseek-reasoner": "DeepSeek-V3.2 推理模型，支持深度思考模式",
        },
    },
    "openai": {
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1",
            "o1-mini",
            "o1-preview",
        ],
        "default": "gpt-4o",
        "description": {
            "gpt-4o": "GPT-4 优化版，速度快、成本低，推荐使用",
            "gpt-4o-mini": "轻量版 GPT-4o，更快更便宜",
            "gpt-4-turbo": "GPT-4 Turbo，支持 128K 上下文",
            "gpt-4": "GPT-4 原版，稳定可靠",
            "gpt-3.5-turbo": "GPT-3.5，速度快成本低",
            "o1": "OpenAI o1 推理模型，适合复杂任务",
            "o1-mini": "轻量版 o1，平衡速度和推理能力",
            "o1-preview": "o1 预览版",
        },
    },
    "anthropic": {
        "models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        "default": "claude-3-5-sonnet-20241022",
        "description": {
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet，最新版，性能优异",
            "claude-3-5-haiku-20241022": "Claude 3.5 Haiku，轻量快速",
            "claude-3-opus-20240229": "Claude 3 Opus，最强能力",
            "claude-3-sonnet-20240229": "Claude 3 Sonnet，平衡性能",
            "claude-3-haiku-20240307": "Claude 3 Haiku，快速响应",
        },
    },
    "zhipu": {
        "models": [
            "glm-4.7",
            "glm-4.6",
            "glm-4.5",
            "glm-4.5-air",
            "glm-4-plus",
            "glm-4-flash",
            "glm-4",
        ],
        "default": "glm-4.7",
        "description": {
            "glm-4.7": "GLM-4.7 最新版，专注于代码生成和 Agent 任务（推理模型，输出包含思考过程）",
            "glm-4.6": "GLM-4.6，增强推理和代码能力（推理模型）",
            "glm-4.5": "GLM-4.5 旗舰版，355B 参数 MoE 架构（推理模型）",
            "glm-4.5-air": "GLM-4.5-Air 轻量版，106B 参数",
            "glm-4-plus": "GLM-4 Plus，增强版通用模型，推荐用于代码补全",
            "glm-4-flash": "GLM-4 Flash，快速响应版本，推荐用于代码补全",
            "glm-4": "GLM-4 基础版",
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
