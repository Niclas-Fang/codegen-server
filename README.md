# Code Completion API Server

A Django-based code completion API server for VSCode intelligent coding assistant plugin. Provides AI-powered code completion suggestions using DeepSeek FIM API and multi-provider Chat API with Graph-RAG enhancement.

## Quick Start

```bash
git clone <repo-url> && cd codegen-server
pixi install
export DEEPSEEK_API_KEY="your-api-key"
pixi run python codegen/manage.py migrate
pixi run python codegen/manage.py runserver
```

## Documentation

- **[codegen/README.md](codegen/README.md)** - Full project README (English)
- **[codegen/README-zh.md](codegen/README-zh.md)** - 中文文档
- **[codegen/API文档.md](codegen/API文档.md)** - Complete API specification
- **[codegen/examples/](codegen/examples/)** - FIM and RAG usage examples

## License

MIT
