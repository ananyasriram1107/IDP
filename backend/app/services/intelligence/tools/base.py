from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Tool:
    """A single agent tool: a name/description/JSON-schema the LLM sees,
    plus the async handler that actually executes it. Each tool wraps
    existing, unmodified services (question_service, relationships,
    analytics) -- this module adds, it doesn't change, that logic.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

    def spec(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
