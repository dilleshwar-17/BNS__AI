import pytest
from app.ai.drafting.orchestrator import orchestrator
from app.ai.drafting.questionnaire import questionnaire
from app.ai.drafting.template_registry import template_registry
from app.ai.validators.query_validator import QueryValidator


def test_template_registry_loads_legal_notice():
    tpl = template_registry.get("legal_notice")
    assert tpl is not None
    assert "title" in tpl or "template" in tpl


def test_questionnaire_definition_legal_notice():
    qdef = questionnaire.get_definitions("legal_notice")
    assert qdef is not None
    assert "groups" in qdef


def test_query_validator_bns():
    validator = QueryValidator()
    valid, conf, msg = validator.is_legal_query("What is the penalty for theft under Section 303 BNS?")
    assert valid is True

    valid_non_legal, _, _ = validator.is_legal_query("How do I bake a chocolate cake recipe?")
    assert valid_non_legal is False


@pytest.mark.asyncio
async def test_orchestrator_pipeline_dry_run():
    result = await orchestrator.run_pipeline(
        "legal_notice",
        {
            "sender_name": "Ramesh Kumar",
            "recipient_name": "Suresh Verma",
            "subject": "Notice for breach of contract",
        },
    )
    assert result is not None
    assert "content" in result or "error" in result
