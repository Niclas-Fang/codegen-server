# VSCode智能编码助手插件 API文档

## 基本信息

- **API版本**: v2.0
- **基础URL**: `http://localhost:8000/api/v1`
- **内容类型**: `application/json`
- **认证方式**: 暂无（MVP版本）

---

## 接口列表

| 接口名称 | 方法 | 路径 | 说明 |
|---------|------|------|------|
| 代码补全 (FIM) | POST | `/completion` | 使用 FIM 模式获取代码补全建议 |
| 代码补全 (Chat) | POST | `/chat` | 使用 Chat 模式获取代码补全建议 |
| 模型列表 | GET | `/models` | 获取支持的模型和提供者列表 |

---

## 1. 模型列表接口

### 1.1 接口描述

获取所有支持的模型提供者和模型列表。

### 1.2 请求

**URL**: `/api/v1/models`

**方法**: `GET`

### 1.3 响应

```json
{
  "success": true,
  "providers": ["deepseek", "openai", "anthropic", "zhipu"],
  "models": {
    "deepseek": {
      "models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
      "default": "deepseek-chat",
      "description": {
        "deepseek-v4-pro": "DeepSeek-V4 Pro，1.6T MoE，1M 上下文",
        "deepseek-v4-flash": "DeepSeek-V4 Flash，284B MoE，高性价比",
        "deepseek-chat": "DeepSeek-V3.2 通用对话模型",
        "deepseek-reasoner": "DeepSeek-V3.2 推理模型"
      }
    },
    "openai": {
      "models": ["gpt-5.5", "gpt-5.4"],
      "default": "gpt-5.4"
    },
    "anthropic": {
      "models": ["claude-opus-4-7-20260416", "claude-sonnet-4-6-20250217"],
      "default": "claude-sonnet-4-6-20250217"
    },
    "zhipu": {
      "models": ["glm-5.1", "glm-5"],
      "default": "glm-5"
    }
  }
}
```

---

## 2. 代码补全接口 (FIM 模式)

### 2.1 接口描述

根据当前代码上下文和光标位置，返回智能代码补全建议。

### 2.2 请求

**URL**: `/api/v1/completion`

**方法**: `POST`

**请求头**:
```
Content-Type: application/json
```

**请求体参数**:

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| prompt | string | 是 | 光标之前的代码（FIM格式） | `"int main() {\n    int a = 10;\n    int b = 20;\n    "` |
| suffix | string | 是 | 光标之后的代码（FIM格式） | `"\n    return 0;\n}"` |
| includes | array | 否 | include语句列表，后端会添加到prompt开头 | `["#include <iostream>", "#include <vector>"]` |
| other_functions | array | 否 | 同文件的其他函数签名，帮助模型理解可调用的函数 | `[{"name": "calculate_sum", "signature": "int calculate_sum(int a, int b)"}]` |
| max_tokens | integer | 否 | 最大生成token数，默认100 | `100` |

**请求示例**:
```json
{
  "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
  "suffix": "\n    return 0;\n}",
  "includes": [
    "#include <iostream>",
    "#include <vector>"
  ],
  "other_functions": [
    {
      "name": "calculate_sum",
      "signature": "int calculate_sum(int a, int b)",
      "return_type": "int",
      "parameters": [
        {"name": "a", "type": "int"},
        {"name": "b", "type": "int"}
      ]
    },
    {
      "name": "calculate_product",
      "signature": "int calculate_product(int a, int b)",
      "return_type": "int",
      "parameters": [
        {"name": "a", "type": "int"},
        {"name": "b", "type": "int"}
      ]
    }
  ],
  "max_tokens": 100
}
```

### 2.3 响应

#### 2.3.1 成功响应

**状态码**: `200 OK`

**响应体结构**:

```json
{
  "success": true,
  "suggestion": {
    "text": "int sum = a + b;",
    "label": "sum = a + b"
  }
}
```

#### 2.3.2 字段说明

**顶层字段**:

| 字段名 | 类型 | 说明 |
|-------|------|------|
| success | boolean | 请求是否成功 |
| suggestion | object | 补全建议 |

**suggestion 对象字段**:

| 字段名 | 类型 | 说明 |
|-------|------|------|
| text | string | 插入到编辑器中的完整代码 |
| label | string | 在补全列表中显示的简短标签 |



