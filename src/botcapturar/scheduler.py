"""Background scheduler for the fixed Kick chat message."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from botcapturar.kick_api import (
    AuthenticationError,
    AuthorizationError,
    KickApiError,
    RateLimitError,
    SendResult,
    TransientKickApiError,
)


class SchedulerState(str, Enum):
    STOPPED = "stopped"
    SENDING = "sending"
    WAITING = "waiting"
    RETRYING = "retrying"
    AUTH_REQUIRED = "auth_required"
    ERROR = "error"


@dataclass(frozen=True)
class SchedulerStatus:
    state: SchedulerState
    message: str
    next_send_at: float | None = None


class MessageScheduler:
    """Send immediately, then repeat on success with bounded transient retries."""

    def __init__(
        self,
        sender: Callable[[], SendResult],
        *,
        interval_seconds: float = 305,
        on_status: Callable[[SchedulerStatus], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        wait: Callable[[threading.Event, float], bool] | None = None,
        max_retries: int = 5,
        retry_base_seconds: float = 1,
        retry_max_seconds: float = 60,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        if retry_base_seconds <= 0 or retry_max_seconds <= 0:
            raise ValueError("retry delays must be positive")

        self._sender = sender
        self._interval_seconds = interval_seconds
        self._on_status = on_status or (lambda status: None)
        self._clock = clock
        self._wait = wait or (lambda stop_event, seconds: stop_event.wait(seconds))
        self._max_retries = max_retries
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._status = SchedulerStatus(SchedulerState.STOPPED, "Stopped")

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def next_send_at(self) -> float | None:
        with self._lock:
            return self._status.next_send_at

    @property
    def status(self) -> SchedulerStatus:
        with self._lock:
            return self._status

    def start(self) -> bool:
        """Start one background worker; return False if already active."""
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="botcapturar-message-scheduler",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self) -> None:
        """Stop future sends and interrupt any scheduled wait."""
        self._stop_event.set()
        self._set_status(SchedulerState.STOPPED, "Stopped")

    def join(self, timeout: float | None = None) -> None:
        """Wait for the worker to finish, primarily for orderly shutdown/tests."""
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

    def _run(self) -> None:
        retry_count = 0
        try:
            while not self._stop_event.is_set():
                self._set_status(SchedulerState.SENDING, "Sending $capturar")
                try:
                    result = self._sender()
                except (AuthenticationError, AuthorizationError):
                    self._set_status(SchedulerState.AUTH_REQUIRED, "Kick authorization is required")
                    return
                except RateLimitError as error:
                    retry_count += 1
                    if not self._schedule_retry(retry_count, error.retry_after_seconds):
                        return
                    continue
                except TransientKickApiError:
                    retry_count += 1
                    if not self._schedule_retry(retry_count, None):
                        return
                    continue
                except KickApiError:
                    self._set_status(SchedulerState.ERROR, "Kick rejected the chat message")
                    return
                except Exception:
                    self._set_status(SchedulerState.ERROR, "Unexpected error while sending the message")
                    return

                if self._stop_event.is_set():
                    return
                if not isinstance(result, SendResult) or not result.is_sent:
                    self._set_status(SchedulerState.ERROR, "Kick did not accept the chat message")
                    return

                retry_count = 0
                next_send_at = self._clock() + self._interval_seconds
                self._set_status(
                    SchedulerState.WAITING,
                    "Message sent; waiting for the next interval",
                    next_send_at=next_send_at,
                )
                if self._wait(self._stop_event, self._interval_seconds):
                    return
        finally:
            with self._lock:
                self._running = False
            if self._stop_event.is_set() and self.status.state not in {
                SchedulerState.AUTH_REQUIRED,
                SchedulerState.ERROR,
            }:
                self._set_status(SchedulerState.STOPPED, "Stopped")

    def _schedule_retry(self, retry_count: int, retry_after_seconds: float | None) -> bool:
        if retry_count > self._max_retries:
            self._set_status(SchedulerState.ERROR, "Maximum retry attempts reached")
            return False

        exponential_delay = min(
            self._retry_base_seconds * (2 ** (retry_count - 1)),
            self._retry_max_seconds,
        )
        delay = max(exponential_delay, retry_after_seconds or 0)
        self._set_status(
            SchedulerState.RETRYING,
            f"Temporary API failure; retrying in {delay:g} seconds",
            next_send_at=self._clock() + delay,
        )
        return not self._wait(self._stop_event, delay)

    def _set_status(
        self,
        state: SchedulerState,
        message: str,
        *,
        next_send_at: float | None = None,
    ) -> None:
        status = SchedulerStatus(state=state, message=message, next_send_at=next_send_at)
        with self._lock:
            self._status = status
        self._on_status(status)
