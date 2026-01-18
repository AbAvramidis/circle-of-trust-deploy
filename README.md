# Circle of Trust (LLM Council)

A multi-LLM advisory system that consults multiple AI models and synthesizes their responses through a 3-stage council process. Think of it as your personal "council of advisors" where multiple AI perspectives are combined to give you more balanced, thoughtful answers.

## Overview

Circle of Trust orchestrates conversations with multiple LLMs (via Ollama) using a sophisticated 3-stage process:

### How It Works

1. **Stage 1 - Collect Responses**: Your question is sent to all configured advisor models in parallel. Each model provides its independent response.

2. **Stage 2 - Peer Ranking**: Each model evaluates and ranks all the anonymized responses (including its own), providing reasoning for their rankings.

3. **Stage 3 - Final Synthesis**: A "chairman" model aggregates the rankings and synthesizes a final, consensus response that incorporates the best insights from all advisors.

### Features

- **Multi-model consultation**: Configure multiple LLM advisors with different personalities/models
- **Group Chat**: Have multiple AI personas discuss topics together
- **Persona Generation**: Auto-generate detailed personas from Wikipedia for your advisors
- **Real-time streaming**: Watch responses come in as they're generated
- **Conversation history**: All conversations are persisted in SQLite
- **Monitoring dashboard**: Track Ollama status and usage statistics

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager
- **[Ollama](https://ollama.ai/)** - Local LLM runtime (must be running with models pulled)

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd llm-council
```

### 2. Install dependencies

**Backend (Python):**
```bash
uv sync
uv pip install -e ".[dev]"
```

**Frontend (Node.js):**
```bash
cd frontend
npm install
cd ..
```

### 3. Start Ollama

Make sure Ollama is running and you have at least one model pulled:

```bash
ollama serve  # In a separate terminal
ollama pull llama3.2  # Or any model you prefer
```

### 4. Run the application

```bash
./start.sh
```

Or run backend and frontend separately:

```bash
# Terminal 1 - Backend
uv run python -m backend.main

# Terminal 2 - Frontend
cd frontend && npm run dev
```

### 5. Open the app

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## Running Tests

### Backend Tests (pytest)

```bash
# Run all tests
.venv/bin/pytest

# Run with verbose output
.venv/bin/pytest -v

# Run specific test file
.venv/bin/pytest tests/test_council.py
```

### Frontend Tests (Vitest)

```bash
cd frontend

# Run tests once
npm test -- --run

# Run tests in watch mode
npm test
```

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── main.py             # API routes and endpoints
│   ├── council.py          # 3-stage council orchestration
│   ├── group_chat.py       # Group chat functionality
│   ├── ollama_client.py    # Ollama API client
│   ├── persona_generator.py # Wikipedia-based persona generation
│   ├── storage.py          # Database operations
│   ├── models.py           # SQLAlchemy models
│   ├── database.py         # Database configuration
│   ├── config.py           # Application configuration
│   └── tests/              # Backend unit tests
├── frontend/               # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx         # Main application component
│   │   ├── api.js          # Backend API client
│   │   └── components/     # React components
│   └── package.json
├── tests/                  # Integration tests
├── data/                   # Runtime data (SQLite DB, configs)
├── prompts/                # Custom prompt templates
├── pyproject.toml          # Python project configuration
├── start.sh                # Convenience startup script
└── README.md
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
OLLAMA_API_URL=http://localhost:11434
```

### Council Configuration

Edit `data/council_config.json` to configure your advisors:

```json
{
  "advisors": [
    {
      "name": "Philosopher",
      "description": "A thoughtful philosophical advisor",
      "model": "llama3.2"
    },
    {
      "name": "Scientist", 
      "description": "A data-driven scientific advisor",
      "model": "llama3.2"
    }
  ]
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations` | GET | List all conversations |
| `/api/conversations` | POST | Create new conversation |
| `/api/conversations/{id}` | GET | Get conversation details |
| `/api/conversations/{id}/messages` | POST | Send message (triggers council) |
| `/api/group-chats` | GET/POST | Manage group chats |
| `/api/models` | GET | List available Ollama models |
| `/api/monitoring` | GET | Get system status and stats |
| `/api/council/config` | GET/PUT | Manage council configuration |

## License

MIT
