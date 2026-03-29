"""Protocol contracts for structured LLM integrations."""

from __future__ import annotations

from typing import Literal, Protocol, Sequence, TypeVar

from pydantic import BaseModel
from typing_extensions import TypedDict

T = TypeVar("T", bound=BaseModel)


class LLMMessage(TypedDict):
    """Single chat message passed to structured LLM backends.

    Attributes:
        role: Message role in the chat transcript.
        content: Message content text.
    """

    role: Literal["system", "user", "assistant"]
    content: str


class StructuredLLM(Protocol):
    """Interface for schema-constrained LLM generation."""

    def generate_structured(
        self,
        *,
        messages: Sequence[LLMMessage],
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Generate a response and validate it against a model schema.

        Args:
            messages: Ordered input messages.
            response_model: Pydantic model expected from the response.
            temperature: Sampling temperature for model inference.

        Returns:
            Parsed response model instance.
        """

        ...
