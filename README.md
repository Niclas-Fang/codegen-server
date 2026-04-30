# Code Completion API Server

This project is written by opencode with deepseek v3.2.

A Django-based code completion API server for VSCode intelligent coding assistant plugin. This server provides AI-powered code completion suggestions using the DeepSeek API.

## Features

- **AI-Powered Code Completion**: Uses DeepSeek FIM API and multi-provider Chat API
- **Multi-Provider Support**: DeepSeek, OpenAI, Anthropic, Zhipu
- **Graph-RAG Enhancement**: Code knowledge graph with LSP-based AST extraction (clangd/ccls)
- **RESTful API**: Simple JSON-based API for integration with VSCode plugins
- **CORS Support**: Built-in CORS headers for cross-origin requests
- **Error Handling**: Comprehensive error codes and messages
- **Modern Tooling**: Uses Pixi for dependency management

## Quick Start

### Prerequisites
- Python 3.14.1+
- [Pixi](https://pixi.sh/latest/) installed
- DeepSeek API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd codegen-server
   ```

2. **Install dependencies with Pixi**
   ```bash
   pixi install
   ```

3. **Set up environment variables**
   ```bash
   export DEEPSEEK_API_KEY="your-deepseek-api-key"
   ```

4. **Initialize database**
   ```bash
   pixi run python manage.py migrate
   ```

5. **Start development server**
   ```bash
   pixi run python manage.py runserver
   # Or specify a different port
   pixi run python manage.py runserver 8080
   ```

6. **Verify installation**
   ```bash
   pixi run python test_api.py
   ```

## API Usage

### Basic Request
```bash
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "int main() {\n    int a = 10;\n    int b = 20;\n    ",
    "suffix": "\n    return 0;\n}"
  }'
```

### Complete Request Example
```bash
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{
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
    ],
    "max_tokens": 100
  }'
```

### API Response Format
```json
{
  "success": true,
  "suggestion": {
    "text": "int sum = a + b;\n    std::cout << \"Sum: \" << sum << std::endl;",
    "label": "Calculate and print sum"
  }
}
```

## Project Structure

```
codegen-server/
├── codegen/                    # Django project
│   ├── api/                   # Django project settings
│   ├── completion/            # Completion app
│   │   ├── views.py          # API endpoints
│   │   ├── services.py       # DeepSeek FIM API
│   │   ├── chat_service.py   # Multi-provider chat API
│   │   ├── model_providers.py # Provider abstraction
│   │   ├── rag/              # RAG & Graph-RAG module
│   │   └── urls.py           # App URL routing
│   ├── manage.py             # Django management script
│   └── test_api.py           # Test suite
├── pixi.toml                 # Pixi dependency configuration
└── README.md                # This file
```

## Production Deployment

### 1. Environment Configuration
```bash
DEEPSEEK_API_KEY=your-production-api-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost
```

### 2. Using Gunicorn
```bash
# Install gunicorn
pixi add --pypi gunicorn

# Start production server
pixi run gunicorn api.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
```

## Error Handling

### Common Error Codes
| Error Code | Description | Solution |
|------------|-------------|----------|
| INVALID_PARAMS | Missing or invalid request parameters | Check prompt and suffix parameters |
| INVALID_JSON | Invalid JSON format | Ensure request body is valid JSON |
| API_TIMEOUT | DeepSeek API timeout | Check network connection, increase timeout |
| API_CONNECTION_ERROR | Cannot connect to DeepSeek API | Check network and API endpoint |
| API_ERROR | DeepSeek API returned error | Check API key and quota |
| INTERNAL_ERROR | Server internal error | Check server logs |

### Error Response Example
```json
{
  "success": false,
  "error_code": "INVALID_PARAMS",
  "error": "Missing required parameter: prompt"
}
```

## Testing

```bash
# Run test suite
pixi run python test_api.py
```

### Test Categories
1. **Basic Tests**: Server connection, CORS support (always runs)
2. **Error Tests**: Parameter validation, error handling (always runs)
3. **API Tests**: Real API integration tests (requires valid API key)

## Development

### Code Style Guidelines
- Follow PEP 8 conventions
- Use type hints for all function signatures
- Document complex logic with clear comments
- Use Django best practices for views and models

### Dependency Management
This project uses [Pixi](https://pixi.sh/latest/) for dependency management instead of traditional `requirements.txt`.

**Key commands:**
```bash
# Install dependencies
pixi install

# Update dependencies
pixi update

# Add new dependency
pixi add --pypi package-name
```

### Available Development Commands
```bash
# Check project configuration
pixi run python manage.py check

# Create database migrations
pixi run python manage.py makemigrations

# Apply migrations
pixi run python manage.py migrate
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
# View Django error logs
pixi run python manage.py runserver

# Check DeepSeek API key
curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  https://api.deepseek.com/beta/models
```

### CORS Errors
```bash
# Test OPTIONS request
curl -X OPTIONS http://localhost:8000/api/v1/completion -i

# Check response headers
curl -I http://localhost:8000/api/v1/completion
```

## Security Recommendations

1. **API Key Security**
   - Never commit API keys to version control
   - Use environment variables or secret management services
   - Rotate API keys regularly

2. **Access Control**
   - Restrict ALLOWED_HOSTS in production
   - Consider adding API key authentication
   - Implement rate limiting

3. **CORS Configuration**
   - Specify specific domains instead of `*` in production
   - Only allow necessary HTTP methods

## Performance Optimization

1. **Adjust Timeout Settings**
   - Modify `DEFAULT_TIMEOUT` in `completion/services.py`

2. **Increase Worker Processes**
   ```bash
   pixi run gunicorn api.wsgi:application --workers 8 --threads 4
   ```

## Maintenance

### Updating Dependencies
```bash
# Update pixi dependencies
pixi update

# Reinstall Python packages
pixi install
```

### Database Maintenance
```bash
# Create migration files
pixi run python manage.py makemigrations

# Apply migrations
pixi run python manage.py migrate

# Backup database
cp db.sqlite3 db.sqlite3.backup
```

### Code Updates
```bash
# Pull latest code
git pull origin main

# Restart server (if using systemd)
sudo systemctl restart gunicorn
```

## Documentation

- **[API文档.md](codegen/API文档.md)** - Complete API specifications (Chinese)
- **[AGENTS.md](codegen/AGENTS.md)** - Development guide for AI agents
- **[部署指南.md](codegen/部署指南.md)** - Detailed deployment guide (Chinese)

## Support

When encountering issues:
1. Check error logs
2. Verify environment variables
3. Test API endpoints
4. Review relevant documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*Last Updated: 2026-05-01*