### 2.4 错误响应

**状态码**: `400 Bad Request` 或 `500 Internal Server Error`

```json
{
  "success": false,
  "error_code": "INVALID_PARAMS",
  "error": "错误描述信息"
}
```

**错误码定义**:

| 错误码 | HTTP状态码 | 说明 |
|-------|-----------|------|
| INVALID_PARAMS | 400 | 请求参数缺失或格式错误 |
| INVALID_JSON | 400 | JSON格式无效 |
| API_TIMEOUT | 500 | LLM API调用超时 |
| API_CONNECTION_ERROR | 500 | 无法连接到LLM API |
| API_ERROR | 500 | LLM API返回错误 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 4. RAG 配置说明

### 4.1 什么是 Graph-RAG？

Graph-RAG（Graph-based Retrieval-Augmented Generation）是传统 RAG 的增强版本。它不仅使用语义相似度检索代码片段，还构建了代码的**知识图谱**，通过图遍历发现相关代码：

- **传统 RAG**：只找语义相似的代码（"这个函数看起来像你写的"）
- **Graph-RAG**：找语义相似 + 调用关系 + 继承关系 + 导入依赖的代码（"这个函数调用了你写的函数，所以可能相关"）

### 4.2 Graph-RAG 架构

```
代码文件 → AST解析 → 实体（函数/类/导入）
                    ↓
            关系（调用/继承/包含）
                    ↓
            知识图谱(NetworkX) + 向量库(FAISS)
                    ↓
            检索：语义搜索种子 → 图遍历扩展 → 混合排序
```

### 4.3 RAG 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `use_rag` | `true` | 请求级开关，控制是否启用RAG |
| `use_graph_rag` | `true` | 请求级开关，控制是否启用Graph-RAG（优先于传统RAG） |
| `project_path` | `""` | 项目路径，不同项目使用独立的向量库和图 |
| `RAG_ENABLED` | `true` | 全局环境变量开关 |
| `GRAPH_RAG_ENABLED` | `true` | 全局Graph-RAG开关 |
| `RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | 嵌入模型 |
| `SIMILARITY_THRESHOLD` | `0.5` | 相似度阈值 |
| `GRAPH_HOPS` | `2` | 图遍历跳数 |
| `LSP_COMMAND` | `clangd` | LSP 命令，用于代码解析 |
| `LSP_FALLBACK_COMMANDS` | `clangd,ccls` | LSP 回退命令列表，逗号分隔，按顺序尝试启动 |

### 4.4 RAG 使用流程

1. **首次索引**：`indexer` 同时构建向量库 + 代码知识图谱；自动检测可用的 LSP（clangd → ccls 按序回退）
2. **增量更新**：代码变更后重新索引，基于文件修改时间（mtime）自动检测变更文件
3. **请求时检索**：Chat API 优先使用 Graph-RAG，失败时回退到传统 RAG

### 4.5 项目隔离

不同 `project_path` 使用完全独立的存储：
- 向量库：`rag_data/vector_stores/{project_name}_{hash}/code_index.faiss`
- 知识图谱：`rag_data/vector_stores/{project_name}_{hash}/code_graph.json`
- 元数据：`rag_data/vector_stores/{project_name}_{hash}/metadata.json`

### 4.6 includes 自动提取

如果请求中未提供 `includes` 字段，后端会自动从 `prompt` 中提取：
- Python: `import xxx`, `from xxx import yyy`
- C/C++: `#include <xxx>`
- C#: `using xxx;`

**错误示例**:

```json
// 参数错误
{
  "success": false,
  "error_code": "INVALID_PARAMS",
  "error": "缺少必填参数: prompt"
}

// JSON格式错误
{
  "success": false,
  "error_code": "INVALID_JSON",
  "error": "无效的JSON格式"
}

// LLM API超时
{
  "success": false,
  "error_code": "API_TIMEOUT",
  "error": "LLM API调用超时"
}

// LLM API连接错误
{
  "success": false,
  "error_code": "API_CONNECTION_ERROR",
  "error": "无法连接到LLM API"
}

// LLM API错误
{
  "success": false,
  "error_code": "API_ERROR",
  "error": "LLM API返回错误: 500 - rate limit exceeded"
}

// 服务器内部错误
{
  "success": false,
  "error_code": "INTERNAL_ERROR",
  "error": "服务器内部错误"
}
```

