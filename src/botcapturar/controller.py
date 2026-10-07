"""Application orchestration between settings, OAuth, API, and scheduler."""

from __future__ import annotations

import threading
import time
from typing import Callable, Protocol

from botcapturar.credentials import CredentialStore
from botcapturar.kick_api import AuthenticationError, KickApiClient
from botcapturar.oauth import OAuthClient, OAuthError, OAuthTokenManager, OAuthTokens
from botcapturar.scheduler import MessageScheduler, SchedulerStatus


class ConfigurationError(RuntimeError):
    """Required local application configuration is missing or invalid."""


class SecretStore(Protocol):
    def save(self, key: str, secret: str) -> None: ...

    def load(self, key: str) -> str | None: ...

    def delete(self, key: str) -> None: ...


class ApplicationController:
    """Own application settings and coordinate authorization and message sends."""

    def __init__(
        self,
        credential_store: SecretStore | CredentialStore,
        *,
        oauth_client_factory: Callable[..., OAuthClient] = OAuthClient,
        api_client_factory: Callable[[], KickApiClient] = KickApiClient,
        scheduler_factory: Callable[..., MessageScheduler] = MessageScheduler,
        on_status: Callable[[SchedulerStatus], None] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._credential_store = credential_store
        self._oauth_client_factory = oauth_client_factory
        self._api_client_factory = api_client_factory
        self._scheduler_factory = scheduler_factory
        self._on_status = on_status or (lambda status: None)
        self._clock = clock
        self._scheduler: MessageScheduler | None = None
        self._oauth_client: OAuthClient | None = None
        self._api_client: KickApiClient | None = None

    @property
    def scheduler(self) -> MessageScheduler | None:
        return self._scheduler

    @property
    def is_running(self) -> bool:
        return self._scheduler is not None and self._scheduler.is_running

    @property
    def next_send_at(self) -> float | None:
        return self._scheduler.next_send_at if self._scheduler is not None else None

    def has_configuration(self) -> bool:
        try:
            self._load_configuration()
        except ConfigurationError:
            return False
        return True

    def can_start(self) -> bool:
        return self.has_configuration() and all(
            self._credential_store.load(key)
            for key in (
                "oauth.access_token",
                "oauth.refresh_token",
                "oauth.expires_at",
            )
        )

    def save_settings(self, client_id: str, client_secret: str, channel_slug: str) -> None:
        if not client_id.strip():
            raise ConfigurationError("Enter the Kick app Client ID")
        if not client_secret:
            raise ConfigurationError("Enter the Kick app Client Secret")
        slug = channel_slug.strip().lower()
        if not slug or len(slug) > 25 or any(character.isspace() for character in slug):
            raise ConfigurationError("Enter the channel slug from the Kick channel URL")

        self._credential_store.save("app.client_id", client_id.strip())
        self._credential_store.save("app.client_secret", client_secret)
        self._credential_store.save("app.channel_slug", slug)
        self._credential_store.delete("app.broadcaster_user_id")
        self._credential_store.delete("app.resolved_channel_slug")

    def load_settings(self) -> tuple[str, str, str]:
        return (
            self._credential_store.load("app.client_id") or "",
            self._credential_store.load("app.client_secret") or "",
            self._credential_store.load("app.channel_slug") or "",
        )

    def resolve_channel(self):
        client_id, client_secret, channel_slug = self._load_app_settings()
        oauth_client = self._oauth_client_factory(client_id=client_id, client_secret=client_secret)
        api_client = self._api_client_factory()
        try:
            app_token = oauth_client.get_app_access_token()
            channel = api_client.get_channel_by_slug(app_token.access_token, channel_slug)
            self._credential_store.save("app.channel_slug", channel.slug)
            self._credential_store.save("app.resolved_channel_slug", channel.slug)
            self._credential_store.save("app.broadcaster_user_id", str(channel.broadcaster_user_id))
            return channel
        finally:
            api_client.close()
            oauth_client.close()

    def authorize(self) -> OAuthTokens:
        client_id, client_secret, _ = self._load_configuration()
        oauth_client = self._oauth_client_factory(client_id=client_id, client_secret=client_secret)
        try:
            token_manager = OAuthTokenManager(oauth_client, self._credential_store, clock=self._clock)
            return token_manager.authorize()
        finally:
            oauth_client.close()

    def start(self) -> bool:
        if self.is_running:
            return False

        client_id, client_secret, broadcaster_user_id = self._load_configuration()
        self._dispose_clients()
        self._oauth_client = self._oauth_client_factory(
            client_id=client_id,
            client_secret=client_secret,
        )
        self._api_client = self._api_client_factory()
        token_manager = OAuthTokenManager(
            self._oauth_client,
            self._credential_store,
            clock=self._clock,
        )

        def sender():
            try:
                access_token = token_manager.get_access_token()
            except OAuthError as error:
                raise AuthenticationError("Kick authorization is required") from error
            return self._api_client.send_chat_message(
                access_token,
                broadcaster_user_id,
                "$capturar",
            )

        self._scheduler = self._scheduler_factory(
            sender,
            interval_seconds=305,
            on_status=self._on_status,
        )
        return self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.stop()

    def close(self) -> None:
        self.stop()
        scheduler = self._scheduler
        cleanup = threading.Thread(
            target=self._close_after_scheduler,
            args=(scheduler,),
            name="botcapturar-cleanup",
            daemon=True,
        )
        cleanup.start()

    def _load_configuration(self) -> tuple[str, str, int]:
        client_id, client_secret, channel_slug = self._load_app_settings()
        resolved_slug = self._credential_store.load("app.resolved_channel_slug")
        broadcaster_id_value = self._credential_store.load("app.broadcaster_user_id")
        if not broadcaster_id_value or resolved_slug != channel_slug:
            raise ConfigurationError("Save and verify the channel name before continuing")
        try:
            broadcaster_user_id = int(broadcaster_id_value)
        except ValueError as error:
            raise ConfigurationError("Resolved channel ID is invalid; verify the channel again") from error
        if broadcaster_user_id <= 0:
            raise ConfigurationError("Resolved channel ID is invalid; verify the channel again")
        return client_id, client_secret, broadcaster_user_id

    def _load_app_settings(self) -> tuple[str, str, str]:
        client_id = self._credential_store.load("app.client_id")
        client_secret = self._credential_store.load("app.client_secret")
        channel_slug = self._credential_store.load("app.channel_slug")
        if not client_id or not client_secret or not channel_slug:
            raise ConfigurationError("Save the Kick app credentials and channel name first")
        return client_id, client_secret, channel_slug

    def _close_after_scheduler(self, scheduler: MessageScheduler | None) -> None:
        if scheduler is not None:
            scheduler.join()
        self._dispose_clients()

    def _dispose_clients(self) -> None:
        if self._api_client is not None:
            self._api_client.close()
            self._api_client = None
        if self._oauth_client is not None:
            self._oauth_client.close()
            self._oauth_client = None
