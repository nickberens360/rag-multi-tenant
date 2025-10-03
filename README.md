# Nick Berens - Portfolio Website

Personal website with intelligent RAG-powered AI assistant. Built with FastAPI backend and Astro frontend, featuring a **unified smart retriever system** that automatically discovers and indexes content without configuration.

## Features

* **🤖 AI Chatbot ("nick.AI")**: RAG system with auto-discovery, dual LLM support (Claude/Gemini), streaming responses, and smart follow-ups

* **📊 Admin Dashboard**: Vue.js + Vuetify interface with real-time analytics, settings management, and secure authentication

* **🖥️ Interactive Terminal**: Draggable terminal for site navigation with command-line interface

* **🎨 Smart Gallery**: Illustrations with fuzzy search and parallax effects

* **📝 Blog & Resume**: MDX-powered blog and dynamic resume with PDF download

---

## Technology Stack

### Frontend
* **Astro** - Static site generation with component islands
* **Vue.js** - Interactive components (chatbot, terminal)
* **Nanostores** - Global state management

### Backend
* **FastAPI** - Async API with unified smart retriever
* **SQLite** - Query logging and admin data
* **LangChain** - RAG pipeline with smart routing
* **ChromaDB** - Vector database for semantic search

### AI Models
* **Claude 3.5 Sonnet** (primary) + **Gemini 1.5 Flash** (fallback)
* **GoogleGenerativeAI** embeddings

### Admin Dashboard
* **Vue.js 3 + Vuetify 3** - Material Design UI
* **Pinia** - State management
* **Chart.js** - Data visualization

---

## Project Structure

```text
├── src/                    # Astro frontend
│   ├── components/         # Vue components (ChatBot, Terminal)
│   ├── pages/             # Routes (index, blog, resume)
│   └── stores/            # Nanostores state
├── backend/               # FastAPI backend
│   ├── core/              # Business logic (unified_retriever, config)
│   ├── knowledge/         # Auto-indexed content (.md, .pdf, .json)
│   ├── routes/            # API endpoints
│   └── logs/              # SQLite databases
├── admin/frontend/        # Vue.js admin dashboard
│   └── src/               # Components, views, stores
├── tests/                 # Unit, integration, e2e tests
└── Makefile               # Development commands
```

## Quick Start

```bash
# Development
npm run dev                # Frontend
npm run backend:dev        # Backend
npm run admin:frontend     # Admin dashboard

# Code Quality
make lint-fix             # Format code
pytest -m unit           # Run tests
```

## Smart Retriever (Zero Configuration!)

**Just drop content files and go!**

1. **Add content**: Drop `.md`, `.pdf`, `.json` files in `backend/knowledge/` or `public/`
2. **Restart backend**: Content automatically indexed and searchable
3. **No config needed**: System auto-detects content types and routes queries intelligently

### Key Features
- **Auto-discovery**: Finds all content automatically
- **Smart routing**: Understands query intent (technical, personal, creative)
- **Semantic search**: ChromaDB with intelligent filtering
- **Multi-level caching**: Fast repeated queries

---

## Configuration & Environment

The backend now uses a database‑first configuration with code defaults:

- Secrets in env: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, optional `GITHUB_TOKEN`, `IP_HASH_SALT`, `ADMIN_DEFAULT_*`
- Deployment in env: `ENVIRONMENT`, `PUBLIC_API_URL`, public GitHub vars, optional GA tracking id
- Non‑secrets in DB (editable via Admin UI): LLM models, search/retrieval, RAG, feature flags, rate limit string, security/privacy
- Code defaults live in `backend/core/config_v2.py` and are overridden by DB values

Minimal `.env` example:

```bash
# Required secrets
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

# Deployment
ENVIRONMENT=development
PUBLIC_API_URL=http://localhost:8000
```

Notes

- Most settings are managed in the Admin Dashboard (DB overrides). Changes take effect without restart.
- FORCE_REBUILD_DATA is treated as an operational flag (one‑off), not a persisted setting.
- New code should import `AppConfig` from `backend.core.config_v2`.

## Admin Dashboard

* **Frontend**: `npm run admin:frontend` (Vue.js + Vuetify)
* **Backend**: Integrated at http://localhost:8000
* **Authentication**: Session-based with secure cookies
* **Features**: Analytics, settings, API key management

---

## Migration Summary (for contributors)

- New config entry point: `backend/core/config_v2.py`
- Legacy shim retained: `backend/core/config.py` (deprecated; kept for tests/back‑compat)
- Migration script: `backend/scripts/migrate_env_to_db.py` to seed DB from env where applicable

---

## License

This project is a personal portfolio and is not licensed for reuse.