---

## 3. 代码补全接口 (Chat 模式)

### 3.1 接口描述

使用 Chat 模式（基于提示词工程）获取代码补全建议。支持多种模型提供者。

### 3.2 请求

**URL**: `/api/v1/chat`

**方法**: `POST`

**请求头**:
```
Content-Type: application/json
```

**请求体参数**:

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| context | object | 是 | 代码上下文 | 见下方 |
| model | string | 否 | 模型名称，默认使用 provider 的默认模型 | `"glm-4-flash"` |
| provider | string | 否 | 模型提供者，默认 `zhipu` | `"zhipu"` |
| max_tokens | integer | 否 | 最大生成token数，默认1000 | `1000` |
| use_rag | boolean | 否 | 是否启用RAG代码检索增强，默认 `true` | `true` |
| use_graph_rag | boolean | 否 | 是否启用Graph-RAG（优先于传统RAG），默认 `true` | `true` |
| project_path | string | 否 | 项目绝对路径，用于RAG向量库隔离和代码检索 | `"/home/user/myproject"` |

**context 对象字段**:

| 字段名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| prompt | string | 是 | 光标之前的代码 |
| suffix | string | 是 | 光标之后的代码 |
| includes | array | 否 | include/import语句列表（不传则自动从prompt提取） |
| other_functions | array | 否 | 同文件的其他函数签名 |

**请求示例**:
```json
{
  "context": {
    "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
    "suffix": "\n    return 0;\n}",
    "other_functions": [
      {"name": "calculate_sum", "signature": "int calculate_sum(int a, int b)"}
    ]
  },
  "model": "glm-4-flash",
  "provider": "zhipu",
  "max_tokens": 1000,
  "use_rag": true,
  "project_path": "/home/user/myproject"
}
```

### 3.3 响应

**成功响应**:
```json
{
  "success": true,
  "response": {
    "text": "int sum = calculate_sum(a, b);\nstd::cout << sum << std::endl;",
    "model": "glm-4-flash",
    "provider": "zhipu"
  }
}
```

### 3.4 支持的模型提供者

| Provider | 环境变量 | 默认模型 | 说明 |
|----------|----------|----------|------|
| `zhipu` | `ZHIPU_API_KEY` | glm-5 | 智谱AI，推荐使用 |
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-chat | DeepSeek |
| `openai` | `OPENAI_API_KEY` | gpt-5.4 | OpenAI |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-sonnet-4-6-20250217 | Anthropic Claude |

### 3.5 各提供者支持的模型

**智谱AI (zhipu)**:
| 模型 | 说明 |
|------|------|
| glm-5.1 | GLM-5.1 全自治 Agent，8h 自主工作，SWE-Bench Pro 58.4 |
| glm-5 | GLM-5 旗舰，744B/40B MoE，200K 上下文，开源 SOTA |

**DeepSeek**:
| 模型 | 说明 |
|------|------|
| deepseek-v4-pro | DeepSeek-V4 Pro，1.6T MoE，1M 上下文，旗舰推理与编码 |
| deepseek-v4-flash | DeepSeek-V4 Flash，284B MoE，1M 上下文，高性价比 |
| deepseek-chat | DeepSeek-V3.2 通用对话，128K 上下文 |
| deepseek-reasoner | DeepSeek-V3.2 推理模型 |

**OpenAI**:
| 模型 | 说明 |
|------|------|
| gpt-5.5 | GPT-5.5 旗舰推理与编码模型，1M 上下文，82.7% Terminal-Bench |
| gpt-5.4 | GPT-5.4 高性能推理模型，1M 上下文 |

**Anthropic**:
| 模型 | 说明 |
|------|------|
| claude-opus-4-7-20260416 | Claude Opus 4.7 旗舰，87.6% SWE-bench，1M 上下文 |
| claude-sonnet-4-6-20250217 | Claude Sonnet 4.6 主力，最佳性价比 |

---

## 4. 前端对接示例

### 4.1 TypeScript对接代码

