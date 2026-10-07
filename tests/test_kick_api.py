import json

import httpx
import pytest

from botcapturar.kick_api import (
    AuthenticationError,
    AuthorizationError,
    ChannelNotFoundError,
    KickApiClient,
    KickApiError,
    RateLimitError,
    TransientKickApiError,
)


def test_sends_user_message_to_broadcaster_and_returns_receipt():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"data": {"is_sent": True, "message_id": "message-123"}, "message": "OK"},
        )

    client = KickApiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    result = client.send_chat_message(
        access_token="oauth-token",
        broadcaster_user_id=456,
        content="$capturar",
    )

    assert captured == {
        "url": "https://api.kick.com/public/v1/chat",
        "authorization": "Bearer oauth-token",
        "body": {
            "content": "$capturar",
            "type": "user",
            "broadcaster_user_id": 456,
        },
    }
    assert result.is_sent is True
    assert result.message_id == "message-123"


def test_returns_unsent_receipt_when_api_does_not_accept_message():
    client = KickApiClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"data": {"is_sent": False, "message_id": ""}, "message": "Not sent"},
                )
            )
        )
    )

    result = client.send_chat_message("oauth-token", 456, "$capturar")

    assert result.is_sent is False


def test_rejects_malformed_success_payload_instead_of_coercing_sent_flag():
    client = KickApiClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"data": {"is_sent": "false", "message_id": "message-123"}},
                )
            )
        )
    )

    with pytest.raises(KickApiError, match="invalid chat response"):
        client.send_chat_message("oauth-token", 456, "$capturar")


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, AuthenticationError),
        (403, AuthorizationError),
        (500, KickApiError),
    ],
)
def test_maps_api_errors(status_code: int, error_type: type[Exception]):
    client = KickApiClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(status_code, json={"message": "failed"}))
        )
    )

    with pytest.raises(error_type):
        client.send_chat_message("oauth-token", 456, "$capturar")


def test_rate_limit_error_preserves_retry_after_header():
    client = KickApiClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(429, headers={"Retry-After": "17"}, json={"message": "slow down"})
            )
        )
    )

    with pytest.raises(RateLimitError) as caught:
        client.send_chat_message("oauth-token", 456, "$capturar")

    assert caught.value.retry_after_seconds == 17


def test_server_errors_are_classified_as_transient():
    client = KickApiClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        )
    )

    with pytest.raises(TransientKickApiError):
        client.send_chat_message("oauth-token", 456, "$capturar")


def test_resolves_channel_slug_to_broadcaster_user_id():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(
            200,
            json={
                "data": [{"slug": "jukes", "broadcaster_user_id": 9876}],
                "message": "OK",
            },
        )

    client = KickApiClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    channel = client.get_channel_by_slug("app-access-token", "jukes")

    assert captured == {
        "method": "GET",
        "url": "https://api.kick.com/public/v1/channels?slug=jukes",
        "authorization": "Bearer app-access-token",
    }
    assert channel.slug == "jukes"
    assert channel.broadcaster_user_id == 9876


@pytest.mark.parametrize(
    "payload",
    [
        {"data": [], "message": "OK"},
        {"data": [{"slug": "someone-else", "broadcaster_user_id": 9876}], "message": "OK"},
    ],
)
def test_reports_channel_not_found_for_empty_or_non_matching_slug(payload):
    client = KickApiClient(
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        )
    )

    with pytest.raises(ChannelNotFoundError, match="channel slug"):
        client.get_channel_by_slug("app-access-token", "jukes")
