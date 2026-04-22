from __future__ import annotations

import pytest

from younggeul_core._compat import (
    DEFAULT_BACKEND,
    ENV_VAR,
    get_backend,
    require_abdp,
)


def test_default_backend_is_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert get_backend() == "local"
    assert DEFAULT_BACKEND == "local"


@pytest.mark.parametrize("value", ["local", "abdp", "LOCAL", "  ABDP  "])
def test_get_backend_accepts_valid_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(ENV_VAR, value)
    assert get_backend() == value.strip().lower()


def test_get_backend_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_VAR, "remote")
    with pytest.raises(ValueError, match="not supported"):
        get_backend()


def test_require_abdp_raises_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "abdp" or name.startswith("abdp."):
            raise ImportError("simulated missing abdp")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="abdp"):
        require_abdp()
