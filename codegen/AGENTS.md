# AGENTS.md - Code Completion Server Guide

**Generated:** 2026-03-24
**Commit:** b270daf
**Branch:** master

## Overview
Django-based code completion API server for VSCode plugin using DeepSeek FIM API + multi-provider Chat API.

## Structure
```
codegen/
├── api/                  # Django project config
├── completion/           # Main app (views, services, providers)
├── manage.py             # Django management
└── test_api.py           # Custom TestRunner (not pytest)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API endpoints | `completion/views.py` | `@csrf_exempt`, custom `@cors_exempt` |
| FIM service | `completion/services.py` | DeepSeek FIM API |
| Chat service | `completion/chat_service.py` | Multi-provider (chat) |
| Providers | `completion/model_providers.py` | DeepSeek, OpenAI, Anthropic, Zhipu |
| Prompts | `completion/prompt_templates.py` | System/user templates |

## ANTI-PATTERNS (THIS PROJECT)
- **Never use bare `except: pass`** - silently swallows errors (services.py:131, model_providers.py:156,212,284,340)
- **Never use generic `raise Exception(...)`** - use `ValueError` for params, specific errors for API
- **Never hardcode `DEBUG=True` in production** - settings.py:26
- **Never hardcode SECRET_KEY** - settings.py:23

## UNIQUE STYLES
- Custom `@cors_exempt` decorator instead of `django-cors-headers`
- API key validation at import time (`completion/__init__.py`)
- Dual completion paths: FIM (`/api/v1/completion`) + Chat (`/api/v1/chat`)
- Chinese error messages throughout

## COMMANDS
```bash
pixi install                           # Install deps
pixi run python manage.py migrate     # DB init
pixi run python manage.py runserver   # Dev server
pixi run python test_api.py           # Run tests
pixi run python -m black .           # Format
```

## Quick Start
```bash
pixi install
export DEEPSEEK_API_KEY="your-api-key"
pixi run python manage.py migrate
pixi run python manage.py runserver
```

## Error Codes
| Code | Meaning |
|------|---------|
| INVALID_PARAMS | Missing required parameters |
| INVALID_JSON | Invalid JSON format |
| API_TIMEOUT | LLM API timeout |
| API_CONNECTION_ERROR | Cannot connect to LLM API |
| API_ERROR | LLM API error |
| INTERNAL_ERROR | Server internal error |

## Testing
- Primary: `python test_api.py` (custom TestRunner, not pytest)
- Django: `python manage.py test` (runs completion.tests - currently empty)
- Categories: Unit, Error, Integration, Boundary, CORS, Performance, Chat, Models
