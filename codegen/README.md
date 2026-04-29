# VSCode Intelligent Code Completion Server

A Django-based code completion API server for VSCode plugin, supporting DeepSeek FIM API and multi-provider Chat API with RAG (Retrieval-Augmented Generation) enhancement.

## Features

- **FIM Mode**: Fill-in-the-middle code completion via DeepSeek API
- **Chat Mode**: Multi-provider chat completion (DeepSeek, OpenAI, Anthropic, Zhipu)
- **Graph-RAG Enhancement**: Hybrid graph + vector retrieval for superior code context
- **Code Knowledge Graph**: Extracts functions, classes, imports, calls, inheritance
- **Graph Traversal**: Multi-hop retrieval through call chains and dependencies
- **Project Isolation**: Each project has its own vector store and graph
- **Incremental Indexing**: Only update changed files, no full rebuild needed
- **Embedding Cache**: LRU cache for faster repeated queries
- **Similarity Threshold**: Filter out low-quality retrieval results

## Quick Start

```bash
# Install dependencies
pixi install

# Set API key (required)
export DEEPSEEK_API_KEY="your-api-key"

# Initialize database
pixi run python manage.py migrate

# Start server
pixi run python manage.py runserver

# Run tests (in another terminal)
pixi run python test_api.py
```

## API Endpoints

- `POST /api/v1/completion` - FIM code completion
- `POST /api/v1/chat` - Chat code completion with RAG support
- `GET /api/v1/models` - List available models and providers

### Chat API with Graph-RAG

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

## RAG Setup

### Index Your Project

```bash
# Incremental index (recommended)
pixi run python -m completion.rag.indexer index /path/to/project

# Full rebuild
pixi run python -m completion.rag.indexer index /path/to/project --full
```

### Multi-Project Support

```bash
# Index project A
pixi run python -m completion.rag.indexer index /path/to/project-a --project-path /path/to/project-a

# Index project B
pixi run python -m completion.rag.indexer index /path/to/project-b --project-path /path/to/project-b
```

### Manage Index

```bash
# Show stats
pixi run python -m completion.rag.indexer stats

# Search index
pixi run python -m completion.rag.indexer search "def handle_request"

# Clear index
pixi run python -m completion.rag.indexer clear
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | Yes | - | DeepSeek API key |
| `ZHIPU_API_KEY` | For zhipu | - | Zhipu API key |
| `OPENAI_API_KEY` | For openai | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | For anthropic | - | Anthropic API key |
| `RAG_ENABLED` | No | `true` | Enable RAG globally |
| `RAG_EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `RAG_EMBEDDING_CACHE_SIZE` | No | `1000` | Embedding cache size |

### RAG Parameters (in `completion/rag/config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CHUNK_SIZE` | 500 | Characters per chunk |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks |
| `DEFAULT_TOP_K` | 5 | Number of results to retrieve |
| `MAX_CONTEXT_CHUNKS` | 3 | Max chunks in context |
| `SIMILARITY_THRESHOLD` | 0.5 | Minimum similarity score |

## Project Structure

```
codegen/
├── api/                  # Django project config
├── completion/           # Main Django app
│   ├── views.py          # API handlers
│   ├── services.py       # DeepSeek FIM API
│   ├── chat_service.py   # Multi-provider chat API with RAG
│   ├── model_providers.py # Provider classes
│   ├── prompt_templates.py # Chat prompt building
│   └── rag/              # RAG / Graph-RAG module
│       ├── chunker.py       # Code chunking
│       ├── vector_store.py  # FAISS vector store with cache
│       ├── retriever.py     # Traditional vector retrieval
│       ├── graph_store.py   # NetworkX graph + vector hybrid
│       ├── graph_retriever.py # Graph traversal retrieval
│       ├── code_parser.py   # AST + regex code parser
│       ├── indexer.py       # CLI tool for indexing
│       └── config.py        # RAG configuration
├── manage.py
└── test_api.py           # Test suite
```

## Prompt Concatenation Locations

The system constructs prompts at multiple layers:

1. **`services.py:48-85`** - FIM mode: includes + other_functions + prompt + suffix
2. **`chat_service.py:70-77`** - Chat mode: RAG augmentation + prompt building
3. **`chat_service.py:88-115`** - `_augment_prompt_with_rag()`: `// Relevant code...` + rag_context + `// Current code...` + prompt
4. **`prompt_templates.py:8-21`** - Template: `{includes}` + `{functions}` + `{prompt}▌{suffix}`
5. **`retriever.py:176-180`** - RAG context formatting with source paths

## Documentation

- [API文档.md](API文档.md) - Complete API specification (Chinese)
- [部署指南.md](部署指南.md) - Deployment guide with RAG setup (Chinese)
- [AGENTS.md](AGENTS.md) - Development guide

## License

MIT
