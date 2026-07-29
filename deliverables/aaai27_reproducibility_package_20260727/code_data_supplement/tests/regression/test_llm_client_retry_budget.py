from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

import llm_client


def _api_settings() -> dict[str, str]:
    return {
        "base_url": "https://example.invalid/v1",
        "api_key": "test-key",
        "model": "test-model",
        "source": "test",
    }


def test_get_client_disables_openai_sdk_retries(monkeypatch) -> None:
    captured: dict[str, object] = {}
    client = object()

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return client

    monkeypatch.setattr(llm_client, "_client", None)
    monkeypatch.setattr(llm_client, "api_settings", _api_settings)
    monkeypatch.setattr(llm_client, "OpenAI", fake_openai)

    assert llm_client.get_client() is client
    assert captured == {
        "base_url": "https://example.invalid/v1",
        "api_key": "test-key",
        "max_retries": 0,
    }


def test_llm_config_records_openai_sdk_retry_budget(monkeypatch) -> None:
    monkeypatch.setattr(llm_client, "api_settings", _api_settings)

    assert llm_client.llm_config()["sdk_max_retries"] == 0
    assert llm_client.llm_config()["json_temperature"] == 0.2


@pytest.mark.parametrize("error_type", [APIConnectionError, APITimeoutError])
def test_real_openai_transport_errors_are_retryable(error_type) -> None:
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    error = error_type(request=request)

    assert llm_client._is_retryable_llm_api_error(error) is True


@pytest.mark.parametrize("status_code", [408, 409, 425, 429, 499, 500, 501, 599])
def test_retryable_http_statuses_include_all_5xx(status_code: int) -> None:
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    error = APIStatusError("request failed", response=response, body=None)

    assert llm_client._is_retryable_llm_api_error(error) is True


def test_transport_retry_count_uses_only_api_retry_budget(monkeypatch) -> None:
    attempts = 0

    class RetryableError(RuntimeError):
        status_code = 503

    def create(**kwargs):
        nonlocal attempts
        attempts += 1
        raise RetryableError("temporarily unavailable")

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setenv("ALGOLAB_LLM_API_RETRIES", "1")
    monkeypatch.setenv("ALGOLAB_LLM_JSON_RETRIES", "9")
    monkeypatch.setenv("ALGOLAB_LLM_API_RETRY_DELAY_S", "0")

    with pytest.raises(RetryableError):
        llm_client._create_chat_completion_with_retry(client, model="test-model")

    assert attempts == 2


def test_invalid_json_retry_count_uses_only_json_retry_budget(monkeypatch) -> None:
    attempts = 0
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))],
        usage=None,
    )

    def fake_create(client, **kwargs):
        nonlocal attempts
        attempts += 1
        return response

    monkeypatch.setenv("ALGOLAB_LLM_JSON_RETRIES", "1")
    monkeypatch.setenv("ALGOLAB_LLM_API_RETRIES", "9")
    monkeypatch.setattr(llm_client, "get_client", lambda: object())
    monkeypatch.setattr(llm_client, "_create_chat_completion_with_retry", fake_create)
    monkeypatch.setattr(llm_client._MODEL_CALL_STATE, "calls", [], raising=False)

    with pytest.raises(llm_client.LLMJsonError):
        llm_client.chat_json_with_metadata(
            "system prompt",
            "user prompt",
            model="test-model",
        )

    assert attempts == 2
    assert len(llm_client._model_call_log()) == 2


def test_json_retry_metadata_preserves_first_response_validity_and_variant_budget(
    monkeypatch,
) -> None:
    responses = iter(
        [
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))],
                usage=None,
            ),
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"variants":[{},{}]}')
                    )
                ],
                usage=None,
            ),
        ]
    )
    captured_messages = []

    def fake_create(client, **kwargs):
        captured_messages.append(kwargs["messages"])
        return next(responses)

    monkeypatch.setenv("ALGOLAB_LLM_JSON_RETRIES", "1")
    monkeypatch.setattr(llm_client, "get_client", lambda: object())
    monkeypatch.setattr(llm_client, "_create_chat_completion_with_retry", fake_create)
    monkeypatch.setattr(llm_client._MODEL_CALL_STATE, "calls", [], raising=False)

    result = llm_client.chat_json_with_metadata(
        "system prompt",
        "Required number of solution variants: 2",
        model="test-model",
    )

    assert result["content"] == {"variants": [{}, {}]}
    calls = llm_client._model_call_log()
    assert [(call["json_attempt"], call["json_valid"]) for call in calls] == [
        (0, False),
        (1, True),
    ]
    retry_text = captured_messages[1][1]["content"]
    assert "保留 1 个 variant" not in retry_text
    assert "保持用户提示中要求的 variant 数量" in retry_text
