# AGENTS.md

## Required Reading Before Implementation
- `PROMPT.md` - Project requirements and workflow
- `.specify/memory/constitution.md` - Project guidelines (currently empty template)
- `ARCHITECTURE.md` - System architecture (currently empty)

## Development Commands

### Langgraph Agent (`agents/`)
```powershell
cd agents
.venv\Scripts\ Activate.ps1
langgraph dev
```

### Streamlit Interface (`presentation/web/`)
```powershell
cd presentation/web
streamlit run main.py
```

### Production
```powershell
docker-compose up
```

## Testing & Linting
```powershell
cd agents
pytest
ruff check .
mypy .
```

## Key Files
- `agents/src/main_agent/graph.py` - Langgraph definition
- `agents/src/main_agent/primary_agent.py` - Main agent logic
- `presentation/web/main.py` - Streamlit entry point

## Dependencies
- Python >= 3.10
- PostgreSQL + Redis (via docker-compose for production)
- Environment: `.env` file with `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, `POSTGRES_*`, `REDIS_*`

## Notes
- Single chat thread intentionally used (personal assistant)
- Update docs when implementing features per PROMPT.md