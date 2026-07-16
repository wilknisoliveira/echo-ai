# Architecture

## Overview
Personal Langgraph-based assistant with memory. Single chat thread intentionally maintained for conversation continuity.

## System Components

### Langgraph Agent (`agents/`)
Backend agent powered by Langgraph state machine.

**State Flow:**
```
START → reset_iteration_count → attach_timestamps
     → select_messages_before_summarize → summarize → select_messages_after_summarize
     → criticality_check → reasoning
          ├─(max iter reached)────────────────────────→ END
          └─→ skeptic
                ├─(not approved)──────────────────────→ reasoning (loop)
                ├─(approved + call_tools)→ prepare_tool_calls → primary_assistant_tools → reasoning
                └─(approved + finish)────────────────→ END
```

**Nodes:**

| Node | Function | Purpose |
|------|----------|---------|
| `reset_iteration_count` | Inline | Sets `iteration_count = 0` at invocation start |
| `attach_timestamps` | `attach_timestamps` | Prepends `[YYYY-MM-DD HH:MM:SS]` to newest human message |
| `select_messages_before_summarize` | `select_messages_before_summarize` | Saves last 10 messages to `messages_to_keep`, removes from `messages` |
| `summarize` | Langmem `SummarizationNode` | Compresses old conversation history (via retry_llm_call) |
| `select_messages_after_summarize` | `select_messages_after_summarize` | Restores kept messages into `messages` |
| `criticality_check` | `criticality_assessment` | Three-Laws safety check on user input (human, self, life, spirit) |
| `reasoning` | `reasoning_node` | Deliberative reasoning: analyze, plan, decide call_tools or finish |
| `skeptic` | `skeptic_node` | Challenges reasoning; rejects with feedback or approves |
| `prepare_tool_calls` | `_prepare_tool_calls_inner` | Converts ReasoningOutput tool_calls to AIMessage tool-call objects |
| `primary_assistant_tools` | `ToolNode` + fallback | Executes tools (Tavily search, upsert memory) |
| `leave_skill` | `pop_dialog_state` | Pops dialog stack for sub-graph delegation |

**LLM:** Two models via OpenRouter (`langchain-openrouter`):
- `LLM_MODEL` (default: `google/gemini-2.5-flash`) — General assistant chat
- `LLM_STRUCTURED_MODEL` (default: `google/gemini-2.5-flash`) — Structured output (reasoning, skeptic, criticality)

**Tools:**
- `TavilySearchResults` — Web search (max 1 result)
- `upsert_memory` — Vector memory storage using Google embeddings

**State Schema:**
```python
messages: list[BaseMessage]       # Conversation history (inherited from MessagesState)
context: dict                     # Summarization metadata
messages_to_keep: list[AnyMessage]  # Retained after summarization
dialog_state: list[str]           # Dialog stack for skill delegation
iteration_count: int              # Reasoning iterations counter (0..MAX_ITERATIONS)
reasoning_output: Any             # ReasoningOutput pydantic model
skeptic_output: Any               # SkepticOutput pydantic model
```

### Streamlit Interface (`presentation/web/`)
Web UI connecting to Langgraph API via langgraph_sdk.

**Flow:**
- Password authentication (MASTER_KEY env var)
- Chat input → POST to `/runs` → Stream response
- Visible nodes: `criticality_check`, `reasoning`, `skeptic`
- Single thread per session

### Infrastructure
- PostgreSQL (pgvector) — Vector storage
- Redis — Langgraph checkpointing
- Langgraph API — Port 8000

## Folder Structure

```
echo-ai/
├── agents/
│   ├── src/main_agent/
│   │   ├── graph.py              # Langgraph state machine
│   │   ├── primary_agent.py      # Assistant logic + prompt
│   │   ├── reasoning.py          # Reasoning node (deliberative analysis)
│   │   ├── skeptic.py            # Skeptic node (challenges reasoning)
│   │   └── utils/
│   │       ├── agent.py           # Agent wrapper class
│   │       ├── diagnostics.py     # save_diagnostic + unwrap_properties
│   │       ├── llm_model.py       # LLM configuration
│   │       ├── retry.py           # Exponential backoff retry helper
│   │       ├── state.py           # State schema
│   │       ├── utilities.py       # Tool node with fallback
│   │       ├── nodes/
│   │       │   ├── criticality_node.py  # Three-Laws safety check
│   │       │   ├── summarization_nodes.py
│   │       │   └── timestamp_node.py
│   │       └── tools/
│   │           └── memory_tool.py  # upsert_memory, prepare_memories
│   ├── diagnostics/              # Raw LLM dumps (dev only, ECHO_ENV=development)
│   ├── tests/
│   │   ├── unit_tests/
│   │   └── integration_tests/
│   ├── docker-compose.yml        # Production infra
│   ├── langgraph.json
│   └── pyproject.toml
├── presentation/
│   └── web/
│       ├── main.py               # Streamlit entry point
│       └── interface/
│           └── web_interface.py  # Chat UI + stream handling
└── .specify/
    └── memory/
        └── constitution.md       # Project guidelines
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| OPENROUTER_API_KEY | OpenRouter LLM access |
| GOOGLE_API_KEY | Google embeddings |
| LLM_MODEL | General chat model (default: google/gemini-2.5-flash) |
| LLM_STRUCTURED_MODEL | Structured output model (default: google/gemini-2.5-flash) |
| LLM_MAX_RETRIES | Max retries for LLM calls (default: 0) |
| TAVILY_API_KEY | Web search API key |
| MAX_ITERATIONS | Max reasoning/skeptic cycles (default: 5) |
| ECHO_ENV | Environment mode: "development" or "production" (default: production) |
| POSTGRES_* | Database connection |
| REDIS_* | Checkpoint store |
| LANGGRAPH_API_URL | Agent endpoint |
| THREAD_ID | Chat session |
| MASTER_KEY | Web UI password |
| EMBEDDING_MODEL | Embedding model name (default: models/gemini-embedding-001) |
