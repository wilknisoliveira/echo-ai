<!--
## Sync Impact Report

- Version change: 0.0.0 → 0.1.0
- Added principles: I. Personal Assistant, II. Single Thread, III. Documentation On-Call, IV. Langgraph Framework, V. Streamlit Interface
- Added sections: Development Workflow, Infrastructure
- Templates requiring updates: ⚠ pending (all templates use generic placeholders)
-->

# Echo Constitution

## Core Principles

### I. Personal Assistant
This is a personal langgraph agent for human interaction. It is NOT a multitenant system. The single chat thread design is intentional to maintain conversation history for a personal assistant.

### II. Single Thread
A single chat thread is used intentionally. Do not implement multi-thread or multi-user features.

### III. Documentation On-Call
When implementing new features, MUST update the following documents if outdated:
- `ARCHITECTURE.md` - System architecture and folder structure
- `.specify/memory/constitution.md` - This file (mandatory guidelines)
- `README.md` - Project overview
- `presentation/web/README.md` - Interface documentation
- `agents/README.md` - Agent documentation

### IV. Langgraph Framework
The agent core is developed with Langgraph. All agent logic must integrate with the Langgraph state machine defined in `agents/src/main_agent/graph.py`.

### V. Streamlit Interface
The presentation layer uses Streamlit. The interface is currently temporary and may be replaced in the future. Do not invest heavily in UI polish until a stable interface is chosen.

## Development Workflow

### Mandatory Pre-Implementation Steps
Before any implementation:
1. Read `ARCHITECTURE.md`
2. Read `.specify/memory/constitution.md`
3. Understand the Langgraph state machine in `agents/src/main_agent/graph.py`
4. Review existing tools in `agents/src/main_agent/utils/tools/`

### Testing & Linting

> **PowerShell Tips**
> - Use `&` call operator for venv commands (e.g., `& .venv\Scripts\python.exe`)
> - Avoid `&&` - use semicolon `;` for sequential commands
> - Quote paths with spaces: `"C:\Program Files\..."`
> - Run venv commands from project root or use `workdir` parameter

**Python Syntax Check:**
```powershell
& "C:\Users\wilkn\Code\Projects\Echo\echo-ai\presentation\web\venv\Scripts\python.exe" -m py_compile "file.py"
```

### Command Order
lint → typecheck → test (run all three before committing)

## Infrastructure

### Dependencies
- Python >= 3.10
- PostgreSQL + Redis (required for production via docker-compose)
- Environment: `.env` file with `GOOGLE_API_KEY`, `POSTGRES_*`, `REDIS_*`

### Services
- Langgraph Agent: `agents/` (dev: `langgraph dev`)
- Streamlit Interface: `presentation/web/` (dev: `streamlit run main.py`)
- Production: `docker-compose up` from `agents/` directory

## Governance

This constitution supersedes generic practices. All changes must update documentation per Principle III.

**Version**: 0.1.0 | **Ratified**: 2025-07-17 | **Last Amended**: 2026-04-22