```typescript
import * as vscode from 'vscode';

interface CompletionRequest {
    prompt: string;
    suffix: string;
    includes?: string[];
    other_functions?: Array<{
        name: string;
        signature?: string;
        return_type?: string;
        parameters?: Array<{name: string; type: string}>;
    }>;
    max_tokens?: number;
}

interface CompletionSuggestion {
    text: string;
    label: string;
}

interface CompletionResponse {
    success: boolean;
    suggestion?: CompletionSuggestion;
    error_code?: string;
    error?: string;
}

class CodeCompletionProvider implements vscode.CompletionItemProvider {
    private apiUrl = 'http://localhost:8000/api/v1/completion';

    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        try {
            // 使用LSP提取上下文并构造FIM格式
            const fimContext = await this.extractFIMContext(document, position);

            // 构造请求
            const request: CompletionRequest = {
                prompt: fimContext.prompt,
                suffix: fimContext.suffix,
                includes: fimContext.includes,
                other_functions: fimContext.other_functions,
                max_tokens: 100
            };

            // 调用API
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(request)
            });

            const data: CompletionResponse = await response.json();

            if (!data.success || !data.suggestion) {
                return [];
            }

            // 转换为VSCode CompletionItem
            const item = new vscode.CompletionItem(data.suggestion.label);
            item.insertText = data.suggestion.text;

            return [item];

        } catch (error) {
            console.error('Completion error:', error);
            return [];
        }
    }

    private async extractFIMContext(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<{
        prompt: string;
        suffix: string;
        includes: string[];
        other_functions: Array<{
            name: string;
            signature: string;
            return_type?: string;
            parameters?: Array<{name: string; type: string}>;
        }>;
    }> {
        const text = document.getText();

        // 1. 提取include语句
        const includes = text.match(/^#include\s+[<"][^>"]+[>"]/gm) || [];

        // 2. 获取所有函数定义
        const symbols = await vscode.commands.executeCommand<vscode.SymbolInformation[]>(
            'vscode.executeDocumentSymbolProvider',
            document.uri
        );

        // 3. 找到当前函数
        let functionRange: vscode.Range | undefined;
        let currentFunction: vscode.SymbolInformation | undefined;

        if (symbols) {
            currentFunction = symbols.find(func => {
                const range = func.location.range;
                return position.line >= range.start.line && position.line <= range.end.line;
            });
            if (currentFunction) {
                functionRange = currentFunction.location.range;
            }
        }

        // 4. 提取其他函数（排除当前函数）
        const otherFunctions = symbols
            ?.filter(func =>
                func !== currentFunction &&
                func.kind === vscode.SymbolKind.Function
            )
            .map(func => ({
                name: func.name,
                signature: func.name + '(...)'
            })) || [];

        // 5. 构造FIM格式的prompt和suffix
        let prompt = '';
        let suffix = '';

        if (functionRange) {
            // 提取函数体
            const functionText = document.getText(functionRange);

            // 计算光标在函数体内的偏移
            const functionStartOffset = document.offsetAt(functionRange.start);
            const cursorOffset = document.offsetAt(position);
            const cursorOffsetInFunction = cursorOffset - functionStartOffset;

            // 构造prompt：函数体前半部分（不包含include）
            prompt = functionText.substring(0, cursorOffsetInFunction);

            // 构造suffix：函数体后半部分
            suffix = functionText.substring(cursorOffsetInFunction);
        } else {
            // 如果不在函数内，使用整个文档
            const cursorOffset = document.offsetAt(position);
            prompt = text.substring(0, cursorOffset);
            suffix = text.substring(cursorOffset);
        }

        return {
            prompt,
            suffix,
            includes,
            other_functions: otherFunctions
        };
};
}

// 注册补全提供者
export function activate(context: vscode.ExtensionContext) {
    const provider = vscode.languages.registerCompletionItemProvider(
        { scheme: 'file', language: 'cpp' },
        new CodeCompletionProvider()
    );

    context.subscriptions.push(provider);
}
```

---

## 5. 后端实现示例

### 5.1 Django视图实现

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import requests

