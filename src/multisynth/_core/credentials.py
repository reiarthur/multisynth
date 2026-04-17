"""Lazy credential resolution for module helpers and client instances."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from .config import KNOWN_CREDENTIAL_ENV_VARS


@dataclass(frozen=True, slots=True)
class CredentialStore:
    """Resolves credentials from explicit overrides first, then environment."""

    explicit: dict[str, str] = field(default_factory=dict)

    def resolve(self, env_name: str) -> str | None:
        if env_name in self.explicit:
            value = self.explicit[env_name]
            return value if value else None
        value = os.getenv(env_name)
        return value if value else None

    def merged(self, overrides: Mapping[str, str] | None = None) -> CredentialStore:
        if not overrides:
            return self
        merged = dict(self.explicit)
        merged.update({key: value for key, value in overrides.items() if value})
        return CredentialStore(merged)

    def snapshot(self) -> dict[str, str]:
        return {
            env_name: value
            for env_name in KNOWN_CREDENTIAL_ENV_VARS
            if (value := self.resolve(env_name))
        }


def make_credential_store(credentials: Mapping[str, str] | None = None) -> CredentialStore:
    """Create a credential store from explicit overrides."""

    return CredentialStore(dict(credentials or {}))


def ensure_credential_store(
    credentials: Mapping[str, str] | CredentialStore | None = None,
) -> CredentialStore:
    """Normalize mappings and stores into a CredentialStore instance."""

    if isinstance(credentials, CredentialStore):
        return credentials
    return make_credential_store(credentials)
