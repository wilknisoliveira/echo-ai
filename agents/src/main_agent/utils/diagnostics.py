"""Save raw LLM responses to disk for debugging structured output issues."""

import json
import os
from datetime import datetime
from pathlib import Path

DIAG_DIR = Path(__file__).resolve().parents[3] / "diagnostics"


def unwrap_properties(raw_content: str) -> dict | None:
    """If the provider wrapped the response in {title, description, properties}, extract properties."""
    try:
        data = json.loads(raw_content)
        if isinstance(data, dict) and "properties" in data and "title" in data:
            return data["properties"]
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def save_diagnostic(
    node_name: str,
    raw_content: str,
    iteration: int = 0,
    error: str | None = None,
) -> None:
    if os.getenv("ECHO_ENV", "production") != "development":
        return

    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_name = node_name.replace(" ", "_")
    filename = f"{timestamp}_{safe_name}_iter{iteration}.json"

    payload = {
        "node": node_name,
        "iteration": iteration,
        "timestamp": timestamp,
        "raw_content": raw_content,
        "parsing_error": error,
    }

    (DIAG_DIR / filename).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
