from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from botcapturar.oauth import (
    AppAccessToken,
    OAuthClient,
    OAuthError,
    OAuthTokenManager,
    OAuthTokens,
    authorization_code_from_callback,
)


def test_builds_pkce_authorization_url_for_chat_write_scope():
    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        redirect_uri="http://localhost:8765/callback",
    )

    request = oauth.build_authorization_request(state="csrf-state", code_verifier="known-verifier")

    parsed = urlparse(request.url)
    query = parse_qs(parsed.query)
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(b"known-verifier").digest()
    ).decode("ascii").rstrip("=")
    assert parsed.scheme == "https"
    assert parsed.netloc == "id.kick.com"
    assert parsed.path == "/oauth/authorize"
    assert query == {
        "client_id": ["client-123"],
        "response_type": ["code"],
        "redirect_uri": ["http://localhost:8765/callback"],
        "scope": ["chat:write"],
        "state": ["csrf-state"],
        "code_challenge": [expected_challenge],
        "code_challenge_method": ["S256"],
    }
    assert request.code_verifier == "known-verifier"


def test_exchanges_authorization_code_for_tokens_and_expiry():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((str(request.url), dict(request.headers), request.content.decode()))
        return httpx.Response(
            200,
            json={
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": 3600,
                "scope": "chat:write",
            },
        )

    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        redirect_uri="http://localhost:8765/callback",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: 1000,
    )

    tokens = oauth.exchange_code("auth-code", "code-verifier")

    assert requests[0][0] == "https://id.kick.com/oauth/token"
    assert "application/x-www-form-urlencoded" in requests[0][1]["content-type"]
    assert "grant_type=authorization_code" in requests[0][2]
    assert "client_id=client-123" in requests[0][2]
    assert "client_secret=client-secret" in requests[0][2]
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Fcallback" in requests[0][2]
    assert "code_verifier=code-verifier" in requests[0][2]
    assert "code=auth-code" in requests[0][2]
    assert tokens.access_token == "access-1"
    assert tokens.refresh_token == "refresh-1"
    assert tokens.expires_at == 4600
    assert tokens.scope == "chat:write"


def test_obtains_app_access_token_for_public_channel_lookup():
    request_body = {}

    def handler(request: httpx.Request) -> httpx.Response:
        request_body.update(parse_qs(request.content.decode()))
        return httpx.Response(
            200,
            json={"access_token": "app-access", "expires_in": 3600, "token_type": "Bearer"},
        )

    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: 1000,
    )

    token = oauth.get_app_access_token()

    assert request_body == {
        "client_id": ["client-123"],
        "client_secret": ["client-secret"],
        "grant_type": ["client_credentials"],
    }
    assert isinstance(token, AppAccessToken)
    assert token.access_token == "app-access"
    assert token.expires_at == 4600


def test_refreshes_tokens_and_uses_new_refresh_token_when_returned():
    request_body = {}

    def handler(request: httpx.Request) -> httpx.Response:
        request_body.update(parse_qs(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "access_token": "access-2",
                "refresh_token": "refresh-2",
                "expires_in": "1800",
                "scope": "chat:write",
            },
        )

    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        redirect_uri="http://localhost:8765/callback",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=lambda: 2000,
    )

    tokens = oauth.refresh_access_token("refresh-1")

    assert request_body == {
        "client_id": ["client-123"],
        "client_secret": ["client-secret"],
        "grant_type": ["refresh_token"],
        "refresh_token": ["refresh-1"],
    }
    assert tokens.access_token == "access-2"
    assert tokens.refresh_token == "refresh-2"
    assert tokens.expires_at == 3800


def test_rejects_token_response_without_refresh_token_for_initial_authorization():
    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"access_token": "access-1", "expires_in": 3600, "scope": "chat:write"},
                )
            )
        ),
    )

    with pytest.raises(OAuthError, match="invalid token response"):
        oauth.exchange_code("auth-code", "code-verifier")


def test_rejects_oauth_grant_without_chat_write_scope():
    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "access_token": "access-1",
                        "refresh_token": "refresh-1",
                        "expires_in": 3600,
                        "scope": "user:read",
                    },
                )
            )
        ),
    )

    with pytest.raises(OAuthError, match="chat:write"):
        oauth.exchange_code("auth-code", "code-verifier")


def test_callback_requires_matching_state_and_authorization_code():
    callback_url = "http://localhost:8765/callback?code=auth-code&state=expected-state"

    assert authorization_code_from_callback(callback_url, "expected-state") == "auth-code"

    with pytest.raises(OAuthError, match="state validation failed"):
        authorization_code_from_callback(
            "http://localhost:8765/callback?code=auth-code&state=attacker-state",
            "expected-state",
        )


def test_callback_rejects_oauth_error_response():
    with pytest.raises(OAuthError, match="authorization was not completed"):
        authorization_code_from_callback(
            "http://localhost:8765/callback?error=access_denied&state=expected-state",
            "expected-state",
        )


def test_authorize_opens_browser_once_receives_loopback_code_and_exchanges_it():
    exchanged = {}

    def handler(request: httpx.Request) -> httpx.Response:
        exchanged.update(parse_qs(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "access_token": "access-from-oauth",
                "refresh_token": "refresh-from-oauth",
                "expires_in": 3600,
                "scope": "chat:write",
            },
        )

    oauth = OAuthClient(
        client_id="client-123",
        client_secret="client-secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    opened_urls = []

    def open_browser(url: str) -> bool:
        opened_urls.append(url)
        state = parse_qs(urlparse(url).query)["state"][0]
        response = httpx.get(
            "http://localhost:8765/callback",
            params={"code": "callback-code", "state": state},
            trust_env=False,
        )
        return response.status_code == 200

    tokens = oauth.authorize(open_browser=open_browser, timeout=3)

    assert len(opened_urls) == 1
    assert tokens.access_token == "access-from-oauth"
    assert exchanged["code"] == ["callback-code"]


def test_token_manager_returns_access_token_before_expiry():
    credentials = {
        "oauth.access_token": "current-access",
        "oauth.refresh_token": "current-refresh",
        "oauth.expires_at": "2000",
    }

    class Store:
        def load(self, key: str) -> str | None:
            return credentials.get(key)

        def save(self, key: str, value: str) -> None:
            credentials[key] = value

    class OAuth:
        def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
            raise AssertionError("valid access token should not be refreshed")

    manager = OAuthTokenManager(OAuth(), Store(), clock=lambda: 1000, refresh_skew_seconds=60)

    assert manager.get_access_token() == "current-access"


def test_token_manager_refreshes_expired_access_and_persists_rotated_tokens():
    credentials = {
        "oauth.access_token": "expired-access",
        "oauth.refresh_token": "old-refresh",
        "oauth.expires_at": "1000",
    }

    class Store:
        def load(self, key: str) -> str | None:
            return credentials.get(key)

        def save(self, key: str, value: str) -> None:
            credentials[key] = value

    class OAuth:
        def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
            assert refresh_token == "old-refresh"
            return OAuthTokens("new-access", "new-refresh", 5000, "chat:write")

    manager = OAuthTokenManager(OAuth(), Store(), clock=lambda: 1000)

    assert manager.get_access_token() == "new-access"
    assert credentials["oauth.access_token"] == "new-access"
    assert credentials["oauth.refresh_token"] == "new-refresh"
    assert credentials["oauth.expires_at"] == "5000"
