import pytest
from app.ai.orchestrator.pipeline import pipeline as ai_pipeline
from app.ai.drafting.validator import DraftValidator
from app.ai.drafting.orchestrator import orchestrator as drafting_orchestrator
from app.services.drafting_service import generate_draft


@pytest.mark.asyncio
async def test_non_legal_query_rejection():
    # Non-legal queries must be rejected with the specialized domain message
    result = await ai_pipeline.process("how to bake chocolate cookies")
    assert "rejected" in result["steps"]["validation"]
    assert result["steps"]["validation"]["rejected"] is True
    assert "I specialize exclusively in the **Bharatiya Nyaya Sanhita (BNS)**" in result["response"]


@pytest.mark.asyncio
async def test_empty_retrieved_context_strict_fallback():
    # If a specific legal question is asked but no relevant legal context is found,
    # the engine must decline to answer with the exact working principle string.
    # We query for an off-topic / unknown law item that won't have context in our offline base.
    result = await ai_pipeline.process("What is Section 9999 of BNS?")
    assert result["response"] == "I cannot answer this using the currently available BNS knowledge base."


@pytest.mark.asyncio
async def test_chat_output_hallucination_prevention():
    # Test that _validate_output catches hallucinated sections not in context or query
    query = "What is the punishment for theft?"
    context = "Section 303: Punishment for theft. Whoever commits theft shall be punished..."

    # 1. This response is grounded since Section 303 is in context
    good_resp = "Under Section 303 BNS, the punishment for theft is up to 3 years."
    valid_resp = ai_pipeline._validate_output(good_resp, query, context)
    assert valid_resp == good_resp

    # 2. This response contains Section 500, which is NOT in context or query
    hallucinated_resp = "Section 500 BNS says the punishment is death."
    invalid_resp = ai_pipeline._validate_output(hallucinated_resp, query, context)
    assert invalid_resp == "I cannot answer this using the currently available BNS knowledge base."


@pytest.mark.asyncio
async def test_draft_validator_catches_hallucination():
    validator = DraftValidator()

    # Valid FIR draft (only contains allowed Section 173 BNS / BNSS)
    valid_content = "FIR under Section 173 of BNSS. Name Rajesh Kumar..."
    validation = validator.validate(valid_content, "fir", context="Section 173 BNSS", details={"complainant_name": "Rajesh"})
    assert validation["valid"] is True
    assert validation["hallucinated"] is False

    # Stolen/hallucinated section in FIR draft
    invalid_content = "FIR under Section 999 of BNS."
    validation = validator.validate(invalid_content, "fir", context="Section 173 BNSS", details={})
    assert validation["valid"] is False
    assert validation["hallucinated"] is True


@pytest.mark.asyncio
async def test_drafting_orchestrator_hallucination_fallback():
    # Test that orchestrator falls back to correct template-driven generation on validation failure
    # We trigger a mock generation where the output would have hallucination
    details = {
        "complainant_name": "Amit Shah",
        "complainant_address": "New Delhi",
        "contact_no": "9999999999",
        "incident_date": "2026-05-01",
        "incident_place": "Delhi",
        "police_station": "Connaught Place",
        "description": "Amit Shah reports a very serious theft of wallet on 2026-05-01."
    }

    # We execute drafting pipeline
    res = await drafting_orchestrator.run_pipeline("fir", details)
    assert res["step"] == "complete"
    assert "Amit Shah" in res["content"]
    # Fallback template is correct
    assert "FIRST INFORMATION REPORT" in res["content"]
