"""Kick OAuth 2.1 authorization-code + PKCE flow for a local desktop app."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Mapping, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

import httpx


AUTHORIZE_URL = "https://id.kick.com/oauth/authorize"
TOKEN_URL = "https://id.kick.com/oauth/token"
DEFAULT_REDIRECT_URI = "http://localhost:8765/callback"


class OAuthError(RuntimeError):
    """A safe-to-display OAuth failure that does not contain credentials."""


@dataclass(frozen=True)
class AuthorizationRequest:
    url: str
    state: str
    code_verifier: str


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: float
    scope: str


@dataclass(frozen=True)
class AppAccessToken:
    access_token: str
    expires_at: float


class TokenCredentialStore(Protocol):
    def save(self, key: str, secret: str) -> None: ...

    def load(self, key: str) -> str | None: ...


def authorization_code_from_callback(callback_url: str, expected_state: str) -> str:
    """Validate the loopback callback and extract its authorization code."""
    parsed = urlparse(callback_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "localhost"
        or parsed.port != 8765
        or parsed.path != "/callback"
    ):
        raise OAuthError("Invalid local OAuth callback URL")

    parameters = parse_qs(parsed.query, keep_blank_values=True)
    returned_state = parameters.get("state", [""])[0]
    if not hmac.compare_digest(returned_state, expected_state):
        raise OAuthError("OAuth state validation failed")
    if parameters.get("error"):
        raise OAuthError("Kick authorization was not completed")

    code = parameters.get("code", [""])[0]
    if not code:
        raise OAuthError("OAuth callback did not include an authorization code")
    return code


class _LocalOAuthCallback:
    def __init__(self, expected_state: str, redirect_uri: str) -> None:
        parsed = urlparse(redirect_uri)
        if parsed.hostname != "localhost" or parsed.port is None or parsed.path != "/callback":
            raise OAuthError("OAuth redirect must use a localhost callback on /callback")
        self.expected_state = expected_state
        self.redirect_uri = redirect_uri
        self._event = threading.Event()
        self._code: str | None = None
        self._error: OAuthError | None = None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        callback = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed_request = urlparse(self.path)
                if parsed_request.path != "/callback":
                    self.send_error(404)
                    return

                callback_url = f"{callback.redirect_uri}?{parsed_request.query}"
                try:
                    callback._code = authorization_code_from_callback(
                        callback_url,
                        callback.expected_state,
                    )
                    body = b"Authorization complete. You can return to BotCapturar."
                    status = 200
                except OAuthError as error:
                    callback._error = error
                    body = b"Authorization could not be completed. Return to BotCapturar."
                    status = 400

                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                callback._event.set()

            def log_message(self, format: str, *args: object) -> None:
                return

        parsed = urlparse(self.redirect_uri)
        try:
            self._server = ThreadingHTTPServer((parsed.hostname or "localhost", parsed.port or 8765), Handler)
        except OSError as error:
            raise OAuthError("Unable to start the local OAuth callback; port 8765 may be in use") from error
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, name="kick-oauth-callback", daemon=True)
        self._thread.start()

    def wait_for_code(self, timeout: float) -> str:
        if not self._event.wait(timeout):
            raise OAuthError("Kick authorization timed out")
        if self._error is not None:
            raise self._error
        if self._code is None:
            raise OAuthError("OAuth callback did not include an authorization code")
        return self._code

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)


class OAuthClient:
    """Obtains and refreshes user access tokens for Kick's Public API."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
        http_client: httpx.Client | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not client_id.strip():
            raise ValueError("client_id must not be empty")
        if not client_secret:
            raise ValueError("client_secret must not be empty")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._http_client = http_client or httpx.Client(timeout=15.0)
        self._owns_client = http_client is None
        self._clock = clock

    def build_authorization_request(
        self,
        *,
        state: str | None = None,
        code_verifier: str | None = None,
    ) -> AuthorizationRequest:
        state = state or secrets.token_urlsafe(32)
        code_verifier = code_verifier or secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        query = urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": "chat:write",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return AuthorizationRequest(f"{AUTHORIZE_URL}?{query}", state, code_verifier)

    def authorize(
        self,
        *,
        open_browser: Callable[[str], bool] = webbrowser.open,
        timeout: float = 180,
    ) -> OAuthTokens:
        request = self.build_authorization_request()
        callback = _LocalOAuthCallback(request.state, self.redirect_uri)
        callback.start()
        try:
            if not open_browser(request.url):
                raise OAuthError("Could not open the system browser for Kick authorization")
            code = callback.wait_for_code(timeout)
            return self.exchange_code(code, request.code_verifier)
        finally:
            callback.close()

    def exchange_code(self, code: str, code_verifier: str) -> OAuthTokens:
        return self._request_tokens(
            {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
                "code": code,
            }
        )

    def get_app_access_token(self) -> AppAccessToken:
        """Obtain a short-lived token for public channel metadata lookups."""
        try:
            response = self._http_client.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
        except httpx.RequestError as error:
            raise OAuthError("Unable to reach Kick OAuth") from error
        if response.is_error:
            raise OAuthError("Kick OAuth rejected the app token request")

        try:
            payload = response.json()
            access_token = payload["access_token"]
            expires_in = float(payload["expires_in"])
            if not isinstance(access_token, str) or not access_token or expires_in <= 0:
                raise ValueError("invalid app token")
            return AppAccessToken(access_token, self._clock() + expires_in)
        except (KeyError, TypeError, ValueError) as error:
            raise OAuthError("Kick OAuth returned an invalid app token response") from error

    def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        tokens = self._request_tokens(
            {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
            },
            refresh_token_fallback=refresh_token,
            scope_fallback="chat:write",
        )
        return tokens

    def close(self) -> None:
        if self._owns_client:
            self._http_client.close()

    def _request_tokens(
        self,
        form: Mapping[str, str],
        *,
        refresh_token_fallback: str = "",
        scope_fallback: str = "",
    ) -> OAuthTokens:
        try:
            response = self._http_client.post(TOKEN_URL, data=form)
        except httpx.RequestError as error:
            raise OAuthError("Unable to reach Kick OAuth") from error
        if response.is_error:
            raise OAuthError("Kick OAuth rejected the token request")

        try:
            payload = response.json()
            access_token = payload["access_token"]
            expires_in = float(payload["expires_in"])
            refresh_token = payload.get("refresh_token", refresh_token_fallback)
            scope = payload.get("scope") or scope_fallback
            if not isinstance(access_token, str) or not access_token:
                raise ValueError("missing access token")
            if not isinstance(refresh_token, str) or not refresh_token:
                raise ValueError("invalid refresh token")
            if not isinstance(scope, str):
                raise ValueError("invalid scope")
            if expires_in <= 0:
                raise ValueError("invalid expiry")
        except (KeyError, TypeError, ValueError) as error:
            raise OAuthError("Kick OAuth returned an invalid token response") from error
        if "chat:write" not in scope.split():
            raise OAuthError("Kick authorization did not grant the required chat:write scope")
        return OAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=self._clock() + expires_in,
            scope=scope,
        )


