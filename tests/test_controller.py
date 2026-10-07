from __future__ import annotations

import pytest

from botcapturar.controller import ApplicationController, ConfigurationError
from botcapturar.kick_api import ChannelInfo
from botcapturar.oauth import AppAccessToken, OAuthTokens
from botcapturar.scheduler import SchedulerState, SchedulerStatus


class FakeStore:
    def __init__(self, initial=None) -> None:
        self.values = dict(initial or {})

    def load(self, key: str) -> str | None:
        return self.values.get(key)

    def save(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


class FakeOAuthClient:
    def __init__(self, tokens: OAuthTokens | None = None) -> None:
        self.tokens = tokens or OAuthTokens("new-access", "new-refresh", 5000, "chat:write")
        self.authorize_calls = 0
        self.refresh_calls = 0
        self.closed = False

    def authorize(self) -> OAuthTokens:
        self.authorize_calls += 1
        return self.tokens

    def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        self.refresh_calls += 1
        return self.tokens

    def get_app_access_token(self) -> AppAccessToken:
        return AppAccessToken("app-access", 9000)

    def close(self) -> None:
        self.closed = True


class FakeApiClient:
    instances = []

    def __init__(self) -> None:
        self.sent = []
        self.lookups = []
        self.closed = False
        self.instances.append(self)

    def get_channel_by_slug(self, app_access_token: str, slug: str) -> ChannelInfo:
        self.lookups.append((app_access_token, slug))
        return ChannelInfo("jukes", 9876)

    def send_chat_message(self, access_token: str, broadcaster_user_id: int, content: str):
        self.sent.append((access_token, broadcaster_user_id, content))
        return type("Receipt", (), {"is_sent": True, "message_id": "message-1"})()

    def close(self) -> None:
        self.closed = True


class FakeScheduler:
    def __init__(self, sender, *, interval_seconds, on_status) -> None:
        self.sender = sender
        self.interval_seconds = interval_seconds
        self.on_status = on_status
        self.running = False
        self.started = 0
        self.stopped = 0

    def start(self) -> bool:
        self.started += 1
        self.running = True
        self.sender()
        return True

    def stop(self) -> None:
        self.stopped += 1
        self.running = False
        self.on_status(SchedulerStatus(SchedulerState.STOPPED, "Stopped"))

    def join(self, timeout=None) -> None:
        return None


def test_save_settings_persists_client_credentials_and_channel_slug():
    store = FakeStore()
    controller = ApplicationController(store)

    controller.save_settings("kick-client-id", "kick-client-secret", "jukes")

    assert store.values["app.client_id"] == "kick-client-id"
    assert store.values["app.client_secret"] == "kick-client-secret"
    assert store.values["app.channel_slug"] == "jukes"
    assert "app.broadcaster_user_id" not in store.values


def test_save_settings_rejects_input_that_is_not_a_channel_slug():
    controller = ApplicationController(FakeStore())

    with pytest.raises(ConfigurationError, match="slug"):
        controller.save_settings("kick-client-id", "kick-client-secret", "channel name")


def test_resolve_channel_looks_up_slug_and_stores_numeric_id_internally():
    FakeApiClient.instances.clear()
    store = FakeStore()
    oauth_client = FakeOAuthClient()
    controller = ApplicationController(
        store,
        oauth_client_factory=lambda **kwargs: oauth_client,
        api_client_factory=FakeApiClient,
    )
    controller.save_settings("kick-client-id", "kick-client-secret", "jukes")

    channel = controller.resolve_channel()

    assert FakeApiClient.instances[0].lookups == [("app-access", "jukes")]
    assert channel.slug == "jukes"
    assert channel.broadcaster_user_id == 9876
    assert store.values["app.broadcaster_user_id"] == "9876"
    assert oauth_client.closed is True


def test_authorize_saves_tokens_and_closes_temporary_oauth_client():
    store = FakeStore(
        {
            "app.client_id": "kick-client-id",
            "app.client_secret": "kick-client-secret",
            "app.channel_slug": "jukes",
            "app.resolved_channel_slug": "jukes",
            "app.broadcaster_user_id": "9876",
        }
    )
    oauth_client = FakeOAuthClient()
    controller = ApplicationController(store, oauth_client_factory=lambda **kwargs: oauth_client)

    tokens = controller.authorize()

    assert tokens.access_token == "new-access"
    assert store.values["oauth.access_token"] == "new-access"
    assert store.values["oauth.refresh_token"] == "new-refresh"
    assert oauth_client.closed is True


def test_start_sends_fixed_message_to_resolved_broadcaster_and_stop_stops_scheduler():
    FakeApiClient.instances.clear()
    store = FakeStore(
        {
            "app.client_id": "kick-client-id",
            "app.client_secret": "kick-client-secret",
            "app.channel_slug": "jukes",
            "app.resolved_channel_slug": "jukes",
            "app.broadcaster_user_id": "9876",
            "oauth.access_token": "access-token",
            "oauth.refresh_token": "refresh-token",
            "oauth.expires_at": "5000",
        }
    )
    oauth_client = FakeOAuthClient()
    statuses = []
    controller = ApplicationController(
        store,
        oauth_client_factory=lambda **kwargs: oauth_client,
        api_client_factory=FakeApiClient,
        scheduler_factory=FakeScheduler,
        on_status=statuses.append,
        clock=lambda: 1000,
    )

    assert controller.start() is True
    assert FakeApiClient.instances[0].sent == [("access-token", 9876, "$capturar")]
    assert controller.scheduler.interval_seconds == 305

    controller.stop()

    assert controller.scheduler.stopped == 1
    assert statuses[-1].state is SchedulerState.STOPPED
