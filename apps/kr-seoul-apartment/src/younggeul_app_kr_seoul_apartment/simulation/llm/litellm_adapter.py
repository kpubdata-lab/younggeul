"""LiteLLM adapter that validates structured JSON responses."""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from importlib import import_module
from typing import Any, TypeVar

from opentelemetry.trace import Status, StatusCode
from pydantic import BaseModel, ValidationError

from ..tracing import get_tracer
from .ports import LLMMessage

T = TypeVar("T", bound=BaseModel)


def _normalize_provider(model: str) -> str:
    if "/" in model:
        return model.split("/")[0]
    return "openai"


class StructuredLLMTransportError(RuntimeError):
    """Raised when transport-level LLM invocation fails."""

    pass


class StructuredLLMResponseError(ValueError):
    """Raised when LLM output is empty, invalid, or schema-incompatible."""

    pass


class LiteLLMStructuredLLM:
    """Structured LLM transport backed by the LiteLLM completion API."""

    def __init__(self, model: str, **default_kwargs: Any) -> None:
        self.model = model
        self._default_kwargs = default_kwargs

    def generate_structured(
        self,
        *,
        messages: Sequence[LLMMessage],
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Generate and validate a structured response from LiteLLM.

        Args:
            messages: Ordered chat messages sent to the model.
            response_model: Pydantic model used as the response schema.
            temperature: Sampling temperature for generation.

        Returns:
            Parsed and validated response model instance.

        Raises:
            StructuredLLMTransportError: When the model call fails.
            StructuredLLMResponseError: When output content is invalid.
        """
        litellm = import_module("litellm")

        schema = response_model.model_json_schema()
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": response_model.__name__, "schema": schema},
        }

        tracer = get_tracer()
        span_attrs = {
            "llm.request.model": self.model,
            "llm.provider": _normalize_provider(self.model),
        }
        start = time.monotonic()

        with tracer.start_as_current_span("llm.completion", attributes=span_attrs) as span:
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=list(messages),
                    temperature=temperature,
                    response_format=response_format,
                    **self._default_kwargs,
                )
            except Exception as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                span.set_attribute("llm.status", "error")
                span.set_attribute("llm.error.type", type(exc).__name__)
                span.set_attribute("llm.latency_ms", elapsed_ms)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                raise StructuredLLMTransportError(f"LLM call failed: {exc}") from exc

            elapsed_ms = (time.monotonic() - start) * 1000
            actual_model = getattr(response, "model", None)
            if isinstance(actual_model, str) and actual_model != self.model:
                span.set_attribute("llm.response.model", actual_model)

            usage = getattr(response, "usage", None)
            if usage is not None:
                prompt_tokens = (
                    usage.get("prompt_tokens") if isinstance(usage, dict) else getattr(usage, "prompt_tokens", None)
                )
                completion_tokens = (
                    usage.get("completion_tokens")
                    if isinstance(usage, dict)
                    else getattr(usage, "completion_tokens", None)
                )
                total_tokens = (
                    usage.get("total_tokens") if isinstance(usage, dict) else getattr(usage, "total_tokens", None)
                )

                if prompt_tokens is not None:
                    span.set_attribute("llm.prompt_tokens", prompt_tokens)
                if completion_tokens is not None:
                    span.set_attribute("llm.completion_tokens", completion_tokens)
                if total_tokens is not None:
                    span.set_attribute("llm.total_tokens", total_tokens)

            hidden_params = getattr(response, "_hidden_params", None)
            if isinstance(hidden_params, dict):
                cost_usd = hidden_params.get("response_cost")
                if cost_usd is not None:
                    span.set_attribute("llm.cost_usd", cost_usd)

            choices = getattr(response, "choices", None)
            if choices:
                finish_reason = getattr(choices[0], "finish_reason", None)
                if finish_reason is not None:
                    span.set_attribute("llm.finish_reason", finish_reason)

            span.set_attribute("llm.status", "success")
            span.set_attribute("llm.latency_ms", elapsed_ms)

        raw_content = response.choices[0].message.content
        if raw_content is None:
            raise StructuredLLMResponseError("LLM returned empty content")

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise StructuredLLMResponseError(f"LLM returned invalid JSON: {raw_content[:200]}") from exc

        try:
            return response_model.model_validate(data)
        except ValidationError as exc:
            raise StructuredLLMResponseError(f"LLM output failed schema validation: {exc}") from exc
