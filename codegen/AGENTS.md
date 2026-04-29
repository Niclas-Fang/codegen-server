# AGENTS.md - Code Completion Server Guide

**Generated:** 2026-04-16
**Commit:** current
**Branch:** master

## Overview
Django-based code completion API server for VSCode plugin using DeepSeek FIM API + multi-provider Chat API.

## Project Structure
```
codegen/
├── api/                  # Django project config (settings.py, urls.py, wsgi.py)
├── completion/           # Main Django app
│   ├── views.py          # API handlers (@csrf_exempt, custom @cors_exempt)
│   ├── services.py       # DeepSeek FIM API
│   ├── chat_service.py   # Multi-provider chat API (with RAG augmentation)
│   ├── model_providers.py # Provider classes (BaseProvider, DeepSeek/OpenAI/Anthropic/Zhipu)
│   ├── prompt_templates.py # Chat prompt building
│   ├── rag/              # RAG module for code completion enhancement
│   │   ├── chunker.py    # Code chunking (structural + character-based)
│   │   ├── vector_store.py # FAISS vector store with sentence embeddings
│   │   ├── retriever.py  # Retrieval and context formatting
│   │   └── indexer.py    # CLI tool for building/searching index
│   └── urls.py           # Routes: /completion, /chat, /models
├── manage.py             # Django management
└── test_api.py           # Custom TestRunner (~1050 lines, not pytest)
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| API endpoints | `completion/views.py` |
| FIM completion | `completion/services.py` |
| Chat completion | `completion/chat_service.py` |
| Model providers | `completion/model_providers.py` |
| Prompts | `completion/prompt_templates.py` |

## Request Flow
```
POST /api/v1/completion → views.completion() → services.call_fim_api()
POST /api/v1/chat       → views.chat()       → chat_service.call_chat_api()
GET  /api/v1/models     → views.models()     → model_providers.get_all_models()
```

## API Endpoints
- `POST /api/v1/completion` - FIM mode (DeepSeek)
- `POST /api/v1/chat` - Chat mode (multi-provider)
- `GET /api/v1/models` - List available providers/models

## Environment Variables
| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DEEPSEEK_API_KEY` | Yes | - | Import-time validation in `completion/__init__.py` |
| `ZHIPU_API_KEY` | For zhipu | - | |
| `OPENAI_API_KEY` | For openai | - | |
| `ANTHROPIC_API_KEY` | For anthropic | - | |
| `RAG_ENABLED` | No | true | Enable RAG context augmentation in chat |
| `RAG_EMBEDDING_MODEL` | No | sentence-transformers/all-MiniLM-L6-v2 | Embedding model for RAG |

## IMPORTANT QUIRKS

### Import-Time API Key Validation
`completion/__init__.py` raises `ValueError` if `DEEPSEEK_API_KEY` is missing **at import time**. App crashes on `python manage.py runserver` if key absent. Set env var BEFORE starting server.

### Custom CORS Decorator
Uses `@cors_exempt` (hardcoded `*` origin) instead of `django-cors-headers`. In production, consider restricting origins.

### Provider Defaults
- Default chat provider: `zhipu` (not deepseek)
- Default FIM model: `deepseek-chat`
- Default chat model per provider: see `model_providers.py` SUPPORTED_MODELS

### Hardcoded Limits (services.py)
- `MAX_TOTAL_LENGTH = 8000`
- `MAX_INCLUDES = 10`
- `MAX_FUNCTIONS = 5`
- `MAX_PROMPT_LENGTH = 4000`
- `DEFAULT_TIMEOUT = 10s`

## ANTI-PATTERNS (THIS PROJECT)

### Bare `except: pass`
Silently swallows JSON parse errors. Found at:
- `services.py:131-132` (error detail parsing)
- `model_providers.py:156-157` (DeepSeek)
- `model_providers.py:212-213` (OpenAI)
- `model_providers.py:284-285` (Anthropic)
- `model_providers.py:340-341` (Zhipu)

**Fix**: Use `except Exception:` with logging or specific exception types.

### Generic `raise Exception(...)`
Scattered throughout `services.py` (lines 133, 170, 172, 174, 176, 178) and `model_providers.py` (lines 158, 168, 170, 172, 214, 224, 226, 228, 286, 296, 298, 300, 342, 356, 358, 360).

**Fix**: Use `ValueError` for params, `requests.exceptions.Timeout`/`ConnectionError` for API errors.

### Hardcoded Secrets (settings.py)
- `SECRET_KEY` (line 23): Uses insecure placeholder - set via environment in production
- `DEBUG = True` (line 26): Never hardcode in production

## COMMANDS
```bash
# Install dependencies (uses pixi.toml, NOT requirements.txt)
pixi install

# Database
pixi run python manage.py migrate
pixi run python manage.py makemigrations  # Create migrations

# Run server
pixi run python manage.py runserver        # Default port 8000
pixi run python manage.py runserver 8080   # Custom port

# Run tests (REQUIRES running server)
pixi run python test_api.py                # All tests
pixi run python test_api.py test_name      # Single test (e.g., test_valid_request_minimal)

# Check Django config
pixi run python manage.py check

# Production (requires gunicorn)
pixi run gunicorn api.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120

# RAG Commands (build and search code knowledge base)
pixi run python -m completion.rag.indexer index <directory>  # Index code directory
pixi run python -m completion.rag.indexer stats               # Show index statistics
pixi run python -m completion.rag.indexer search "<query>"    # Search the index
pixi run python -m completion.rag.indexer clear               # Clear the index
```

## Quick Start
```bash
pixi install
export DEEPSEEK_API_KEY="your-api-key"   # Required before running
pixi run python manage.py migrate
pixi run python manage.py runserver
# In another terminal:
pixi run python test_api.py
```

## Error Codes
| Code | HTTP | Meaning |
|------|------|---------|
| INVALID_PARAMS | 400 | Missing required parameters |
| INVALID_JSON | 400 | Invalid JSON format |
| INVALID_METHOD | 405 | Wrong HTTP method |
| API_TIMEOUT | 500 | LLM API timeout |
| API_CONNECTION_ERROR | 500 | Cannot connect to LLM API |
| API_ERROR | 500 | LLM API error |
| INTERNAL_ERROR | 500 | Server internal error |

## Testing
- Primary: `test_api.py` (~1050 lines, custom TestRunner with colored output)
- Django test: `python manage.py test` (runs `completion.tests` - currently empty)
- Test categories: Unit, Error, Integration, Boundary, CORS, Performance, Chat, Models
- Tests require running server - prints warning if server not detected

## Documentation
- `API文档.md` - Complete API specs (Chinese)
- `部署指南.md` - Deployment guide (Chinese)
- `项目进展报告.md` - Project progress (Chinese)
