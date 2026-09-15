"""Solid-OIDC authentication for Solid catalog pushes."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
import threading
from urllib.parse import urlsplit, urlunsplit
from dataclasses import dataclass, field
from typing import Any

import httpx
import jwt
from fastapi import Request

logger = logging.getLogger(__name__)


class SolidAuthError(RuntimeError):
    def __init__(self, error: str, detail: str, status_code: int = 401) -> None:
        super().__init__(detail)
        self.error = error
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class AuthenticatedSolidUser:
    webid: str
    auth_mode: str


class SolidAuth:
    def authenticate(
        self,
        request: Request,
        *,
        declared_participant_id: str | None = None,
    ) -> AuthenticatedSolidUser:
        raise NotImplementedError


@dataclass
class TrustedHeaderSolidAuth(SolidAuth):
    def __post_init__(self) -> None:
        logger.warning(
            "SOLID_AUTH_MODE=trusted-header is enabled. This trusts X-Participant-Id "
            "and is only appropriate for local development."
        )

    def authenticate(
        self,
        request: Request,
        *,
        declared_participant_id: str | None = None,
    ) -> AuthenticatedSolidUser:
        webid = (declared_participant_id or "").strip()
        if not webid:
            raise SolidAuthError(
                "missing_participant",
                "X-Participant-Id or participant_id is required in trusted-header mode",
            )
        return AuthenticatedSolidUser(webid=webid, auth_mode="trusted-header")


def _base64url_no_padding(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jwk_thumbprint(jwk: dict[str, Any]) -> str:
    kty = jwk.get("kty")
    if kty == "RSA":
        members = {key: jwk[key] for key in ("e", "kty", "n")}
    elif kty == "EC":
        members = {key: jwk[key] for key in ("crv", "kty", "x", "y")}
    elif kty == "OKP":
        members = {key: jwk[key] for key in ("crv", "kty", "x")}
    else:
        raise SolidAuthError("invalid_dpop_jwk", f"Unsupported DPoP JWK type: {kty}")

    canonical = json.dumps(members, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _base64url_no_padding(hashlib.sha256(canonical).digest())


@dataclass
class OidcSolidAuth(SolidAuth):
    issuer: str | None = field(default_factory=lambda: os.getenv("SOLID_OIDC_ISSUER") or None)
    audience: str | None = field(default_factory=lambda: os.getenv("SOLID_OIDC_AUDIENCE") or None)
    require_dpop: bool = field(
        default_factory=lambda: os.getenv("SOLID_AUTH_REQUIRE_DPOP", "true").lower()
        not in {"0", "false", "no"}
    )
    dpop_max_age_seconds: int = field(
        default_factory=lambda: int(os.getenv("SOLID_DPOP_MAX_AGE_SECONDS", "300"))
    )
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("SOLID_AUTH_TIMEOUT_SECONDS", "10")))
    http_client: httpx.Client | None = None

    def __post_init__(self) -> None:
        self._jwks_cache: dict[str, dict[str, Any]] = {}
        self._seen_proofs: dict[tuple[str, str], float] = {}
        self._replay_lock = threading.Lock()

    def authenticate(
        self,
        request: Request,
        *,
        declared_participant_id: str | None = None,
    ) -> AuthenticatedSolidUser:
        token, scheme = self._access_token_from_request(request)
        try:
            unverified_claims = jwt.decode(token, options={"verify_signature": False})
        except Exception as exc:
            raise SolidAuthError("invalid_token", "Malformed access token") from exc
        issuer = self.issuer
        if not issuer:
            raise SolidAuthError("issuer_not_configured", "SOLID_OIDC_ISSUER must be configured", 503)
        if unverified_claims.get("iss") != issuer:
            raise SolidAuthError("invalid_issuer", "Access token issuer is not the configured provider")

        claims = self._verify_access_token(token, issuer)
        webid = claims.get("webid") or claims.get("solid_webid")
        if not isinstance(webid, str) or not webid.startswith(("http://", "https://")):
            raise SolidAuthError("missing_webid", "Verified token does not contain a WebID claim")

        if self.require_dpop:
            if scheme != "dpop":
                raise SolidAuthError("invalid_authorization", "Use the DPoP authorization scheme")
            dpop_token = request.headers.get("DPoP")
            if not dpop_token:
                raise SolidAuthError("missing_dpop", "DPoP proof header is required")
            self._verify_dpop_proof(dpop_token, request=request, access_token_claims=claims, access_token=token)
        elif scheme == "dpop" and request.headers.get("DPoP"):
            self._verify_dpop_proof(
                request.headers["DPoP"],
                request=request,
                access_token_claims=claims,
                access_token=token,
            )

        return AuthenticatedSolidUser(webid=webid, auth_mode="oidc")

    def _client(self) -> httpx.Client:
        return self.http_client or httpx.Client(timeout=self.timeout_seconds)

    def _get_json(self, url: str) -> dict[str, Any]:
        client = self._client()
        close_client = self.http_client is None
        try:
            response = client.get(url, headers={"Accept": "application/json"})
        finally:
            if close_client:
                client.close()
        response.raise_for_status()
        return response.json()

    def _jwks_for_issuer(self, issuer: str) -> dict[str, Any]:
        if issuer not in self._jwks_cache:
            metadata = self._get_json(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
            jwks_uri = metadata.get("jwks_uri")
            if not jwks_uri:
                raise SolidAuthError("invalid_issuer", f"OIDC metadata has no jwks_uri: {issuer}")
            self._jwks_cache[issuer] = self._get_json(str(jwks_uri))
        return self._jwks_cache[issuer]

    def _key_for_token(self, token: str, issuer: str) -> Any:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        jwks = self._jwks_for_issuer(issuer)
        keys = jwks.get("keys", [])
        matches = [key for key in keys if not kid or key.get("kid") == kid]
        if not matches:
            raise SolidAuthError("unknown_key", f"No JWKS key matched kid={kid!r}")
        return jwt.PyJWK.from_dict(matches[0]).key

    def _verify_access_token(self, token: str, issuer: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                key=self._key_for_token(token, issuer),
                algorithms=["RS256", "ES256", "EdDSA"],
                issuer=issuer,
                audience=self.audience,
                options={"verify_aud": bool(self.audience), "require": ["exp", "iat", "iss"]},
            )
        except SolidAuthError:
            raise
        except Exception as exc:
            raise SolidAuthError("invalid_token", f"Access token verification failed: {exc}") from exc

    def _access_token_from_request(self, request: Request) -> tuple[str, str]:
        authorization = request.headers.get("Authorization", "")
        try:
            scheme, token = authorization.split(" ", 1)
        except ValueError as exc:
            raise SolidAuthError("missing_token", "Authorization header is required") from exc

        scheme = scheme.lower()
        if scheme not in {"bearer", "dpop"} or not token.strip():
            raise SolidAuthError("invalid_authorization", "Authorization must be Bearer or DPoP")
        return token.strip(), scheme

    def _verify_dpop_proof(
        self,
        dpop_token: str,
        *,
        request: Request,
        access_token_claims: dict[str, Any],
        access_token: str,
    ) -> None:
        try:
            header = jwt.get_unverified_header(dpop_token)
            if header.get("typ", "").lower() != "dpop+jwt":
                raise SolidAuthError("invalid_dpop", "DPoP proof typ must be dpop+jwt")
            jwk = header.get("jwk")
            if not isinstance(jwk, dict):
                raise SolidAuthError("invalid_dpop", "DPoP proof header has no public JWK")
            if any(key in jwk for key in ("d", "p", "q", "dp", "dq", "qi", "k")):
                raise SolidAuthError("invalid_dpop", "DPoP JWK must be public and asymmetric")
            proof_claims = jwt.decode(
                dpop_token,
                key=jwt.PyJWK.from_dict(jwk).key,
                algorithms=["RS256", "ES256", "EdDSA"],
                options={"verify_aud": False, "verify_iss": False},
            )
        except SolidAuthError:
            raise
        except Exception as exc:
            raise SolidAuthError("invalid_dpop", f"DPoP proof verification failed: {exc}") from exc

        public_url = os.getenv("CATALOG_PUBLIC_URL", "").rstrip("/")
        url = urlsplit(public_url + request.url.path if public_url else str(request.url))
        expected_htu = urlunsplit((url.scheme, url.netloc, url.path, "", ""))
        if proof_claims.get("htm") != request.method:
            raise SolidAuthError("invalid_dpop", "DPoP proof htm does not match request method")
        if proof_claims.get("htu") != expected_htu:
            raise SolidAuthError("invalid_dpop", "DPoP proof htu does not match request URL")
        if not isinstance(proof_claims.get("jti"), str) or not proof_claims["jti"]:
            raise SolidAuthError("invalid_dpop", "DPoP proof has no jti")

        iat = proof_claims.get("iat")
        if not isinstance(iat, int) or abs(time.time() - iat) > self.dpop_max_age_seconds:
            raise SolidAuthError("invalid_dpop", "DPoP proof iat is missing or stale")

        cnf = access_token_claims.get("cnf")
        token_thumbprint = cnf.get("jkt") if isinstance(cnf, dict) else None
        if not token_thumbprint or token_thumbprint != jwk_thumbprint(jwk):
            raise SolidAuthError("invalid_dpop", "DPoP key does not match required access token cnf.jkt")
        expected_ath = _base64url_no_padding(hashlib.sha256(access_token.encode("ascii")).digest())
        if proof_claims.get("ath") != expected_ath:
            raise SolidAuthError("invalid_dpop", "DPoP ath does not match access token")
        with self._replay_lock:
            now = time.time()
            self._seen_proofs = {key: expiry for key, expiry in self._seen_proofs.items() if expiry > now}
            proof_id = (token_thumbprint, proof_claims["jti"])
            if proof_id in self._seen_proofs:
                raise SolidAuthError("invalid_dpop", "DPoP proof has already been used")
            if len(self._seen_proofs) >= 10000:
                raise SolidAuthError("auth_capacity", "Authentication capacity reached", 503)
            self._seen_proofs[proof_id] = iat + self.dpop_max_age_seconds


def build_solid_auth_from_env() -> SolidAuth:
    mode = os.getenv("SOLID_AUTH_MODE", "oidc").strip().lower()
    if mode == "trusted-header":
        return TrustedHeaderSolidAuth()
    if mode != "oidc":
        raise RuntimeError("SOLID_AUTH_MODE must be either 'oidc' or 'trusted-header'")
    return OidcSolidAuth()

