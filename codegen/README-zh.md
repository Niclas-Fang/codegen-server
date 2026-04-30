# VSCode 智能代码补全服务器

基于 Django 的代码补全 API 服务器，为 VSCode 插件提供后端服务。支持 DeepSeek FIM API 和多提供商 Chat API，集成 RAG（检索增强生成）和 Graph-RAG 提升补全质量。

## 功能特性

- **FIM 模式**：通过 DeepSeek API 实现 Fill-in-the-Middle 代码补全
- **Chat 模式**：多提供商聊天补全（DeepSeek、OpenAI、Anthropic、智谱AI）
- **Graph-RAG 增强**：图 + 向量混合检索，提供更精准的代码上下文
- **LSP 协议支持**：使用 clangd（或 ccls 作为回退）进行精确的 C/C++ AST 提取
- **代码知识图谱**：通过 LSP 提取函数、类、导入、调用、继承关系
- **图遍历检索**：沿调用链和依赖关系进行多跳检索
- **项目隔离**：每个项目拥有独立的向量存储和知识图谱
- **增量索引**：基于文件修改时间（mtime），仅更新变更文件
- **Embedding 缓存**：LRU 缓存加速重复查询

## 快速开始

### 环境要求

- Python 3.14.1+
- [Pixi](https://pixi.sh/latest/) 包管理器
- 至少一个 API 密钥: `DEEPSEEK_API_KEY`、`ZHIPU_API_KEY`、`OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`

```bash
# 安装依赖
pixi install

# 设置 API 密钥（必填）
export DEEPSEEK_API_KEY="your-api-key"

# 初始化数据库
pixi run python manage.py migrate

# 启动服务
pixi run python manage.py runserver

# 运行测试（另一个终端）
pixi run python test_api.py
```

## API 接口

- `POST /api/v1/completion` - FIM 代码补全
- `POST /api/v1/chat` - Chat 代码补全（支持 RAG）
- `GET /api/v1/models` - 获取可用模型和提供商列表

### FIM 补全示例

```bash
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
    "suffix": "\n    return 0;\n}",
    "max_tokens": 100
  }'
```

### Chat 补全（Graph-RAG）示例

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "prompt": "def hello():",
      "suffix": ""
    },
    "use_graph_rag": true,
    "project_path": "/path/to/your/project"
  }'
```

## RAG 配置

### 索引项目

```bash
# 增量索引（推荐）
pixi run python -m completion.rag.indexer index /path/to/project

# 全量重建
pixi run python -m completion.rag.indexer index /path/to/project --full
```

### 多项目支持

```bash
# 索引项目 A
pixi run python -m completion.rag.indexer index /path/to/project-a --project-path /path/to/project-a

# 索引项目 B
pixi run python -m completion.rag.indexer index /path/to/project-b --project-path /path/to/project-b
```

### 索引管理

```bash
# 查看统计
pixi run python -m completion.rag.indexer stats --project-path /path/to/project

# 搜索索引
pixi run python -m completion.rag.indexer search "def handle_request"

# 清除索引
pixi run python -m completion.rag.indexer clear --project-path /path/to/project
```

### Language Server (LSP) 设置

Graph-RAG 使用 Language Server 进行精确的 C/C++ AST 提取。如果 clangd 不可用，自动回退到 ccls（GCC 兼容）。全部不可用时使用正则解析。

**安装 clangd（推荐）：**
```bash
# Ubuntu/Debian
sudo apt-get install clangd

# macOS
brew install llvm
```

**安装 ccls（回退，GCC 兼容）：**
```bash
# Ubuntu/Debian
sudo apt-get install ccls

# macOS
brew install ccls
```

**生成 compile_commands.json（可选，提高 LSP 准确性）：**
```bash
# 使用 CMake
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON .

