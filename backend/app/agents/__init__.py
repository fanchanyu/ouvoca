"""Agent package — importing triggers tool/agent registration via app.agents.tools."""
from app.agents.engine import (
    classify_intent, get_agent, get_tool_definitions, execute_tool,
    chat_completion, AGENT_REGISTRY, TOOL_FUNCTIONS,
)
import app.agents.tools  # noqa: F401 — side-effect registers all domain tools

__all__ = [
    "classify_intent", "get_agent", "get_tool_definitions",
    "execute_tool", "chat_completion", "AGENT_REGISTRY", "TOOL_FUNCTIONS",
]
