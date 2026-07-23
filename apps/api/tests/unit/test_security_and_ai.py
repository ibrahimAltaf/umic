"""Unit tests for security helpers and rule engine."""

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.ai.provider import ConfidenceLevel, RuleEngineAIProvider


def test_password_hash_roundtrip():
    hashed = hash_password("SecurePass123!")
    assert hashed != "SecurePass123!"
    assert verify_password("SecurePass123!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="00000000-0000-0000-0000-000000000001")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["type"] == "access"


def test_rule_engine_exact_claim_match():
    provider = RuleEngineAIProvider()
    result = provider.associate_matter(
        signals={"claim_number": "CLM-100"},
        candidates=[
            {"id": "m1", "claim_number": "CLM-100"},
            {"id": "m2", "claim_number": "CLM-999"},
        ],
    )
    assert result.suggested_primary_matter_id == "m1"
    assert result.confidence_level in {
        ConfidenceLevel.MEDIUM,
        ConfidenceLevel.HIGH,
        ConfidenceLevel.LOW,
    }
    assert result.evidence


def test_rule_engine_no_match():
    provider = RuleEngineAIProvider()
    result = provider.associate_matter(
        signals={"claim_number": "NONE"},
        candidates=[{"id": "m1", "claim_number": "CLM-100"}],
    )
    assert result.confidence_level == ConfidenceLevel.NO_MATCH
