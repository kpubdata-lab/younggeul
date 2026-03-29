from __future__ import annotations

import os

DEFAULT_ALLOWED_MODELS: list[str] = [
    "stub",
    "gpt-4o-mini",
    "gpt-4o",
    "anthropic/claude-3-haiku-20240307",
    "anthropic/claude-3-5-sonnet-20241022",
]
MAX_ROUNDS_LIMIT: int = 10


def get_allowed_models() -> list[str]:
    allowed_models_env = os.getenv("YOUNGGEUL_ALLOWED_MODELS")
    if allowed_models_env is None:
        return DEFAULT_ALLOWED_MODELS
    parsed = [m.strip() for m in allowed_models_env.split(",") if m.strip()]
    return parsed if parsed else DEFAULT_ALLOWED_MODELS


def validate_model_id(model_id: str) -> str:
    allowed = get_allowed_models()
    if model_id not in allowed:
        raise ValueError(f"model_id '{model_id}' is not allowed. Allowed: {', '.join(allowed)}.")
    return model_id


def validate_max_rounds(max_rounds: int) -> int:
    if max_rounds < 1 or max_rounds > MAX_ROUNDS_LIMIT:
        raise ValueError(f"max_rounds must be between 1 and {MAX_ROUNDS_LIMIT}.")
    return max_rounds