class OAuthTokenManager:
    """Persist OAuth tokens and refresh them before they expire."""

    def __init__(
        self,
        oauth_client: OAuthClient,
        credential_store: TokenCredentialStore,
        *,
        clock: Callable[[], float] = time.time,
        refresh_skew_seconds: float = 60,
    ) -> None:
        self._oauth_client = oauth_client
        self._credential_store = credential_store
        self._clock = clock
        self._refresh_skew_seconds = refresh_skew_seconds

    def authorize(self) -> OAuthTokens:
        tokens = self._oauth_client.authorize()
        self._save_tokens(tokens)
        return tokens

    def get_access_token(self) -> str:
        access_token = self._credential_store.load("oauth.access_token")
        refresh_token = self._credential_store.load("oauth.refresh_token")
        expires_at_value = self._credential_store.load("oauth.expires_at")
        if not access_token or not refresh_token or not expires_at_value:
            raise OAuthError("Authorize BotCapturar with Kick before starting")
        try:
            expires_at = float(expires_at_value)
        except ValueError as error:
            raise OAuthError("Stored Kick authorization is invalid; authorize again") from error

        if self._clock() < expires_at - self._refresh_skew_seconds:
            return access_token

        tokens = self._oauth_client.refresh_access_token(refresh_token)
        self._save_tokens(tokens)
        return tokens.access_token

    def _save_tokens(self, tokens: OAuthTokens) -> None:
        self._credential_store.save("oauth.access_token", tokens.access_token)
        self._credential_store.save("oauth.refresh_token", tokens.refresh_token)
        self._credential_store.save("oauth.expires_at", str(tokens.expires_at))
        self._credential_store.save("oauth.scope", tokens.scope)
