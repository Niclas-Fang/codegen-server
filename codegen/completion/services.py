import json
import requests
from typing import Optional, Dict, Any, List
from django.http import JsonResponse

# 硬编码常量（来自API文档.md）
MAX_TOTAL_LENGTH = 8000    # FIM API总长度限制
MAX_INCLUDES = 10          # 最多10个include
MAX_FUNCTIONS = 5          # 最多5个函数签名
MAX_PROMPT_LENGTH = 4000   # prompt最大长度
MAX_SUFFIX_LENGTH = 4000   # suffix最大长度

# DeepSeek API配置
DEEPSEEK_API_URL = "https://api.deepseek.com/beta/completions"
DEEPSEEK_MODEL = "deepseek-chat"  # 使用deepseek-chat模型
DEFAULT_MAX_TOKENS = 100
DEFAULT_TIMEOUT = 10  # 秒


def call_fim_api(prompt: str, suffix: str, includes: List[str], 
                 other_functions: List[Dict[str, Any]], max_tokens: int) -> Optional[Dict[str, str]]:
    """调用DeepSeek FIM API获取补全建议（带完整优化）"""
    
    # ========== 1. 数据验证 ==========
    if not isinstance(prompt, str) or not isinstance(suffix, str):
        raise ValueError("prompt和suffix必须是字符串")
    
    if includes and not isinstance(includes, list):
        raise ValueError("includes必须是数组")
    
    if other_functions and not isinstance(other_functions, list):
        raise ValueError("other_functions必须是数组")
    
    # 验证includes元素类型
    if includes:
        for i, inc in enumerate(includes):
            if not isinstance(inc, str):
                raise ValueError(f"includes[{i}]必须是字符串")
    
    # 验证other_functions元素类型
    if other_functions:
        for i, func in enumerate(other_functions):
            if not isinstance(func, dict):
                raise ValueError(f"other_functions[{i}]必须是对象")
            if 'name' not in func:
                func['name'] = f'function_{i}'
    
    # ========== 2. 构造优化的prompt ==========
    prompt_parts = []
    
    # 添加include语句（限制数量）
    if includes:
        limited_includes = includes[:MAX_INCLUDES]
        # 清理include语句
        cleaned_includes = [inc.strip() for inc in limited_includes if inc.strip()]
        if cleaned_includes:
            prompt_parts.extend(cleaned_includes)
    
    # 添加分隔符
    if prompt_parts and other_functions:
        prompt_parts.append("")
        prompt_parts.append("==========")
        prompt_parts.append("")
    
    # 添加其他函数签名（限制数量）
    if other_functions:
        limited_functions = other_functions[:MAX_FUNCTIONS]
        prompt_parts.append("// Available functions in this file:")
        for func in limited_functions:
            signature = func.get('signature', func.get('name', ''))
            if signature:
                prompt_parts.append(f"//   {signature}")
    
    # 添加分隔符（如果有其他函数）
    if prompt_parts and (includes or other_functions):
        prompt_parts.append("")
        prompt_parts.append("==========")
        prompt_parts.append("")
    
    # 添加当前代码（限制长度）
    trimmed_prompt = prompt[:MAX_PROMPT_LENGTH] if len(prompt) > MAX_PROMPT_LENGTH else prompt
    prompt_parts.append(trimmed_prompt)
    
    # 拼接完整prompt
    full_prompt = '\n'.join(prompt_parts)
    
    # ========== 3. 长度检查和调整 ==========
    total_length = len(full_prompt) + len(suffix)
    
    if total_length > MAX_TOTAL_LENGTH:
        # 优先保留prompt，截断suffix
        max_suffix_length = MAX_TOTAL_LENGTH - len(full_prompt)
        if max_suffix_length > 100:  # 至少保留100字符的suffix
            suffix = suffix[:max_suffix_length]
        else:
            # 如果suffix空间太小，截断prompt
            available_for_prompt = MAX_TOTAL_LENGTH - 200  # 为suffix保留200字符
            if available_for_prompt > 0:
                # 从后往前截断prompt，保留最重要的部分
                full_prompt = full_prompt[-available_for_prompt:]
                suffix = suffix[:200]
            else:
                # 极端情况：只保留最基本的内容
                full_prompt = trimmed_prompt[-500:]
                suffix = suffix[:500]
    
    # ========== 4. 调用DeepSeek FIM API ==========
    from . import DEEPSEEK_API_KEY
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": DEEPSEEK_MODEL,
        "prompt": full_prompt,
        "suffix": suffix,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
        
        # 检查HTTP状态码
        if response.status_code != 200:
            error_msg = f"LLM API返回错误: {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
            except Exception:
                pass
            raise Exception(error_msg)
        
        result = response.json()
        
        # ========== 5. 解析和清理响应 ==========
        suggestion = None
        
        if 'choices' not in result or not result['choices']:
            return suggestion
        
        choice = result['choices'][0]
        
        if 'text' not in choice:
            return suggestion
        
        text = choice['text'].strip()
        
        # 清理可能的markdown代码块标记
        text = text.replace('```cpp', '').replace('```python', '').replace('```c', '')
        text = text.replace('```', '').strip()
        
        # 过滤空建议
        if not text:
            return suggestion
        
        # 限制建议长度
        if len(text) > 500:
            text = text[:500]
        
        suggestion = {
            'text': text,
            'label': text[:30].replace('\n', ' ') + '...' if len(text) > 30 else text
        }
        
        return suggestion
    
    except requests.exceptions.Timeout:
        raise Exception("LLM API调用超时")
    except requests.exceptions.ConnectionError:
        raise Exception("无法连接到LLM API")
    except requests.exceptions.RequestException as e:
        raise Exception(f"LLM API调用失败: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("LLM API返回的JSON格式无效")
    except Exception as e:
        raise Exception(f"处理LLM API响应时发生错误: {str(e)}")