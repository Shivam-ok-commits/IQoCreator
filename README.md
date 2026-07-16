# IQoCreator

AI-powered research platform for analyzing and fact-checking content from YouTube and other sources.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│              │     │              │     │              │
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL  │
│  Next.js 15  │     │  FastAPI     │     │              │
│  TailwindCSS │     │  SQLAlchemy  │     │              │
│  shadcn/ui   │     │  Pydantic v2 │     │              │
│              │     │              │     │              │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────▼───────┐
                     │              │
                     │    Redis     │
                     │   Cache      │
                     │              │
                     └──────────────┘
```

## Project Structure

```
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # Route handlers
│   │   ├── analysis/          # Content analysis module
│   │   ├── claim/             # Claim management module
│   │   ├── config/            # Application settings
│   │   ├── core/              # Core utilities
│   │   ├── database/          # Database base models, session, engine
│   │   ├── dependencies/      # FastAPI dependency injection
│   │   ├── evidence/          # Evidence management module
│   │   ├── exceptions/        # Custom exceptions & handlers
│   │   ├── integrations/      # External API integrations
│   │   ├── middleware/        # Custom middleware
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── pipeline/          # Processing pipelines
│   │   ├── repositories/      # Data access layer
│   │   ├── rules/             # Business rules & validation
│   │   ├── schemas/           # Pydantic v2 request/response schemas
│   │   ├── services/          # Business logic layer
│   │   └── utils/             # Shared utilities
│   ├── alembic/               # Database migrations
│   │   └── versions/          # Migration scripts
│   ├── alembic.ini            # Alembic configuration
│   ├── Dockerfile             # Backend Docker image
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Environment variables template
│
├── frontend/                   # Next.js 15 frontend
│   ├── app/                   # Next.js App Router pages
│   ├── components/            # React components (shadcn/ui)
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utility functions
│   ├── services/              # API client services
│   ├── types/                 # TypeScript type definitions
│   ├── Dockerfile             # Frontend Docker image
│   └── package.json           # Node.js dependencies
│
├── docker-compose.yml         # Multi-service Docker setup
├── README.md                  # This file
└── .gitignore
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (optional)

## Environment Variables

### Backend (`backend/.env`)

Copy the example file and adjust:

```bash
cp backend/.env.example backend/.env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment | `development` |
| `DEBUG` | Enable debug mode | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://iqocreator:iqocreator@localhost:5432/iqocreator` |
| `DATABASE_ECHO` | Log SQL queries | `false` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `YOUTUBE_API_KEY` | YouTube Data API key | (optional) |

### Frontend (`frontend/.env.local`)

```bash
cp frontend/.env.local.example frontend/.env.local
```

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Setup & Run

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d --build

# Stop all services
docker-compose down

# Reset databases
docker-compose down -v
```

### Option 2: Local Development

#### Backend

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

#### Frontend

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local

# Start the development server
npm run dev
```

## Database Migrations

```bash
# Generate a new migration (auto-detect changes)
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# View migration history
alembic history

# Generate SQL script (offline mode)
alembic upgrade head --sql

# Apply with custom database URL
alembic -x db_url=postgresql://user:pass@host/db upgrade head
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API root — version info |
| `GET` | `/health` | Health check — `{"status": "ok"}` |
| `GET` | `/docs` | Swagger UI (development only) |
| `GET` | `/redoc` | ReDoc UI (development only) |

## Verification Checklist

- [ ] Backend starts successfully
- [ ] Frontend starts successfully
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Database connection is functional
- [ ] Migrations can be generated and applied
- [ ] Docker Compose starts all services
- [ ] CORS is configured correctly
- [ ] Environment variables are loaded from `.env`
