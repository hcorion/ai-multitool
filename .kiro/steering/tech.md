# Technology Stack

## Coding Principles

- **KISS/YAGNI**: Simple solutions, build only what's needed
- **Duplication > Wrong Abstraction**: Wait for 3+ use cases before generalizing
- **Cognitive Load Over Rules**: Measure by understandability, not line count
- **Synchronous by Default**: Use async only when genuinely needed
- **Idiomatic Code**: Follow language conventions

## Stack

### Backend
- Python 3.13 + Flask
- OpenAI SDK (Responses API with web search/reasoning, GPT-Image-1)
- Pydantic for request/response validation
- NovelAI custom client
- Pillow/Wand for image processing

### Frontend
- TypeScript → ES2024 with strict checking
- jQuery for DOM/AJAX
- Showdown.js + Highlight.js for markdown/code
- Sass for CSS preprocessing

### Tools
- Ruff (linting), Prettier (formatting)
- pytest with pytest-dotenv
- pipenv + npm

## Commands

```powershell
# Setup
npm install && pipenv sync

# Development
pipenv shell && .\run-user.ps1

# Build
tsc && sass static/sass:static/css

# Test
pytest                       # all tests
pytest -m "not integration"  # unit only
pytest --cov=app             # with coverage
```

## Environment Variables
- `OPENAI_API_KEY` - GPT-Image-1, Responses API
- `STABILITY_API_KEY` - StabilityAI
- `NOVELAI_API_KEY` - NovelAI operations

## Testing

- Unit tests mock external APIs; integration tests use real keys from `.env.local`
- Use `skip_if_no_api_key` fixture for conditional integration tests
- JavaScript tested via Selenium with headless Chrome
- Fixtures in `conftest.py`: `client`, `mock_openai_client`, `api_keys`, `sample_image_data`