@csrf_exempt
@require_http_methods(["POST"])
def completion(request):
    """代码补全接口"""
    try:
        # 解析请求
        data = json.loads(request.body)

        # 验证必填参数
        required_fields = ['prompt', 'suffix']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error_code': 'INVALID_PARAMS',
                    'error': f'缺少必填参数: {field}'
                }, status=400)

        prompt = data['prompt']
        suffix = data['suffix']
        includes = data.get('includes', [])
        other_functions = data.get('other_functions', [])
        max_tokens = data.get('max_tokens', 100)

        # 调用DeepSeek FIM API（后端组合include、other_functions和prompt）
        suggestion = call_fim_api(prompt, suffix, includes, other_functions, max_tokens)

        # 构造响应
        return JsonResponse({
            'success': True,
            'suggestion': suggestion
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error_code': 'INVALID_JSON',
            'error': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        error_msg = str(e)
        error_code = 'INTERNAL_ERROR'

        # 根据异常类型设置错误码
        if 'timeout' in error_msg.lower():
            error_code = 'API_TIMEOUT'
        elif 'connection' in error_msg.lower():
            error_code = 'API_CONNECTION_ERROR'
        elif 'LLM API' in error_msg:
            error_code = 'API_ERROR'

        return JsonResponse({
            'success': False,
            'error_code': error_code,
            'error': error_msg
        }, status=500)

def call_fim_api(prompt, suffix, includes, other_functions, max_tokens):
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

    # ========== 2. 长度限制配置 ==========
    MAX_TOTAL_LENGTH = 8000  # FIM API总长度限制
    MAX_INCLUDES = 10        # 最多10个include
    MAX_FUNCTIONS = 5        # 最多5个函数签名
    MAX_PROMPT_LENGTH = 4000 # prompt最大长度
    MAX_SUFFIX_LENGTH = 4000 # suffix最大长度

    # ========== 3. 构造优化的prompt ==========
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

    # ========== 4. 长度检查和调整 ==========
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

    # ========== 5. 调用DeepSeek FIM API ==========
    api_url = "https://api.deepseek.com/beta/completions"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-coder",
        "prompt": full_prompt,
        "suffix": suffix,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)

        # 检查HTTP状态码
        if response.status_code != 200:
            error_msg = f"LLM API返回错误: {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
            except:
                pass
            raise Exception(error_msg)

        result = response.json()

        # ========== 6. 解析和清理响应 ==========
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
```

---

## 6. 测试用例

### 6.1 测试方法说明

由于LLM具有不确定性，补全结果可能每次不同，因此不能使用精确匹配的测试方法。建议采用以下测试策略：

#### 6.1.1 模糊匹配测试
- 检查返回的代码语法是否正确
- 检查变量名是否在上下文中存在
- 检查类型是否匹配

#### 6.1.2 功能性测试
- 提供明确的场景（如"计算两个数的和"）
- 检查补全建议是否完成了预期功能
- 允许多种实现方式

#### 6.1.3 人工审核测试集
- 准备一批典型的代码补全场景
- 人工评估补全建议的质量（相关性、准确性、可用性）
- 评分标准：完全正确/部分正确/不相关/错误

#### 6.1.4 集成测试
- 测试API的整体流程（请求→响应→格式）
- 测试错误处理（参数缺失、格式错误等）
- 测试边界情况（空输入、超长输入）

#### 6.1.5 性能测试
- 响应时间是否在可接受范围内
- 并发请求的处理能力

### 6.2 C++补全测试

**请求**:
```json
{
  "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
  "suffix": "\n    return 0;\n}",
  "includes": [
    "#include <iostream>",
    "#include <vector>"
  ],
  "other_functions": [
    {
      "name": "calculate_sum",
      "signature": "int calculate_sum(int a, int b)"
    },
    {
      "name": "calculate_product",
      "signature": "int calculate_product(int a, int b)"
    }
  ]
}
```

**预期响应**（模糊匹配标准）:
```json
{
  "success": true,
  "suggestion": {
    "text": "int sum = a + b;",
    "label": "sum = a + b"
  }
}
```

**验证标准**：
- `success` 必须为 `true`
- `suggestion` 对象存在
- `text` 字段包含有效的C++代码
- 建议内容与上下文相关（计算或输出操作）
- 语法正确，变量名 `a` 和 `b` 在建议中被使用

---

## 7. 前端上下文提取策略

### 5.1 为什么由前端提取上下文？

由前端（VSCode插件）提取上下文有以下优势：

1. **避免line不一致问题**：前端提取后直接计算偏移，后端无需再次解析
2. **利用LSP能力**：VSCode提供强大的LSP支持，可以准确获取符号信息
3. **减少后端复杂度**：后端无需实现复杂的代码解析逻辑
4. **提高准确性**：LSP提供的符号信息比规则匹配更准确
5. **减少数据传输**：只发送必要的上下文信息，减少网络传输

### 5.2 前端提取策略

前端使用VSCode的LSP能力提取以下信息：

#### 策略1：提取Include语句
- 使用正则表达式匹配`#include`语句
- 作为独立的`includes`字段发送给后端

#### 策略2：获取当前函数信息
- 使用`vscode.executeDocumentSymbolProvider`获取文档符号
- 找到包含光标位置的函数
- 提取函数体并构造FIM格式的prompt和suffix

#### 策略3：提取其他函数
- 获取同文件中的其他函数定义
- 提取函数签名作为`other_functions`字段
- 帮助模型理解可调用的函数

#### 策略4：构造FIM格式
- **prompt**：函数体中光标之前的代码（不包含include）
- **suffix**：函数体中光标之后的代码
- **includes**：include语句列表
- **other_functions**：其他函数签名列表

### 5.3 上下文示例

**原始代码**：
```cpp
#include <iostream>
#include <vector>
using namespace std;

int calculate_sum(int a, int b) {
    return a + b;
}

int calculate_product(int a, int b) {
    return a * b;
}

int main() {
    int a = 10;
    int b = 20;
    // <光标在这里>
    return 0;
}
```

**前端构造的请求**：
```json
{
  "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
  "suffix": "return 0;\n}",
  "includes": [
    "#include <iostream>",
    "#include <vector>"
  ],
  "other_functions": [
    {
      "name": "calculate_sum",
      "signature": "int calculate_sum(int a, int b)"
    },
    {
      "name": "calculate_product",
      "signature": "int calculate_product(int a, int b)"
    }
  ]
}
```

**后端构造的完整prompt**：
```
#include <iostream>
#include <vector>

==========
// Available functions in this file:
//   int calculate_sum(int a, int b)
//   int calculate_product(int a, int b)
==========

int main() {
    int a = 10;
    int b = 20;
```

---

## 8. FIM API说明

### 6.1 什么是FIM API？

FIM（Fill-In-Middle）是DeepSeek专门为代码补全设计的API，它允许在代码中间插入内容，而不是只在末尾补全。

### 6.2 FIM API的优势

| 特性 | 普通Completion API | FIM API |
|------|-------------------|---------|
| **补全位置** | 只能在末尾 | 可以在代码中间任意位置 |
| **上下文理解** | 单向（前缀） | 双向（前缀+后缀） |
| **准确性** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **适用场景** | 续写代码 | 代码补全、填空 |

### 6.3 FIM API格式

FIM API使用`prompt`和`suffix`两个参数：

```python
# prompt: 光标之前的代码
prompt = """
#include <iostream>
int main() {
    int a = 10;
    int b = 20;
"""

# suffix: 光标之后的代码
suffix = """
    return 0;
}
"""

# API调用
response = deepseek.fim.completions(
    model="deepseek-chat",
    prompt=prompt,
    suffix=suffix
)
```

### 6.4 为什么使用FIM API？

1. **更准确**：同时考虑前缀和后缀，理解更全面
2. **更符合补全场景**：代码补全通常是在中间插入，不是续写
3. **DeepSeek优化**：DeepSeek专门为代码补全优化了FIM模型
4. **更好的上下文理解**：可以理解函数的返回值、后续代码的需求等

---

## 9. 部署说明

### 7.1 环境要求

**后端**：
- Python 3.14.1+
- Django 6.0+
- requests 库

**前端**：
- Node.js 16+
- VSCode Extension API

### 7.2 后端部署

1. **安装依赖**：
```bash
pip install django requests
```

2. **配置环境变量**：
```bash
# 智谱AI (推荐)
export ZHIPU_API_KEY="your-zhipu-api-key"

# DeepSeek
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

3. **启动Django服务器**：
```bash
python manage.py runserver 8000
```

### 7.3 前端部署

1. **安装依赖**：
```bash
npm install
```

2. **打包插件**：
```bash
npm run package
```

3. **在VSCode中安装**：
   - 打开VSCode
   - 按 `Ctrl+Shift+P` 打开命令面板
   - 输入 `Install from VSIX`
   - 选择打包后的 `.vsix` 文件

### 7.4 配置说明

**后端配置**：
- API URL：默认 `http://localhost:8000/api/v1/completion`
- DeepSeek API Key：通过环境变量 `DEEPSEEK_API_KEY` 配置
- DeepSeek Base URL：默认 `https://api.deepseek.com/beta`

**前端配置**：
- 后端URL：在 `extension.ts` 中修改 `apiUrl`
- 支持的语言：默认只支持 C/C++

### 7.5 常见问题 (FAQ)

**Q: 后端启动失败怎么办？**
A: 检查端口8000是否被占用，或修改Django配置使用其他端口。

**Q: 补全没有响应？**
A: 检查：
1. 后端服务是否正常运行
2. DeepSeek API Key是否正确配置
3. 网络连接是否正常

**Q: 如何查看日志？**
A: 后端日志在Django控制台输出，前端日志在VSCode开发者工具中查看（`Ctrl+Shift+I`）。

**Q: 支持其他语言吗？**
A: 当前MVP版本只支持C/C++，未来版本会支持更多语言。

**Q: API调用失败怎么办？**
A: 查看错误码（error_code）：
- `API_TIMEOUT`: 网络超时，检查网络连接
- `API_CONNECTION_ERROR`: 无法连接到DeepSeek API
- `API_ERROR`: API返回错误，检查API Key和使用额度

---

## 10. 注意事项

1. **超时设置**：LLM API调用可能较慢，建议设置合理的超时时间（5-10秒）
2. **错误重试**：对于临时性错误，可以实现重试机制
3. **缓存机制**：对于相同的请求，可以缓存结果
4. **限流保护**：防止API被滥用
5. **日志记录**：记录所有请求和响应，便于调试

---

## 11. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v3.1 | 2026-05-01 | LSP 回退机制：自动检测 clangd/ccls，支持 LSP_FALLBACK_COMMANDS 配置；增量索引基于 mtime 精确检测；代码解析性能优化 |
| v3.0 | 2026-04-29 | Graph-RAG：新增代码知识图谱（NetworkX）、AST代码解析、图遍历检索、混合语义+图检索、use_graph_rag参数 |
| v2.1 | 2026-04-26 | RAG增强：新增项目隔离向量库（project_path参数）、增量索引、相似度阈值（0.5）、Embedding缓存、includes自动提取、use_rag请求级开关 |
| v2.0 | 2026-02-22 | 重大更新：新增 Chat 模式端点 `/api/v1/chat`，支持多模型提供者（DeepSeek、OpenAI、Anthropic、智谱AI），添加模型列表端点 `/api/v1/models`，支持模型名称验证 |
| v1.13 | 2025-01-14 | 增强错误处理：添加错误码定义（INVALID_PARAMS、API_TIMEOUT等），优化后端prompt构造（使用更清晰的分隔符），添加完整的部署说明和FAQ |
| v1.12 | 2025-01-14 | 修复文档问题：更新错误响应示例、删除不支持的n参数、修复前端语法错误、删除重复内容、更新API URL为beta端点 |
| v1.11 | 2025-01-14 | 基于DeepSeek FIM API限制，将suggestions数组改为suggestion单个对象，并删除timestamp字段，进一步简化API |
| v1.10 | 2025-01-14 | 移除temperature字段，简化API参数，使用API默认值，符合MVP简化原则 |
| v1.9 | 2025-01-12 | 后端添加完整优化：数据验证、长度限制、清理空行、错误处理增强，提升稳定性和安全性 |
| v1.8 | 2025-01-12 | 添加includes和other_functions字段，帮助模型理解可用的库和函数，提升补全准确性 |
| v1.7 | 2025-01-12 | 前端直接构造FIM格式的prompt和suffix，后端简化为直接转发，前后端职责更清晰 |
| v1.6 | 2025-01-12 | 使用DeepSeek FIM API替代普通completion API，提升代码补全准确性 |
| v1.5 | 2025-01-12 | 前端使用LSP提取上下文，后端直接使用预处理后的上下文，解决line不一致问题 |
| v1.4 | 2025-01-12 | 删除健康检查接口，语言限制为C/C++ |
| v1.3 | 2025-01-12 | 简化错误响应格式，移除复杂的错误码结构 |
| v1.2 | 2025-01-12 | 使用line和character替代cursor_position，添加智能上下文提取策略 |
| v1.1 | 2025-01-12 | 简化API结构，只保留text和label字段 |
| v1.0 | 2025-01-12 | 初始版本，MVP基础功能 |