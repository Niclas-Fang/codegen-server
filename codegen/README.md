# VSCode Intelligent Code Completion Server

A Django-based code completion API server for VSCode plugin, supporting DeepSeek FIM API and multi-provider Chat API with RAG (Retrieval-Augmented Generation) enhancement.

## Features

- **FIM Mode**: Fill-in-the-middle code completion via DeepSeek API
- **Chat Mode**: Multi-provider chat completion (DeepSeek, OpenAI, Anthropic, Zhipu)
- **Graph-RAG Enhancement**: Hybrid graph + vector retrieval for superior code context
- **Language Server Protocol (LSP)**: Uses clangd (or ccls as fallback) for precise C/C++ AST extraction
- **Code Knowledge Graph**: Extracts functions, classes, imports, calls, inheritance via LSP
- **Graph Traversal**: Multi-hop retrieval through call chains and dependencies
- **Project Isolation**: Each project has its own vector store and graph
- **Incremental Indexing**: Only update changed files (mtime-based), no full rebuild needed
- **Embedding Cache**: LRU cache for faster repeated queries

## Quick Start

### Prerequisites

- Python 3.14.1+
- [Pixi](https://pixi.sh/latest/) installed
- At least one API key: `DEEPSEEK_API_KEY`, `ZHIPU_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`

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

### FIM Completion

```bash
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
    "suffix": "\n    return 0;\n}",
    "max_tokens": 100
  }'
```

### Chat Completion with Graph-RAG

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
pixi run python -m completion.rag.indexer stats --project-path /path/to/project

# Search index
pixi run python -m completion.rag.indexer search "def handle_request"

# Clear index
pixi run python -m completion.rag.indexer clear --project-path /path/to/project
```

### Language Server (LSP) Setup

Graph-RAG uses a Language Server for precise C/C++ AST extraction. If clangd is not available, it automatically falls back to ccls (GCC-compatible alternative). If neither is available, it falls back to regex-based parsing.

**Install clangd (recommended):**
```bash
# Ubuntu/Debian
sudo apt-get install clangd

# macOS
brew install llvm
```

**Install ccls (fallback, GCC-compatible):**
```bash
# Ubuntu/Debian
sudo apt-get install ccls

# macOS
brew install ccls
```

**Generate compile_commands.json (optional, for better LSP accuracy):**
```bash
# Using CMake
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON .

# Using Bear
bear -- make
```

**Configure LSP fallback:**
```bash
export LSP_COMMAND="clangd"
export LSP_FALLBACK_COMMANDS="clangd,ccls"  # tried in order
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
| `GRAPH_RAG_ENABLED` | No | `true` | Enable Graph-RAG globally |
| `RAG_EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Embedding model |
| `RAG_EMBEDDING_CACHE_SIZE` | No | `1000` | Embedding cache size |
| `LSP_COMMAND` | No | `clangd` | Language Server command |
| `LSP_FALLBACK_COMMANDS` | No | `clangd,ccls` | LSP fallback commands (comma-separated) |
| `LSP_ARGS` | No | - | Additional arguments for Language Server |

### RAG Parameters (in `completion/rag/config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CHUNK_SIZE` | 500 | Characters per chunk |
| `CHUNK_OVERLAP` | 50 | Overlap between chunks |
| `DEFAULT_TOP_K` | 5 | Number of results to retrieve |
| `MAX_CONTEXT_CHUNKS` | 3 | Max chunks in context |
| `SIMILARITY_THRESHOLD` | 0.5 | Minimum similarity score |
| `GRAPH_HOPS` | 2 | Graph traversal hops |

## Project Structure

```
codegen/
├── config/               # Django project settings
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
│       ├── code_parser.py   # LSP + regex code parser
│       ├── lsp_client.py    # Language Server Protocol client
│       ├── indexer.py       # CLI tool for indexing
│       └── config.py        # RAG configuration
├── manage.py
└── test_api.py           # Test suite
```

## Production Deployment

### Environment Configuration

```bash
DEEPSEEK_API_KEY=your-api-key
DEBUG=False
SECRET_KEY=<random-string>
ALLOWED_HOSTS=your-domain.com
RAG_ENABLED=true
```

### Using Gunicorn

```bash
pixi add --pypi gunicorn
pixi run gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
```

## Troubleshooting

### Server Won't Start

```bash
# Check environment variables
echo $DEEPSEEK_API_KEY

# Check port availability
netstat -tlnp | grep :8000

# Check Django configuration
pixi run python manage.py check
```

### API Returns 500 Error

```bash
# Check API key
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/beta/models
```

### RAG Retrieval Not Working

```bash
# Check if index exists
pixi run python -m completion.rag.indexer stats

# Build index if missing
pixi run python -m completion.rag.indexer index <code-directory>

# Ensure project_path matches the one used during indexing
```

## Security

1. **API Key Security**: Never commit API keys to version control. Use environment variables.
2. **Access Control**: Restrict `ALLOWED_HOSTS` in production.
3. **CORS**: Specify specific domains instead of `*` in production.

## Documentation

- [API文档.md](API文档.md) - Complete API specification (Chinese)
- [README-zh.md](README-zh.md) - Chinese translation of this README
- [CLAUDE.md](CLAUDE.md) - Claude Code project instructions
- [examples/](examples/) - FIM and RAG usage examples

## License

MIT
