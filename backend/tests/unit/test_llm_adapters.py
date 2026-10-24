"""EN-06 provider adapters without network: request shape, streaming parse, error mapping."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from chatdocs.adapters.llm.anthropic_adapter import FALLBACK_BETA, AnthropicAnswerGenerator
from chatdocs.adapters.llm.fake import FakeAnswerGenerator
from chatdocs.adapters.llm.openai_compatible import OpenAICompatibleGenerator
from chatdocs.adapters.llm.resilient import RetryableProviderError
from chatdocs.domain.ids import uuid7
from chatdocs.domain.qa.prompt import Prompt
from chatdocs.domain.retrieval.rrf import Candidate
from chatdocs.ports.answer_generator import GenerationStats, GenerationUnavailable

PROMPT = Prompt("answer_v1", "system", "<doan>...</doan>\nCâu hỏi: Giá?", [])


async def drain(gen, prompt=PROMPT, cancel=None):
    stats = GenerationStats()
    out = [p async for p in gen.stream(prompt, cancel or asyncio.Event(), stats)]
    return out, stats


def test_anthropic_request_shape():
    gen = AnthropicAnswerGenerator(model="claude-sonnet-5-5", api_key="test", max_output_tokens=800)
    req = gen._request(PROMPT)
    assert req["model"] == "claude-sonnet-5-5" and req["max_tokens"] == 800 and req["system"] == "system"
    assert req["messages"] == [{"role": "user", "content": PROMPT.user}]
    assert req["output_config"] == {"effort": "low"}
    assert "temperature" not in req  # rejected by current models
    assert req["betas"] == [FALLBACK_BETA] and req["fallbacks"] == "default"
    no_fb = AnthropicAnswerGenerator(model="m", api_key="t", refusal_fallback=False)._request(PROMPT)
    assert "fallbacks" not in no_fb and "betas" not in no_fb


@pytest.mark.parametrize(("status", "retryable"), [(429, True), (503, True), (529, True), (400, False), (401, False)])
async def test_anthropic_error_mapping(status, retryable, monkeypatch):
    import anthropic

    gen = AnthropicAnswerGenerator(model="m", api_key="t", refusal_fallback=False)
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, request=request, json={"error": {"type": "x", "message": "boom"}})
    cls = anthropic.RateLimitError if status == 429 else anthropic.APIStatusError

    def fail(**kwargs):
        raise cls("boom", response=response, body=None)

    monkeypatch.setattr(gen._client.messages, "stream", fail)
    expected = RetryableProviderError if retryable else GenerationUnavailable
    with pytest.raises(expected):
        await drain(gen)


def sse_body(pieces, usage=True):
    lines = []
    for p in pieces:
        lines.append("data: " + json.dumps({"choices": [{"delta": {"content": p}}]}))
    if usage:
        lines.append("data: " + json.dumps({"choices": [], "usage": {"prompt_tokens": 120, "completion_tokens": 7}}))
    lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode()


async def test_openai_compatible_streams_and_counts_tokens():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, content=sse_body(["Thanh ", "toán [1]"]))

    gen = OpenAICompatibleGenerator(
        base_url="http://vllm:8000", model="qwen", api_key="k", transport=httpx.MockTransport(handler)
    )
    out, stats = await drain(gen)
    assert out == ["Thanh ", "toán [1]"] and (stats.input_tokens, stats.output_tokens) == (120, 7)
    assert seen["body"]["stream"] is True and seen["body"]["temperature"] == 0
    assert seen["body"]["messages"][0] == {"role": "system", "content": "system"} and seen["auth"] == "Bearer k"


@pytest.mark.parametrize(
    ("status", "exc"), [(503, RetryableProviderError), (429, RetryableProviderError), (400, GenerationUnavailable)]
)
async def test_openai_compatible_errors(status, exc):
    gen = OpenAICompatibleGenerator(
        base_url="http://vllm:8000", model="m", transport=httpx.MockTransport(lambda r: httpx.Response(status))
    )
    with pytest.raises(exc):
        await drain(gen)


async def test_openai_compatible_connection_error_is_retryable():
    def boom(request):
        raise httpx.ConnectError("refused")

    gen = OpenAICompatibleGenerator(base_url="http://vllm:8000", model="m", transport=httpx.MockTransport(boom))
    with pytest.raises(RetryableProviderError):
        await drain(gen)


async def test_fake_answers_from_context_and_honours_cancel():
    c = Candidate(uuid7(), uuid7(), 3, "Thanh toán 30% khi ký. Phần còn lại khi nghiệm thu.")
    prompt = Prompt("v1", "Trả lời bằng tiếng Việt.", "Câu hỏi: thanh toán?", [c])
    gen = FakeAnswerGenerator(piece_chars=5)
    out, stats = await drain(gen, prompt)
    assert "".join(out) == "Theo tài liệu: Thanh toán 30% khi ký. [1]" and stats.model_id == "fake-llm"
    cancel = asyncio.Event()
    cancel.set()
    out, _ = await drain(gen, prompt, cancel)
    assert out == []
