"""Credential storage backed by the Windows Credential Manager."""

from __future__ import annotations

from typing import Protocol


SERVICE_NAME = "BotCapturar"


class CredentialStoreError(RuntimeError):
    """A safe-to-display failure from the operating-system credential store."""


class KeyringBackend(Protocol):
    def set_password(self, service: str, username: str, password: str) -> None: ...

    def get_password(self, service: str, username: str) -> str | None: ...

    def delete_password(self, service: str, username: str) -> None: ...


class CredentialStore:
    """Read and write application secrets without creating plaintext files."""

    def __init__(self, *, backend: KeyringBackend | None = None) -> None:
        if backend is None:
            try:
                import keyring
            except ImportError as error:
                raise CredentialStoreError("Install the keyring package to use secure credential storage") from error

            selected_backend = keyring.get_keyring()
            backend_type = type(selected_backend)
            if backend_type.__module__ != "keyring.backends.Windows" or backend_type.__name__ != "WinVaultKeyring":
                raise CredentialStoreError("Windows Credential Manager is unavailable; refusing insecure storage")
            backend = keyring
        self._backend = backend

    def save(self, key: str, secret: str) -> None:
        if not key.strip():
            raise ValueError("key must not be empty")
        if not secret:
            raise ValueError("secret must not be empty")
        try:
            self._backend.set_password(SERVICE_NAME, key, secret)
        except Exception:
            raise CredentialStoreError("Unable to save the credential to Windows Credential Manager") from None

    def load(self, key: str) -> str | None:
        if not key.strip():
            raise ValueError("key must not be empty")
        try:
            return self._backend.get_password(SERVICE_NAME, key)
        except Exception:
            raise CredentialStoreError("Unable to read the credential from Windows Credential Manager") from None

    def delete(self, key: str) -> None:
        if not key.strip():
            raise ValueError("key must not be empty")
        try:
            if self._backend.get_password(SERVICE_NAME, key) is not None:
                self._backend.delete_password(SERVICE_NAME, key)
        except Exception:
            raise CredentialStoreError("Unable to delete the credential from Windows Credential Manager") from None
