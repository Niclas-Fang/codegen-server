# completion/ - Code Completion App

**Purpose:** Main Django app handling code completion API

## Structure
```
completion/
├── views.py              # API handlers (completion, chat, models)
├── urls.py               # Routes: /completion, /chat, /models
├── services.py           # DeepSeek FIM API (legacy)
├── chat_service.py       # Multi-provider chat API
├── model_providers.py    # Provider classes (384 lines)
├── prompt_templates.py   # Chat prompt building
└── __init__.py          # DEEPSEEK_API_KEY validation at import
```

## Request Flow
```
POST /api/v1/completion → views.completion() → services.call_fim_api()
POST /api/v1/chat       → views.chat()       → chat_service.call_chat_api()
GET  /api/v1/models     → views.models()     → model_providers.get_all_models()
```

## Providers (model_providers.py)
- `DeepSeekProvider` - DeepSeek API
- `OpenAIProvider` - OpenAI API
- `AnthropicProvider` - Anthropic Claude
- `ZhipuProvider` - 智谱AI (default)

## CONVENTIONS
- Environment variables: `DEEPSEEK_API_KEY`, `ZHIPU_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- Provider defaults: zhipu (chat), deepseek-chat (FIM)
- CORS: custom `@cors_exempt` decorator (hardcoded `*` origin)
- Constants: `MAX_TOTAL_LENGTH=8000`, `MAX_INCLUDES=10`, `MAX_FUNCTIONS=5`

## ANTI-PATTERNS
- **Bare `except: pass`** at lines 131, 156, 212, 284, 340 - silently swallows JSON parse errors
- **Generic `Exception`** - should use specific exceptions
- **Import-time validation** in `__init__.py` - API key missing crashes app on import
