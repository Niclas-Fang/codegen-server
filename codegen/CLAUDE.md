# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses pixi.toml in parent directory)
pixi install                       # From /home/niclas/codegen-server/

# Database
pixi run python manage.py migrate
pixi run python manage.py makemigrations

# Run server
pixi run python manage.py runserver        # Default port 8000

# Run tests (REQUIRES running server)
pixi run python test_api.py                # All tests
pixi run python test_api.py test_name      # Single test

# RAG indexing
pixi run python -m completion.rag.indexer index /path/to/project
pixi run python -m completion.rag.indexer index /path/to/project --full
pixi run python -m completion.rag.indexer stats --project-path /path/to/project
pixi run python -m completion.rag.indexer search "<query>"
pixi run python -m completion.rag.indexer clear --project-path /path/to/project
```

All commands run from the `codegen/` directory.

## Architecture Overview

Django 6.0-based code completion API server for VSCode plugins. Two completion modes: FIM (Fill-in-Middle) via DeepSeek API and Chat (multi-provider) with RAG/Graph-RAG enhancement.

### Request Flow

```
POST /api/v1/completion → views.completion() → services.call_fim_api()           # FIM mode
POST /api/v1/chat       → views.chat()       → chat_service.call_chat_api()       # Chat mode + RAG
GET  /api/v1/models     → views.models()     → model_providers.get_all_models()
```

### Key Files

| Layer | File | Role |
|-------|------|------|
| Views | `completion/views.py` | API handlers with custom CORS decorator |
| FIM | `completion/services.py` | DeepSeek FIM API, prompt construction, length limits |
| Chat | `completion/chat_service.py` | Multi-provider chat, RAG/Graph-RAG augmentation |
| Providers | `completion/model_providers.py` | DeepSeek/OpenAI/Anthropic/Zhipu provider classes |
| Templates | `completion/prompt_templates.py` | Chat prompt building |
| Config | `completion/rag/config.py` | RAG params, env vars, supported extensions |

### RAG Module (`completion/rag/`)

Two-tier retrieval: traditional vector-only RAG and Graph-RAG.

- **Vector path**: `chunker.py` → `vector_store.py` (FAISS + sentence-transformers) → `retriever.py`
- **Graph path**: `code_parser.py` (LSP/regex) + `lsp_client.py` (clangd/ccls JSON-RPC) → `graph_store.py` (NetworkX) → `graph_retriever.py`
- **CLI**: `indexer.py` — incremental or full rebuild, stats, search, clear
- **LSP fallback**: tries commands from `LSP_FALLBACK_COMMANDS` (default: clangd,ccls) in order; uses regex parser if none available

Graph-RAG strategy: semantic search for seed nodes → BFS graph traversal (calls, inherits, imports, contains) → ranked fusion with relation-aware score decay.

### Per-Project Isolation

Each project gets its own FAISS index + graph, identified by an MD5 hash of the project path. See `get_vector_store_dir()` in `config.py`.

### Important Quirks

- **`DEEPSEEK_API_KEY` required at import time**: `completion/__init__.py` raises `ValueError` if unset. Set env var before starting server.
- **Custom CORS**: Hardcoded `*` via `@cors_exempt` decorator in `views.py` (not django-cors-headers).
- **Default chat provider**: `zhipu` (not deepseek). Default FIM model: `deepseek-chat`.
- **Test suite**: `test_api.py` (~1050 lines, custom TestRunner, requires running server). `completion/tests.py` is empty.
- **Hardcoded limits** in `services.py`: MAX_TOTAL_LENGTH=8000, MAX_INCLUDES=10, MAX_FUNCTIONS=5, MAX_PROMPT_LENGTH=4000, DEFAULT_TIMEOUT=10s.
- **`rag_data/`** lives at `/home/niclas/codegen-server/rag_data/` (adjacent to `codegen/`).
- **LSP fallback**: Set `LSP_FALLBACK_COMMANDS` env var (comma-separated) to customize LSP fallback order. Default: `clangd,ccls`. Indexer tries each in order and falls back to regex parser if none available.

### Prompt Augmentation Points

1. `chat_service.py` — Graph-RAG fallback chain: graph → vector → no augmentation
2. `retriever.py` — Format as `// Relevant code from knowledge base:\n{context}\n\n// Current code context:\n{prompt}`
3. `graph_retriever.py` — Same format with `(Graph-RAG)` label
4. `prompt_templates.py` — Template: `{includes}` + `{functions}` + `{prompt}▌{suffix}`
