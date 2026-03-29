from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pydantic import BaseModel

litellm_adapter_module = import_module("younggeul_app_kr_seoul_apartment.simulation.llm.litellm_adapter")

LiteLLMStructuredLLM = litellm_adapter_module.LiteLLMStructuredLLM
StructuredLLMTransportError = litellm_adapter_module.StructuredLLMTransportError
_normalize_provider = litellm_adapter_module._normalize_provider


class _StructuredResponse(BaseModel):
    message: str


def _choice(content: str, *, finish_reason: str = "stop") -> SimpleNamespace:
    return SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)


def _make_test_tracer() -> tuple[object, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("unit-test"), exporter


def _span_attributes(span: object) -> dict[str, object]:
    attrs = getattr(span, "attributes")
    assert attrs is not None
    return dict(attrs)


def test_generate_structured_creates_child_span() -> None:
    adapter = LiteLLMStructuredLLM(model="vllm/meta-llama")
    tracer, exporter = _make_test_tracer()
    mock_litellm = MagicMock()
    mock_litellm.completion.return_value = SimpleNamespace(
        model="vllm/meta-llama-instruct",
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18),
        _hidden_params={"response_cost": 0.0123},
        choices=[_choice('{"message":"ok"}', finish_reason="stop")],
    )

    with patch.object(litellm_adapter_module, "get_tracer", return_value=tracer):
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            result = adapter.generate_structured(
                messages=[{"role": "user", "content": "hello"}],
                response_model=_StructuredResponse,
            )

    assert result == _StructuredResponse(message="ok")
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    attrs = _span_attributes(span)
    assert span.name == "llm.completion"
    assert attrs["llm.request.model"] == "vllm/meta-llama"
    assert attrs["llm.provider"] == "vllm"
    assert attrs["llm.response.model"] == "vllm/meta-llama-instruct"
    assert attrs["llm.prompt_tokens"] == 11
    assert attrs["llm.completion_tokens"] == 7
    assert attrs["llm.total_tokens"] == 18
    assert attrs["llm.cost_usd"] == pytest.approx(0.0123)
    assert attrs["llm.finish_reason"] == "stop"
    assert attrs["llm.status"] == "success"
    assert isinstance(attrs["llm.latency_ms"], (int, float))
    assert attrs["llm.latency_ms"] >= 0
    assert span.status.status_code == StatusCode.UNSET


def test_generate_structured_records_error_span() -> None:
    adapter = LiteLLMStructuredLLM(model="anthropic/claude-3")
    tracer, exporter = _make_test_tracer()
    mock_litellm = MagicMock()
    mock_litellm.completion.side_effect = RuntimeError("network down")

    with patch.object(litellm_adapter_module, "get_tracer", return_value=tracer):
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            with pytest.raises(StructuredLLMTransportError, match="LLM call failed"):
                adapter.generate_structured(
                    messages=[{"role": "user", "content": "hello"}],
                    response_model=_StructuredResponse,
                )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    attrs = _span_attributes(span)
    assert span.name == "llm.completion"
    assert attrs["llm.request.model"] == "anthropic/claude-3"
    assert attrs["llm.provider"] == "anthropic"
    assert attrs["llm.status"] == "error"
    assert attrs["llm.error.type"] == "RuntimeError"
    assert isinstance(attrs["llm.latency_ms"], (int, float))
    assert attrs["llm.latency_ms"] >= 0
    assert span.status.status_code == StatusCode.ERROR


def test_normalize_provider_openai() -> None:
    assert _normalize_provider("gpt-4") == "openai"


def test_normalize_provider_vllm() -> None:
    assert _normalize_provider("vllm/model") == "vllm"


def test_normalize_provider_anthropic() -> None:
    assert _normalize_provider("anthropic/claude-3") == "anthropic"


def test_cost_usd_absent_gracefully_handled() -> None:
    adapter = LiteLLMStructuredLLM(model="gpt-4")
    tracer, exporter = _make_test_tracer()
    mock_litellm = MagicMock()
    mock_litellm.completion.return_value = SimpleNamespace(
        model="gpt-4",
        usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5),
        _hidden_params={},
        choices=[_choice('{"message":"ok"}', finish_reason="stop")],
    )

    with patch.object(litellm_adapter_module, "get_tracer", return_value=tracer):
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            adapter.generate_structured(
                messages=[{"role": "user", "content": "hello"}],
                response_model=_StructuredResponse,
            )

    span = exporter.get_finished_spans()[0]
    attrs = _span_attributes(span)
    assert "llm.cost_usd" not in attrs
    assert attrs["llm.status"] == "success"
    assert attrs["llm.prompt_tokens"] == 2
    assert attrs["llm.completion_tokens"] == 3
    assert attrs["llm.total_tokens"] == 5
