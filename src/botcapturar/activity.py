"""Session-only recent activity for the desktop window."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass(frozen=True)
class ActivityEntry:
    time_text: str
    message: str
    state: str


class SessionActivityLog:
    """Keep a bounded, in-memory list of the latest session events."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = datetime.now,
        max_entries: int = 5,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least one")
        self._clock = clock
        self._entries: deque[ActivityEntry] = deque(maxlen=max_entries)

    @property
    def entries(self) -> tuple[ActivityEntry, ...]:
        return tuple(reversed(self._entries))

    def add(self, message: str, state: str = "info") -> ActivityEntry:
        entry = ActivityEntry(
            time_text=self._clock().strftime("%H:%M:%S"),
            message=message,
            state=state,
        )
        self._entries.append(entry)
        return entry
