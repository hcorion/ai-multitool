# Project Structure

## Root Level
- `app.py` - Main Flask application with all routes and image generation logic
- `dynamic_prompts.py` - Dynamic prompt system for template-based generation
- `utils.py` - Utility functions (stop word removal, text processing)
- `secret-key.txt` - Auto-generated Flask session secret (gitignored)

## Frontend Source (`src/`)
- `chat.ts` - Chat functionality and message handling
- `script.ts` - Main frontend logic, event handlers, and UI interactions
- `share.ts` - Sharing functionality
- `utils.ts` - Frontend utility functions

## Templates (`templates/`)
- `index.html` - Main application interface
- `login.html` - User login page
- `result-section.html` - Image generation results partial
- `share.html` - Shared content display

## Static Assets (`static/`)
- `css/` - Compiled CSS from Sass
- `sass/` - Sass source files
- `js/` - Compiled TypeScript output
- `images/` - User-generated images organized by username
- `prompts/` - User-specific dynamic prompt files
- `chats/` - Chat conversation storage
- `assets/` - Static assets and resources

## Configuration Files
- `tsconfig.json` - TypeScript compiler configuration
- `package.json` - Frontend dependencies
- `Pipfile` - Python dependencies
- `ruff.toml` - Python linting configuration
- `.prettierrc` - Code formatting rules
- `.env` / `.env.local` - Environment variables (gitignored)

## Conventions

### File Organization
- User-specific content stored under `static/{type}/{username}/`
- Generated images include metadata and thumbnails
- Chat conversations stored as JSON files

### Naming Patterns
- Python files use snake_case
- TypeScript files use camelCase for functions, PascalCase for types
- Generated images: `{sequence}-{cleaned_prompt}.png`
- Thumbnails: `{sequence}-{cleaned_prompt}.thumb.jpg`

### Code Organization
- Flask routes handle both GET (display) and POST (processing)
- TypeScript modules export functions and types
- Image processing functions return structured data objects
- Error handling with custom exception classes