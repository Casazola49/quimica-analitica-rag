"""
test_model_rotation.py - Smart model re-routing behaviour.

The portal must keep answering when an individual model is saturated, and must
NOT hide an exhausted quota behind a chain of doomed retries. These tests pin
both halves of that rule.
"""

import pytest

from src import gemini_client as gc


class _Boom(Exception):
    """Stand-in for a Google GenAI error carrying an HTTP-style code."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class _FakeModels:
    """Fails the first N model ids with ``code``, then succeeds."""

    def __init__(self, fail: dict, code: int, message: str) -> None:
        self.fail = fail
        self.code = code
        self.message = message
        self.attempts: list[str] = []

    def _maybe_fail(self, model: str) -> None:
        self.attempts.append(model)
        if model in self.fail:
            raise _Boom(self.code, f"{self.message} on {model}")

    def generate_content(self, model, contents, config=None):
        self._maybe_fail(model)
        return type("R", (), {"text": f"ok:{model}"})()

    def generate_content_stream(self, model, contents, config=None):
        self._maybe_fail(model)
        yield type("C", (), {"text": f"ok:{model}"})()


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models


class TestFailureClassification:
    """Quota, key errors and saturation must not be confused."""

    @pytest.mark.parametrize(
        "code,message,expected",
        [
            (429, "Resource has been exhausted", "quota"),
            (429, "You exceeded your current quota", "quota"),
            (None, "quota exceeded for this project", "quota"),
            (503, "This model is currently experiencing high demand", "transient"),
            (500, "Internal error", "transient"),
            (None, "deadline exceeded", "transient"),
            (403, "forbidden", "fatal"),
            (400, "invalid api key", "fatal"),
        ],
    )
    def test_classification(self, code, message, expected) -> None:
        """Each failure class maps to the response it deserves."""
        assert gc.classify_model_failure(code, message.lower()) == expected


class TestFallbackChain:
    """Every configured model must be a real, current API id."""

    def test_chain_has_no_retired_models(self) -> None:
        """Rotating into a retired id only spends time on 404s."""
        retired = {"gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro"}
        assert retired.isdisjoint(set(gc.MODEL_FALLBACK_CHAIN))

    def test_chain_starts_with_the_newest_default(self) -> None:
        """The default is the first entry tried."""
        assert gc.MODEL_FALLBACK_CHAIN[0] == gc.DEFAULT_MODEL
        assert gc.DEFAULT_MODEL == "gemini-flash-latest"

    @pytest.mark.parametrize(
        "display",
        [
            "Gemini Flash (más reciente y avanzado)",
            "gemini-flash-latest",
            "gemini-flash-lite-latest (Flash Lite, máxima cuota)",
            "gemini-2.5-pro (último recurso, cuota propia)",
            "Gemini Flash Lite",
            "gemini-1.5-pro",
            None,
        ],
    )
    def test_every_ui_label_resolves_to_a_live_model(self, display) -> None:
        """A stale label must never send a retired id to the API."""
        resolved = gc.resolve_model_name(display)
        assert resolved in gc.MODEL_FALLBACK_CHAIN


class TestRotationOnSaturation:
    """HTTP 503 is per-model, so rotating genuinely helps."""

    def test_rotates_past_a_saturated_model(self, monkeypatch) -> None:
        """A 503 on the first model is re-routed to the next one."""
        models = _FakeModels({"gemini-flash-latest"}, 503, "high demand")
        monkeypatch.setattr(gc, "get_gemini_client", lambda key: _FakeClient(models))

        out = gc.generate_response("mock_test_key_12345", "hola", model=gc.DEFAULT_MODEL)

        assert out == "ok:gemini-3.5-flash"
        assert len(models.attempts) == 2
        assert gc.get_last_model_used() == "gemini-3.5-flash"

    def test_stream_rotates_past_a_saturated_model(self, monkeypatch) -> None:
        """The streaming path applies the same rule."""
        models = _FakeModels({"gemini-flash-latest"}, 503, "high demand")
        monkeypatch.setattr(gc, "get_gemini_client", lambda key: _FakeClient(models))

        out = "".join(
            gc.generate_response("mock_test_key_12345", "hola", stream=True, model=gc.DEFAULT_MODEL)
        )

        assert out == "ok:gemini-3.5-flash"
        assert gc.get_last_model_used() == "gemini-3.5-flash"


class TestQuotaIsNotHidden:
    """A 429 is the account's quota; rotating would only delay the message."""

    def test_stops_at_the_first_model_and_explains(self, monkeypatch) -> None:
        """One attempt, then the student is told the real cause."""
        models = _FakeModels(set(gc.MODEL_FALLBACK_CHAIN), 429, "Resource has been exhausted")
        monkeypatch.setattr(gc, "get_gemini_client", lambda key: _FakeClient(models))

        out = gc.generate_response("mock_test_key_12345", "hola", model=gc.DEFAULT_MODEL)

        assert models.attempts == [gc.DEFAULT_MODEL]
        assert out.startswith("⚠️")
        assert "429" in out
        assert "no rotamos" in out

    def test_bad_key_is_not_retried_across_models(self, monkeypatch) -> None:
        """A 403 fails for every model, so stop immediately."""
        models = _FakeModels(set(gc.MODEL_FALLBACK_CHAIN), 403, "forbidden")
        monkeypatch.setattr(gc, "get_gemini_client", lambda key: _FakeClient(models))

        gc.generate_response("mock_test_key_12345", "hola", model=gc.DEFAULT_MODEL)

        assert models.attempts == [gc.DEFAULT_MODEL]