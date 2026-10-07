"""Typed client for Kick's documented public chat API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


CHAT_MESSAGE_URL = "https://api.kick.com/public/v1/chat"


@dataclass(frozen=True)
class SendResult:
    """Kick's result for a chat message send request."""

    is_sent: bool
    message_id: str


@dataclass(frozen=True)
class ChannelInfo:
    """Public channel information needed to address chat messages."""

    slug: str
    broadcaster_user_id: int


class KickApiError(RuntimeError):
    """Base error for a failed Kick API request."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(KickApiError):
    """The access token is invalid or expired."""


class AuthorizationError(KickApiError):
    """The authorized account cannot send to the requested channel."""


class ChannelNotFoundError(KickApiError):
    """Kick did not return a channel matching the requested slug."""


class TransientKickApiError(KickApiError):
    """A network or server failure that may succeed if retried later."""


class RateLimitError(KickApiError):
    """Kick throttled the request."""

    def __init__(self, *, retry_after_seconds: float | None) -> None:
        super().__init__("Kick API rate limit reached", status_code=429)
        self.retry_after_seconds = retry_after_seconds


def _retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
        return seconds if seconds >= 0 else None
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class KickApiClient:
    """Sends authenticated chat messages through Kick's public REST API."""

    def __init__(self, *, http_client: httpx.Client | None = None) -> None:
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.Client(timeout=15.0)

    def send_chat_message(
        self,
        access_token: str,
        broadcaster_user_id: int,
        content: str,
    ) -> SendResult:
        if not access_token:
            raise ValueError("access_token must not be empty")
        if broadcaster_user_id <= 0:
            raise ValueError("broadcaster_user_id must be a positive integer")

        try:
            response = self._http_client.post(
                CHAT_MESSAGE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "content": content,
                    "type": "user",
                    "broadcaster_user_id": broadcaster_user_id,
                },
            )
        except httpx.TimeoutException as error:
            raise TransientKickApiError("Kick API request timed out") from error
        except httpx.RequestError as error:
            raise TransientKickApiError("Unable to reach Kick API") from error

        self._raise_api_error(response)

        try:
            payload: Any = response.json()
            data = payload["data"]
            is_sent = data["is_sent"]
            message_id = data["message_id"]
            if type(is_sent) is not bool or not isinstance(message_id, str):
                raise ValueError("invalid field types")
            return SendResult(
                is_sent=is_sent,
                message_id=message_id,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise KickApiError("Kick API returned an invalid chat response", status_code=response.status_code) from error

    def get_channel_by_slug(self, app_access_token: str, slug: str) -> ChannelInfo:
        """Resolve a public Kick channel slug to its numeric broadcaster ID."""
        slug = slug.strip()
        if not slug or len(slug) > 25 or any(character.isspace() for character in slug):
            raise ValueError("channel slug must be 1-25 characters without spaces")
        if not app_access_token:
            raise ValueError("app_access_token must not be empty")

        try:
            response = self._http_client.get(
                "https://api.kick.com/public/v1/channels",
                headers={"Authorization": f"Bearer {app_access_token}"},
                params={"slug": slug},
            )
        except httpx.TimeoutException as error:
            raise TransientKickApiError("Kick API request timed out") from error
        except httpx.RequestError as error:
            raise TransientKickApiError("Unable to reach Kick API") from error

        self._raise_api_error(response)
        try:
            payload: Any = response.json()
            channels = payload["data"]
            if not isinstance(channels, list):
                raise ValueError("channels is not a list")
            matching = [
                channel
                for channel in channels
                if isinstance(channel, dict)
                and isinstance(channel.get("slug"), str)
                and channel["slug"].casefold() == slug.casefold()
            ]
            if not matching:
                raise ChannelNotFoundError(f"Kick channel slug '{slug}' was not found")
            if len(matching) != 1:
                raise ValueError("Kick returned multiple matching channels")
            channel = matching[0]
            broadcaster_user_id = channel["broadcaster_user_id"]
            if type(broadcaster_user_id) is not int or broadcaster_user_id <= 0:
                raise ValueError("invalid broadcaster user ID")
            return ChannelInfo(slug=channel["slug"], broadcaster_user_id=broadcaster_user_id)
        except ChannelNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise KickApiError("Kick API returned an invalid channel response", status_code=response.status_code) from error

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise AuthenticationError("Kick access token was rejected", status_code=401)
        if response.status_code == 403:
            raise AuthorizationError("Account is not authorized for this Kick API operation", status_code=403)
        if response.status_code == 429:
            raise RateLimitError(retry_after_seconds=_retry_after_seconds(response.headers.get("Retry-After")))
        if response.status_code in {408, 425} or response.status_code >= 500:
            raise TransientKickApiError(
                "Kick API temporarily failed",
                status_code=response.status_code,
            )
        if response.is_error:
            raise KickApiError("Kick API rejected the request", status_code=response.status_code)

    def close(self) -> None:
        """Close the HTTP session when this client owns it."""
        if self._owns_client:
            self._http_client.close()
