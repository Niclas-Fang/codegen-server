from typing import Dict, Any, List, Optional
import os

from .prompt_templates import build_code_completion_prompt
from .model_providers import (
    get_provider,
    validate_model,
    get_default_model,
)

RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
GRAPH_RAG_ENABLED = os.getenv("GRAPH_RAG_ENABLED", "true").lower() == "true"

DEFAULT_MAX_TOKENS = 1000
DEFAULT_PROVIDER = "deepseek"


def validate_context(context: Dict[str, Any]) -> None:
    if not isinstance(context, dict):
        raise ValueError("context 必须是字典")

    prompt = context.get("prompt", "")
    suffix = context.get("suffix", "")

    if not isinstance(prompt, str):
        raise ValueError("context.prompt 必须是字符串")

    if not isinstance(suffix, str):
        raise ValueError("context.suffix 必须是字符串")

    includes = context.get("includes", [])
    if includes and not isinstance(includes, list):
        raise ValueError("context.includes 必须是数组")

    other_functions = context.get("other_functions", [])
    if other_functions and not isinstance(other_functions, list):
        raise ValueError("context.other_functions 必须是数组")


def _extract_imports(code: str) -> List[str]:
    imports = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ", "#include ", "using ")):
            imports.append(stripped)
        elif stripped and not stripped.startswith("#"):
            if imports:
                break
    return imports[:10]


def call_chat_api(
    context: Dict[str, Any],
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    provider: str = DEFAULT_PROVIDER,
    use_rag: bool = True,
    use_graph_rag: bool = True,
    project_path: str = "",
) -> Dict[str, str]:
    """
    调用 Chat API 获取代码补全建议

    Args:
        context: 包含 prompt, suffix, includes, other_functions 的字典
        model: 模型名称 (可选，默认使用 provider 的默认模型)
        max_tokens: 最大 token 数
        provider: 模型提供者 (deepseek, openai, anthropic, zhipu)
        use_rag: 是否使用 RAG 增强
        use_graph_rag: 是否使用 Graph-RAG 增强（优先于传统RAG）
        project_path: 项目路径，用于 RAG 向量库隔离

    Returns:
        包含 text 和 model 的字典
    """
    validate_context(context)

    model = model or get_default_model(provider)
    validate_model(provider, model)

    prompt = context.get("prompt", "")
    suffix = context.get("suffix", "")
    includes = context.get("includes", [])
    other_functions = context.get("other_functions", [])

    if not includes:
        includes = _extract_imports(prompt)

    # Try Graph-RAG first, fallback to traditional RAG
    augmented_prompt = _augment_prompt_with_graph_rag(
        prompt, suffix, use_graph_rag=use_graph_rag and use_rag, project_path=project_path
    )

    prompt_data = build_code_completion_prompt(
        prompt=augmented_prompt,
        suffix=suffix,
        includes=includes,
        other_functions=other_functions,
    )

    messages = prompt_data["messages"]

    provider_instance = get_provider(provider)

    response_text = provider_instance.chat(messages, model, max_tokens)

    return {"text": response_text, "model": model, "provider": provider}


def _augment_prompt_with_graph_rag(
    prompt: str, suffix: str, use_graph_rag: bool = True, project_path: str = ""
) -> str:
    """Use Graph-RAG for context augmentation."""
    if not GRAPH_RAG_ENABLED or not use_graph_rag:
        return _augment_prompt_with_rag(prompt, suffix, use_rag=True, project_path=project_path)

    try:
        from .rag.graph_retriever import augment_context_with_graph_rag
    except ImportError:
        return _augment_prompt_with_rag(prompt, suffix, use_rag=True, project_path=project_path)

    try:
        return augment_context_with_graph_rag(
            prompt=prompt,
            suffix=suffix,
            project_path=project_path,
            use_graph_rag=True,
        )
    except Exception:
        return _augment_prompt_with_rag(prompt, suffix, use_rag=True, project_path=project_path)


def _augment_prompt_with_rag(
    prompt: str, suffix: str, use_rag: bool = True, project_path: str = ""
) -> str:
    if not RAG_ENABLED or not use_rag:
        return prompt

    try:
        from .rag.retriever import retrieve_relevant_code, format_retrieval_context
    except ImportError:
        return prompt

    try:
        full_context = prompt
        if suffix:
            full_context += "\n" + suffix

        results = retrieve_relevant_code(
            query=full_context, project_path=project_path
        )

        if not results:
            return prompt

        rag_context = format_retrieval_context(results)

        if not rag_context:
            return prompt

        return f"""// Relevant code from knowledge base:
{rag_context}

// Current code context:
{prompt}"""
    except Exception:
        return prompt
