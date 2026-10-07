from __future__ import annotations

import pytest

from botcapturar.credentials import CredentialStore, CredentialStoreError


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, key: str, secret: str) -> None:
        self.values[(service, key)] = secret

    def get_password(self, service: str, key: str) -> str | None:
        return self.values.get((service, key))

    def delete_password(self, service: str, key: str) -> None:
        del self.values[(service, key)]


def test_saves_and_loads_secret_using_application_namespace():
    keyring = FakeKeyring()
    store = CredentialStore(backend=keyring)

    store.save("oauth.refresh_token", "refresh-secret")

    assert keyring.values == {("BotCapturar", "oauth.refresh_token"): "refresh-secret"}
    assert store.load("oauth.refresh_token") == "refresh-secret"


def test_delete_removes_secret_and_is_safe_when_already_missing():
    store = CredentialStore(backend=FakeKeyring())

    store.save("oauth.access_token", "access-secret")
    store.delete("oauth.access_token")
    store.delete("oauth.access_token")

    assert store.load("oauth.access_token") is None


def test_rejects_empty_keys_and_secrets():
    store = CredentialStore(backend=FakeKeyring())

    with pytest.raises(ValueError):
        store.save("", "secret")
    with pytest.raises(ValueError):
        store.save("oauth.access_token", "")


def test_backend_failures_do_not_include_secret_values():
    class BrokenKeyring(FakeKeyring):
        def set_password(self, service: str, key: str, secret: str) -> None:
            raise RuntimeError(f"failed to store {secret}")

    store = CredentialStore(backend=BrokenKeyring())

    with pytest.raises(CredentialStoreError) as caught:
        store.save("oauth.client_secret", "do-not-leak-this")

    assert "do-not-leak-this" not in str(caught.value)
