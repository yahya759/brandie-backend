# Brandie API

AI-powered Instagram automation backend built with FastAPI, LangGraph, and instagrapi.

## Features

- **AI Agent Chat** - Natural language interface for Instagram content management
- **Smart Caption Generation** - AI-generated captions with relevant hashtags
- **Image Prompt Generation** - Create prompts for AI image generators
- **Scheduled Posting** - Schedule posts for optimal engagement times
- **Instagram Authentication** - Secure login with 2FA support
- **Encrypted Sessions** - Session data encrypted at rest

## Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | FastAPI |
| AI Agent | LangGraph + LangChain |
| LLM | OpenAI GPT-4o-mini |
| Instagram API | instagrapi |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy |
| Task Scheduler | APScheduler |
| Authentication | JWT + Fernet encryption |

## Project Structure

```
brandie-backend/
├── main.py                    # FastAPI application entry
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── app/
│   ├── config.py             # Environment settings
│   ├── database.py           # SQLAlchemy setup
│   ├── models.py             # Database models
│   ├── schemas.py            # Pydantic schemas
│   ├── dependencies.py      # Auth dependencies
│   ├── routers/
│   │   ├── auth.py           # Authentication endpoints
│   │   └── chat.py           # Chat endpoints
│   ├── services/
│   │   ├── instagram_service.py   # Instagram API wrapper
│   │   ├── scheduler_service.py   # Post scheduling
│   │   └── encryption_service.py # Session encryption
│   └── agent/
│       ├── graph.py          # LangGraph workflow
│       ├── nodes.py          # Agent nodes
│       ├── prompts.py        # System prompts
│       └── tools.py          # Agent tools
```

## Quick Start

### Prerequisites

- Python 3.13+
- OpenAI API key
- Instagram account

### Installation

```bash
# Clone the repository
git clone https://github.com/yahya759/brandie-backend.git
cd brandie-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the server
uvicorn main:app --reload --port 8000
```

### Docker

```bash
# Build image
docker build -t brandie-api .

# Run container
docker run -p 7860:7860 brandie-api
```

## Environment Variables

Create a `.env` file:

```env
DATABASE_URL=sqlite:///./brandie.db
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
OPENAI_API_KEY=sk-...
ENCRYPTION_KEY=your-32-byte-encryption-key
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/instagram/login` | Login with Instagram credentials |
| POST | `/auth/instagram/verify-2fa` | Complete 2FA verification |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/message` | Send message to AI agent |
| GET | `/chat/history` | Get chat history |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## How It Works

1. **Authentication** - User logs in with Instagram credentials
2. **Session Encryption** - Session data is encrypted and stored securely
3. **AI Agent** - User chats with the AI agent in Arabic
4. **Content Generation** - Agent generates captions, hashtags, and image prompts
5. **Publishing** - Posts are published immediately or scheduled for later

## Supported Languages

- Arabic (primary)
- English (image prompts)

## License

MIT License