# 使用 Bear
bear -- make
```

**配置 LSP 回退：**
```bash
export LSP_COMMAND="clangd"
export LSP_FALLBACK_COMMANDS="clangd,ccls"  # 按顺序尝试
```

## 配置

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | 是 | - | DeepSeek API 密钥 |
| `ZHIPU_API_KEY` | 使用智谱AI时 | - | 智谱AI API 密钥 |
| `OPENAI_API_KEY` | 使用 OpenAI 时 | - | OpenAI API 密钥 |
| `ANTHROPIC_API_KEY` | 使用 Anthropic 时 | - | Anthropic API 密钥 |
| `RAG_ENABLED` | 否 | `true` | 全局启用/禁用 RAG |
| `GRAPH_RAG_ENABLED` | 否 | `true` | 全局启用/禁用 Graph-RAG |
| `RAG_EMBEDDING_MODEL` | 否 | `all-MiniLM-L6-v2` | 嵌入模型 |
| `RAG_EMBEDDING_CACHE_SIZE` | 否 | `1000` | Embedding 缓存大小 |
| `LSP_COMMAND` | 否 | `clangd` | Language Server 命令 |
| `LSP_FALLBACK_COMMANDS` | 否 | `clangd,ccls` | LSP 回退命令列表（逗号分隔） |
| `LSP_ARGS` | 否 | - | Language Server 额外参数 |

### RAG 参数（`completion/rag/config.py`）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CHUNK_SIZE` | 500 | 每个 chunk 的字符数 |
| `CHUNK_OVERLAP` | 50 | chunk 之间的重叠字符数 |
| `DEFAULT_TOP_K` | 5 | 检索结果数量 |
| `MAX_CONTEXT_CHUNKS` | 3 | 上下文中最多包含的 chunk 数 |
| `SIMILARITY_THRESHOLD` | 0.5 | 最小相似度阈值 |
| `GRAPH_HOPS` | 2 | 图遍历跳数 |

## 项目结构

```
codegen/
├── api/                  # Django 项目配置
├── completion/           # 主 Django 应用
│   ├── views.py          # API 处理
│   ├── services.py       # DeepSeek FIM API
│   ├── chat_service.py   # 多提供商 Chat API（含 RAG）
│   ├── model_providers.py # 提供商抽象类
│   ├── prompt_templates.py # Chat prompt 构建
│   └── rag/              # RAG / Graph-RAG 模块
│       ├── chunker.py       # 代码分块
│       ├── vector_store.py  # FAISS 向量存储（含缓存）
│       ├── retriever.py     # 传统向量检索
│       ├── graph_store.py   # NetworkX 图 + 向量混合存储
│       ├── graph_retriever.py # 图遍历检索
│       ├── code_parser.py   # LSP + 正则代码解析
│       ├── lsp_client.py    # Language Server Protocol 客户端
│       ├── indexer.py       # CLI 索引工具
│       └── config.py        # RAG 配置
├── manage.py
└── test_api.py           # 测试套件
```

## 生产部署

### 环境变量配置

```bash
DEEPSEEK_API_KEY=your-api-key
DEBUG=False
SECRET_KEY=<随机字符串>
ALLOWED_HOSTS=your-domain.com
RAG_ENABLED=true
```

### 使用 Gunicorn

```bash
pixi add --pypi gunicorn
pixi run gunicorn api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
```

## 常见问题

### 服务无法启动

```bash
echo $DEEPSEEK_API_KEY          # 检查环境变量
netstat -tlnp | grep :8000      # 检查端口
pixi run python manage.py check  # Django 配置检查
```

### API 返回 500 错误

```bash
# 检查 API 密钥是否有效
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/beta/models
```

### RAG 检索不生效

```bash
pixi run python -m completion.rag.indexer stats   # 检查索引是否存在
pixi run python -m completion.rag.indexer index <代码目录>  # 构建索引
# 确保 project_path 与索引时使用的 --project-path 一致
```

## 安全建议

1. **API 密钥安全**：不要将 API 密钥提交到版本控制，使用环境变量管理
2. **访问控制**：生产环境中限制 `ALLOWED_HOSTS`
3. **CORS 配置**：生产环境中指定具体域名，不要使用 `*`

## 相关文档

- [API文档.md](API文档.md) - 完整 API 规范
- [README.md](README.md) - 英文版 README
- [AGENTS.md](AGENTS.md) - AI 代理开发指南
- [CLAUDE.md](CLAUDE.md) - Claude Code 项目说明
- [examples/](examples/) - FIM 和 RAG 使用示例

## License

MIT
