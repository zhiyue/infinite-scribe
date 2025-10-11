import pytest

from src.agents.orchestrator.intent_classifier import CommandIntentClassifier
from src.external.clients.llm import LLMResponse


class _StubLLMService:
    def __init__(self, response: LLMResponse | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls: list[tuple[str, str]] = []

    async def generate(self, request):
        self.calls.append((request.model, request.messages[-1].content))
        if self._error:
            raise self._error
        if self._response is None:
            raise RuntimeError("No response configured")
        return self._response


@pytest.mark.asyncio
async def test_intent_classifier_uses_llm_result():
    response = LLMResponse(content='{"intent": "feedback_generation", "confidence": 0.92}')
    service = _StubLLMService(response=response)
    classifier = CommandIntentClassifier(llm_service=service, model="test-model")

    result = await classifier.classify(
        "Command.Genesis.Session.Details.Request", {"user_input": "请帮我评价一下这段剧情"}
    )

    assert result.intent == "feedback_generation"
    assert result.source == "llm"
    assert result.confidence == pytest.approx(0.92)
    assert service.calls  # 确认确实调用了 LLM


@pytest.mark.asyncio
async def test_intent_classifier_fallback_to_heuristic_when_llm_fails():
    service = _StubLLMService(error=RuntimeError("network-error"))
    classifier = CommandIntentClassifier(llm_service=service, model="test-model")

    result = await classifier.classify(
        "Command.Genesis.Session.Details.Request", {"user_input": "请给我一些反馈建议"}
    )

    assert result.intent == "feedback_generation"
    assert result.source in {"heuristic", "fallback"}

