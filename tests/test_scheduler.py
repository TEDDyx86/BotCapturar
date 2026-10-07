from __future__ import annotations

from threading import Event

import pytest

from botcapturar.kick_api import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    SendResult,
    TransientKickApiError,
)
from botcapturar.scheduler import MessageScheduler, SchedulerState


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.waits: list[float] = []

    def __call__(self) -> float:
        return self.now

    def wait(self, stop_event: Event, seconds: float) -> bool:
        self.waits.append(seconds)
        self.now += seconds
        return stop_event.is_set()


def test_sends_immediately_then_waits_305_seconds_between_successful_sends():
    clock = FakeClock()
    sent_at: list[float] = []
    terminal = Event()
    scheduler_ref: list[MessageScheduler] = []

    def sender() -> SendResult:
        sent_at.append(clock())
        if len(sent_at) == 2:
            scheduler_ref[0].stop()
        return SendResult(is_sent=True, message_id=f"message-{len(sent_at)}")

    scheduler = MessageScheduler(
        sender,
        interval_seconds=305,
        on_status=lambda status: terminal.set()
        if status.state is SchedulerState.STOPPED
        else None,
        clock=clock,
        wait=clock.wait,
    )
    scheduler_ref.append(scheduler)

    assert scheduler.start() is True
    assert terminal.wait(timeout=1)
    scheduler.join(timeout=1)

    assert sent_at == [0.0, 305.0]
    assert clock.waits == [305]


def test_stop_during_wait_prevents_next_message():
    clock = FakeClock()
    sent: list[str] = []
    terminal = Event()

    def wait_then_stop(stop_event: Event, seconds: float) -> bool:
        clock.waits.append(seconds)
        clock.now += seconds
        stop_event.set()
        return True

    scheduler = MessageScheduler(
        lambda: sent.append("$capturar") or SendResult(True, "message-1"),
        interval_seconds=305,
        on_status=lambda status: terminal.set()
        if status.state is SchedulerState.STOPPED
        else None,
        clock=clock,
        wait=wait_then_stop,
    )

    assert scheduler.start() is True
    assert terminal.wait(timeout=1)
    scheduler.join(timeout=1)

    assert sent == ["$capturar"]
    assert clock.waits == [305]


def test_transient_failures_use_bounded_backoff_then_resume_normal_interval():
    clock = FakeClock()
    attempt_times: list[float] = []
    terminal = Event()
    scheduler_ref: list[MessageScheduler] = []

    def sender() -> SendResult:
        attempt_times.append(clock())
        if len(attempt_times) < 3:
            raise TransientKickApiError("temporary network failure")
        scheduler_ref[0].stop()
        return SendResult(is_sent=True, message_id="message-1")

    scheduler = MessageScheduler(
        sender,
        interval_seconds=305,
        on_status=lambda status: terminal.set()
        if status.state is SchedulerState.STOPPED
        else None,
        clock=clock,
        wait=clock.wait,
        retry_base_seconds=1,
        retry_max_seconds=4,
    )
    scheduler_ref.append(scheduler)

    assert scheduler.start() is True
    assert terminal.wait(timeout=1)
    scheduler.join(timeout=1)

    assert attempt_times == [0.0, 1.0, 3.0]
    assert clock.waits == [1, 2]


@pytest.mark.parametrize(
    ("error_type", "status_code"),
    [(AuthenticationError, 401), (AuthorizationError, 403)],
)
def test_authentication_error_stops_without_retry_and_reports_reauthorization(error_type, status_code):
    attempts = 0
    terminal = Event()
    statuses = []

    def sender() -> SendResult:
        nonlocal attempts
        attempts += 1
        raise error_type("authorization rejected", status_code=status_code)

    def record_status(status) -> None:
        statuses.append(status.state)
        if status.state is SchedulerState.AUTH_REQUIRED:
            terminal.set()

    scheduler = MessageScheduler(sender, on_status=record_status, wait=FakeClock().wait)

    assert scheduler.start() is True
    assert terminal.wait(timeout=1)
    scheduler.join(timeout=1)

    assert attempts == 1
    assert SchedulerState.AUTH_REQUIRED in statuses


def test_rate_limit_retry_waits_at_least_the_server_retry_after_value():
    clock = FakeClock()
    attempts: list[float] = []
    terminal = Event()
    scheduler_ref: list[MessageScheduler] = []

    def sender() -> SendResult:
        attempts.append(clock())
        if len(attempts) == 1:
            raise RateLimitError(retry_after_seconds=17)
        scheduler_ref[0].stop()
        return SendResult(True, "message-1")

    scheduler = MessageScheduler(
        sender,
        on_status=lambda status: terminal.set()
        if status.state is SchedulerState.STOPPED
        else None,
        clock=clock,
        wait=clock.wait,
        retry_base_seconds=1,
    )
    scheduler_ref.append(scheduler)

    assert scheduler.start() is True
    assert terminal.wait(timeout=1)
    scheduler.join(timeout=1)

    assert attempts == [0.0, 17.0]
    assert clock.waits == [17]


def test_stops_after_maximum_transient_retries():
    attempts = 0
    terminal = Event()
    statuses = []
    clock = FakeClock()

    def sender() -> SendResult:
        nonlocal attempts
        attempts += 1
        raise TransientKickApiError("temporary network failure")

    def record_status(status) -> None:
        statuses.append(status.state)
        if status.state is SchedulerState.ERROR:
            terminal.set()

    scheduler = MessageScheduler(
        sender,
        on_status=record_status,
        clock=clock,
        wait=clock.wait,
        max_retries=2,
        retry_base_seconds=1,
        retry_max_seconds=2,
    )

    assert scheduler.start() is True
    assert terminal.wait(timeout=1)
    scheduler.join(timeout=1)

    assert attempts == 3
    assert clock.waits == [1, 2]
    assert statuses[-1] is SchedulerState.ERROR
