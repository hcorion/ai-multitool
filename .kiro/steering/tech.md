# Technology Stack

## Backend
- **Python 3.13** with Flask web framework
- **OpenAI Python SDK** for DALL-E 3 and Assistant API integration
- **Requests** library for StabilityAI and NovelAI API calls
- **Pillow (PIL)** for image processing and metadata handling
- **Wand (ImageMagick)** for advanced image operations and grid generation
- **Pygments** and **Markdown** for syntax highlighting and text processing

## Frontend
- **TypeScript** compiled to ES2024 with strict type checking
- **jQuery** for DOM manipulation and AJAX requests
- **Showdown.js** for Markdown rendering with syntax highlighting
- **Highlight.js** for code syntax highlighting
- **Sass** for CSS preprocessing

## Build System
- **TypeScript Compiler (tsc)** with watch mode for development
- **Sass compiler** with watch mode for CSS generation
- **npm** for frontend dependency management
- **pipenv** for Python dependency management

## Development Tools
- **Ruff** for Python linting with Python 3.13 target
- **Prettier** for code formatting (4-space tabs, 120 char width)

## Common Commands

### Setup
```powershell
# Install dependencies
npm install
pipenv sync

# Install global tools
npm install -g typescript sass
```

### Development
```powershell
# Start development server (runs TypeScript, Sass, and Flask in watch mode)
pipenv shell
.\run-user.ps1
```

### Build
```powershell
# Compile TypeScript
tsc

# Compile Sass
sass static/sass:static/css
```

## Environment Variables
- `OPENAI_API_KEY`: Required for DALL-E 3 and chat functionality
- `STABILITY_API_KEY`: Required for StabilityAI image generation
- `NOVELAI_API_KEY`: Required for NovelAI image generation