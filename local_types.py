"""Minimal standalone stand-ins for the nest_core types this project needs.

Avoids depending on the full nest_core package (not meant to be deployed
separately) for just three names: AgentId, AuthContext, Token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NewType

AgentId = NewType("AgentId", str)
Token = NewType("Token", str)


@dataclass
class AuthContext:
    subject: AgentId
    scopes: list[str] = field(default_factory=list)
    issued_at: float | None = None
    expires_at: float | None = None
