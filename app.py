# SPDX-License-Identifier: Apache-2.0
"""Delegatable auth plugin -- capability tokens with cascading revocation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, cast

from local_types import AgentId, AuthContext, Token

DEFAULT_TTL_SECONDS = 3600.0


class DelegationError(ValueError):
    """Base class for delegation-specific auth failures."""


class ScopeEscalationError(DelegationError):
    """Raised when a delegated token would carry scopes its parent lacks."""

    def __init__(self, requested: list[str], allowed: list[str]) -> None:
        self.requested = requested
        self.allowed = allowed
        excess = sorted(set(requested) - set(allowed))
        super().__init__(f"delegated scopes {excess} exceed parent scopes {sorted(allowed)}")


class ExcessiveTtlError(DelegationError):
    """Raised when a delegated token's expiry would outlive its parent's."""

    def __init__(self, child_expires_at: float, parent_expires_at: float) -> None:
        self.child_expires_at = child_expires_at
        self.parent_expires_at = parent_expires_at
        super().__init__(
            f"child expiry {child_expires_at} exceeds parent expiry {parent_expires_at}"
        )


class RevokedAncestorError(DelegationError):
    """Raised when a token, or any ancestor in its delegation chain, was revoked."""

    def __init__(self, token_id: str) -> None:
        self.token_id = token_id
        super().__init__(f"token {token_id!r} was revoked (directly or via an ancestor)")


class AudienceMismatchError(DelegationError):
    """Raised when a token is presented by an agent other than its declared audience."""

    def __init__(self, expected: AgentId, presented_by: AgentId) -> None:
        self.expected = expected
        self.presented_by = presented_by
        super().__init__(f"token issued to {expected!r} was presented by {presented_by!r}")


def _canonical(claims: dict[str, Any]) -> str:
    """Canonical JSON encoding of a claims dict, used as the HMAC message."""
    return json.dumps(claims, sort_keys=True)


class DelegatableAuth:
    """Capability-token auth with delegation and cascading revocation."""

    def __init__(
        self,
        secret: bytes = b"nest-default-secret",
        clock: float | None = None,
    ) -> None:
        self._secret = secret
        self._clock = clock
        self._revoked: set[str] = set()

    def _now(self) -> float:
        if self._clock is not None:
            return self._clock
        return time.time()

    def _mac(self, key: bytes, claims: dict[str, Any]) -> str:
        return hmac.new(key, _canonical(claims).encode(), hashlib.sha256).hexdigest()

    def _token_id(self, claims: dict[str, Any]) -> str:
        return hashlib.sha256(_canonical(claims).encode()).hexdigest()

    async def issue(self, subject: AgentId, scopes: list[str]) -> Token:
        """Issue a root token for ⁠ subject ⁠ with ⁠ scopes ⁠."""
        now = self._now()
        claims: dict[str, Any] = {
            "subject": str(subject),
            "scopes": list(scopes),
            "iat": now,
            "exp": now + DEFAULT_TTL_SECONDS,
            "parent_id": None,
        }
        claims["token_id"] = self._token_id(claims)
        claims["mac"] = self._mac(self._secret, claims)
        return Token(json.dumps({"chain": [claims]}, sort_keys=True))

    async def delegate(
        self,
        parent_token: Token,
        audience: AgentId,
        scopes_subset: list[str],
        ttl: float,
    ) -> Token:
        """Mint a child token narrower than ⁠ parent_token ⁠, without the issuer."""
        parent_chain = self._verify_chain(parent_token, presented_by=None)
        parent_leaf = parent_chain[-1]
        parent_scopes: list[str] = cast("list[str]", parent_leaf["scopes"])

        requested = set(scopes_subset)
        if not requested.issubset(parent_scopes):
            raise ScopeEscalationError(list(scopes_subset), parent_scopes)

        now = self._now()
        child_expires_at = now + ttl
        parent_expires_at = cast("float", parent_leaf["exp"])
        if child_expires_at > parent_expires_at:
            raise ExcessiveTtlError(child_expires_at, parent_expires_at)

        claims: dict[str, Any] = {
            "subject": str(audience),
            "scopes": list(scopes_subset),
            "iat": now,
            "exp": child_expires_at,
            "parent_id": parent_leaf["token_id"],
        }
        claims["token_id"] = self._token_id(claims)
        parent_key = bytes.fromhex(cast("str", parent_leaf["mac"]))
        claims["mac"] = self._mac(parent_key, claims)

        new_chain = [*parent_chain, claims]
        return Token(json.dumps({"chain": new_chain}, sort_keys=True))

    async def verify(self, token: Token, *, presented_by: AgentId | None = None) -> AuthContext:
        """Verify a (possibly delegated) token and return its context."""
        chain = self._verify_chain(token, presented_by=presented_by)
        leaf = chain[-1]
        return AuthContext(
            subject=AgentId(cast("str", leaf["subject"])),
            scopes=cast("list[str]", leaf["scopes"]),
            issued_at=cast("float", leaf["iat"]),
            expires_at=cast("float", leaf["exp"]),
        )

    async def revoke(self, token: Token) -> None:
        """Revoke a token, invalidating it and everything delegated from it."""
        chain = self._parse_chain(token)
        self._revoked.add(cast("str", chain[-1]["token_id"]))

    def _parse_chain(self, token: Token) -> list[dict[str, Any]]:
        """Parse the JSON delegation chain out of a token without verifying it."""
        try:
            loaded = json.loads(str(token))
        except (json.JSONDecodeError, ValueError) as exc:
            msg = "Invalid token format"
            raise ValueError(msg) from exc
        if not isinstance(loaded, dict):
            msg = "Invalid token format"
            raise ValueError(msg)
        data = cast("dict[str, Any]", loaded)
        chain = data.get("chain")
        if not isinstance(chain, list) or not chain:
            msg = "Invalid token format"
            raise ValueError(msg)
        return cast("list[dict[str, Any]]", chain)

    def _verify_chain(
        self, token: Token, *, presented_by: AgentId | None
    ) -> list[dict[str, Any]]:
        """Verify HMAC integrity, expiry, and revocation across the whole chain."""
        chain = self._parse_chain(token)

        key = self._secret
        for link in chain:
            claims = {k: v for k, v in link.items() if k != "mac"}
            expected = self._mac(key, claims)
            actual = cast("str", link.get("mac", ""))
            if not hmac.compare_digest(expected, actual):
                msg = "Invalid token signature"
                raise ValueError(msg)
            token_id = cast("str", link["token_id"])
            if token_id in self._revoked:
                raise RevokedAncestorError(token_id)
            key = bytes.fromhex(actual)

        leaf = chain[-1]
        if cast("float", leaf["exp"]) < self._now():
            msg = "Token has expired"
            raise ValueError(msg)

        if presented_by is not None and str(presented_by) != leaf["subject"]:
            raise AudienceMismatchError(AgentId(cast("str", leaf["subject"])), presented_by)

        return chain
        # --- WEBSERVER WRAPPER FOR RAILWAY ---
import os
from fastapi import FastAPI

app = FastAPI()
auth_system = DelegatableAuth()  # Initializes your class instance

@app.get("/health")
def health():
    return {"status": "healthy", "plugin": "delegatable-auth"}

# You can add more routing endpoints here later if your assignment needs them!

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

