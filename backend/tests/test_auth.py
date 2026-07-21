from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import auth_service


def test_cognito_access_token_claims_are_validated(monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "COGNITO_USER_POOL_ID", "pool-id")
    monkeypatch.setattr(auth_service, "COGNITO_APP_CLIENT_ID", "client-id")
    monkeypatch.setattr(
        auth_service,
        "_jwk_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key="public-key")
        ),
    )
    monkeypatch.setattr(
        auth_service.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "user-123",
            "client_id": "client-id",
            "token_use": "access",
        },
    )

    claims = auth_service._decode_access_token("token")

    assert claims["sub"] == "user-123"


def test_cognito_rejects_token_for_another_app_client(monkeypatch) -> None:
    monkeypatch.setattr(auth_service, "COGNITO_USER_POOL_ID", "pool-id")
    monkeypatch.setattr(auth_service, "COGNITO_APP_CLIENT_ID", "expected-client")
    monkeypatch.setattr(
        auth_service,
        "_jwk_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key="public-key")
        ),
    )
    monkeypatch.setattr(
        auth_service.jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "user-123",
            "client_id": "different-client",
            "token_use": "access",
        },
    )

    with pytest.raises(HTTPException) as error:
        auth_service._decode_access_token("token")

    assert error.value.status_code == 401
