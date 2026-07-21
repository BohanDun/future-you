"""Create and verify short-lived, customer-bound Manage proposal tokens."""

import base64
import hashlib
import hmac
import json
import os
import time
from secrets import token_urlsafe

from pydantic import TypeAdapter, ValidationError

from app.models.agent_action import AgentOperation
from app.models.customer import CustomerProfile

_operations_adapter = TypeAdapter(list[AgentOperation])
_TOKEN_TTL_SECONDS = 10 * 60


class ProposalTokenError(ValueError):
    pass


def _signing_key() -> bytes:
    value = os.getenv("AGENT_PROPOSAL_SIGNING_KEY", "").strip()
    if len(value) < 32:
        raise ProposalTokenError(
            "AGENT_PROPOSAL_SIGNING_KEY must be configured with at least 32 characters"
        )
    return value.encode("utf-8")


def _profile_revision(profile: CustomerProfile) -> str:
    editable = profile.model_dump(include={
        "customerId",
        "currentBalance",
        "monthlyIncome",
        "monthlyExpenses",
        "goals",
    })
    canonical = json.dumps(editable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise ProposalTokenError("Invalid proposal token") from exc


def create_proposal_token(
    profile: CustomerProfile,
    operations: list[AgentOperation],
) -> str:
    payload = {
        "customerId": profile.customerId,
        "profileRevision": _profile_revision(profile),
        "expiresAt": int(time.time()) + _TOKEN_TTL_SECONDS,
        "nonce": token_urlsafe(12),
        "operations": [item.model_dump(mode="json") for item in operations],
    }
    encoded_payload = _encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    signature = _encode(
        hmac.new(_signing_key(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{encoded_payload}.{signature}"


def verify_proposal_token(
    token: str,
    profile: CustomerProfile,
) -> list[AgentOperation]:
    try:
        encoded_payload, supplied_signature = token.split(".", 1)
    except ValueError as exc:
        raise ProposalTokenError("Invalid proposal token") from exc

    expected_signature = _encode(
        hmac.new(_signing_key(), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise ProposalTokenError("Invalid proposal token")

    try:
        payload = json.loads(_decode(encoded_payload))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProposalTokenError("Invalid proposal token") from exc
    if payload.get("customerId") != profile.customerId:
        raise ProposalTokenError("This proposal belongs to a different customer")
    if payload.get("profileRevision") != _profile_revision(profile):
        raise ProposalTokenError(
            "Your profile changed after this preview was created. Please prepare it again."
        )
    if not isinstance(payload.get("expiresAt"), int) or payload["expiresAt"] < time.time():
        raise ProposalTokenError("This proposal has expired. Please prepare it again.")
    try:
        return _operations_adapter.validate_python(payload.get("operations"))
    except ValidationError as exc:
        raise ProposalTokenError("Invalid proposal token") from exc
