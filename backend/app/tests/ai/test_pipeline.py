import pytest

from app.ai.orchestrator.pipeline import AIOrchestrator
from app.ai.validators.query_validator import query_validator


class TestQueryValidator:
    def test_rejects_non_legal_query(self):
        is_legal, confidence, reason = query_validator.is_legal_query("What is the weather?")
        assert is_legal is False
        assert confidence < 0.5

    def test_accepts_bns_query(self):
        is_legal, confidence, reason = query_validator.is_legal_query("What is theft under BNS?")
        assert is_legal is True

    def test_accepts_legal_procedure_query(self):
        is_legal, confidence, reason = query_validator.is_legal_query("How to file an FIR?")
        assert is_legal is True

    def test_greeting_detected(self):
        msg = query_validator.get_greeting_response()
        assert len(msg) > 0

    def test_rejection_message(self):
        msg = query_validator.get_rejection_message("What is the stock market?")
        assert len(msg) > 0


class TestAIOrchestrator:
    @pytest.mark.asyncio
    async def test_orchestrator_initializes(self):
        orch = AIOrchestrator()
        assert orch.classifier is not None

    @pytest.mark.asyncio
    async def test_orchestrator_validates_non_legal(self):
        orch = AIOrchestrator()
        result = await orch.process("What is the weather?")
        assert result["response"] != ""
        assert result["steps"]["validation"]["rejected"] is True
