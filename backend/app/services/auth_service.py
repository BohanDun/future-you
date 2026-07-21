"""Authentication dependency for local demo mode and Amazon Cognito."""

import logging
import os
import ssl
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import certifi
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

logger = logging.getLogger(__name__)

AUTH_MODE = os.getenv("AUTH_MODE", "mock").strip().lower()
AWS_REGION = os.getenv("AWS_REGION_NAME", "ap-southeast-2")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "").strip()
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "").strip()

_bearer = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(_bearer),
]


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None = None


def _issuer() -> str:
    if not COGNITO_USER_POOL_ID or not COGNITO_APP_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cognito authentication is not configured",
        )
    return f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return PyJWKClient(
        f"{_issuer()}/.well-known/jwks.json",
        ssl_context=ssl_context,
    )


def _decode_access_token(token: str) -> dict[str, Any]:
    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=_issuer(),
            options={"verify_aud": False},
        )
    except (PyJWTError, ValueError) as exc:
        logger.warning("Cognito access token validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        ) from exc

    if claims.get("token_use") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="An access token is required",
        )
    if claims.get("client_id") != COGNITO_APP_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token was issued for a different client",
        )
    if not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has no subject",
        )
    return claims


def get_current_user(credentials: BearerCredentials) -> AuthenticatedUser:
    if AUTH_MODE != "cognito":
        return AuthenticatedUser(user_id="alex", email="alex@example.com")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    claims = _decode_access_token(credentials.credentials)
    return AuthenticatedUser(
        user_id=str(claims["sub"]),
        email=claims.get("email"),
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
