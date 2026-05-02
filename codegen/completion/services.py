"""FIM (Fill-in-the-Middle) code completion — prompt construction + DeepSeek API."""

from typing import Dict, List, Any, Optional

MAX_TOTAL_LENGTH = 8000
MAX_INCLUDES = 10
MAX_FUNCTIONS = 5
MAX_PROMPT_LENGTH = 4000


def _build_fim_prompt(prompt: str, suffix: str, includes: List[str],
                      other_functions: List[Dict[str, Any]]) -> tuple[str, str]:
    """Construct the FIM-format prompt from includes, functions, and code context.

    Returns (full_prompt, possibly_truncated_suffix).
    """
    parts: List[str] = []

    if includes:
        cleaned = [i.strip() for i in includes[:MAX_INCLUDES] if i.strip()]
        if cleaned:
            parts.extend(cleaned)

    if parts and other_functions:
        parts.extend(["", "==========", ""])

    if other_functions:
        parts.append("// Available functions in this file:")
        for f in other_functions[:MAX_FUNCTIONS]:
            sig = f.get("signature") or f.get("name", "")
            if sig:
                parts.append(f"//   {sig}")

    if parts and (includes or other_functions):
        parts.extend(["", "==========", ""])

    trimmed = prompt[:MAX_PROMPT_LENGTH] if len(prompt) > MAX_PROMPT_LENGTH else prompt
    parts.append(trimmed)

    full_prompt = "\n".join(parts)
    total = len(full_prompt) + len(suffix)

    if total > MAX_TOTAL_LENGTH:
        max_suffix = MAX_TOTAL_LENGTH - len(full_prompt)
        if max_suffix > 100:
            suffix = suffix[:max_suffix]
        else:
            available = MAX_TOTAL_LENGTH - 200
            if available > 0:
                full_prompt = full_prompt[-available:]
                suffix = suffix[:200]
            else:
                full_prompt = trimmed[-500:]
                suffix = suffix[:500]

    return full_prompt, suffix


def call_fim_api(prompt: str, suffix: str, includes: List[str],
                 other_functions: List[Dict[str, Any]],
                 max_tokens: int) -> Optional[Dict[str, str]]:
    """Call DeepSeek FIM API for code completion.

    Handles input validation, prompt construction, and delegates
    the HTTP call to DeepSeekProvider.fim().
    """
    if not isinstance(prompt, str) or not isinstance(suffix, str):
        raise ValueError("prompt和suffix必须是字符串")
    if includes and not isinstance(includes, list):
        raise ValueError("includes必须是数组")
    if other_functions and not isinstance(other_functions, list):
        raise ValueError("other_functions必须是数组")

    for i, inc in enumerate(includes or []):
        if not isinstance(inc, str):
            raise ValueError(f"includes[{i}]必须是字符串")
    for i, f in enumerate(other_functions or []):
        if not isinstance(f, dict):
            raise ValueError(f"other_functions[{i}]必须是对象")
        if "name" not in f:
            f["name"] = f"function_{i}"

    full_prompt, suffix = _build_fim_prompt(prompt, suffix, includes, other_functions)

    from .model_providers import DeepSeekProvider
    provider = DeepSeekProvider()
    return provider.fim(full_prompt, suffix, max_tokens=max_tokens)
