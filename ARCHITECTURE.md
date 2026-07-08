# Architecture

## Overview
Personal Langgraph-based assistant with memory. Single chat thread intentionally maintained for conversation continuity.

## System Components

### Langgraph Agent (`agents/`)
Backend agent powered by Langgraph state machine.

**State Flow:**
```
START → select_messages_before_summarize → summarize → select_messages_after_summarize
       → PRIMARY_ASSISTANT → tools_condition → PRIMARY_ASSISTANT_TOOLS → END
                                                    ↓
                                              PRIMARY_ASSISTANT
```

**Nodes:**
- `summarize` - Token management via Langgraph SummarizationNode
- `PRIMARY_ASSISTANT` - Core agent logic with memory integration
- `PRIMARY_ASSISTANT_TOOLS` - Tool execution with fallback
- `LEAVE_SKILL` - Dialog stack management

**LLM:** Gemini 2.5 Flash (via OpenRouter / langchain-openrouter)

**Tools:**
- `TavilySearchResults` - Web search
- `upsert_memory` - Vector memory storage with OpenRouter embeddings

**State Schema:**
```python
context: dict          # Summarization metadata
messages_to_keep: list  # Retained after summarization
dialog_state: list     # Dialog stack for skill delegation
messages: list         # Conversation history
```

### Streamlit Interface (`presentation/web/`)
Web UI connecting to Langgraph API via langgraph_sdk.

**Flow:**
- Password authentication (MASTER_KEY env var)
- Chat input → POST to `/runs` → Stream response
- Single thread per session (THREAD_ID from env)

### Infrastructure
- PostgreSQL (pgvector) - Vector storage
- Redis - Langgraph checkpointing
- Langgraph API - Port 8000

## Folder Structure

```
echo-ai/
├── agents/
│   ├── src/main_agent/
│   │   ├── graph.py              # Langgraph state machine
│   │   ├── primary_agent.py     # Assistant logic + prompt
│   │   └── utils/
│   │       ├── agent.py         # Agent wrapper class
│   │       ├── llm_model.py     # LLM configuration
│   │       ├── state.py         # State schema
│   │       ├── utilities.py     # Tool node with fallback
│   │       ├── nodes/
│   │       │   └── summarization_nodes.py
│   │       └── tools/
│   │           └── memory_tool.py  # upsert_memory, prepare_memories
│   ├── tests/
│   │   ├── unit_tests/
│   │   └── integration_tests/
│   ├── docker-compose.yml       # Production infra
│   └── pyproject.toml
├── presentation/
│   └── web/
│       ├── main.py             # Streamlit entry point
│       └── interface/
│           └── web_interface.py
└── .specify/
    └── memory/
        └── constitution.md     # Project guidelines
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| OPENROUTER_API_KEY | OpenRouter access |
| POSTGRES_* | Database connection |
| REDIS_* | Checkpoint store |
| LANGGRAPH_API_URL | Agent endpoint |
| THREAD_ID | Chat session |
| MASTER_KEY | Web UI password |