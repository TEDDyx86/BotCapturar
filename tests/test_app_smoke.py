from __future__ import annotations

import botcapturar.__main__ as app_main


class FakeRoot:
    def __init__(self) -> None:
        self.mainloop_called = False
        self.destroyed = False

    def mainloop(self) -> None:
        self.mainloop_called = True

    def destroy(self) -> None:
        self.destroyed = True


def test_main_opens_window_and_enters_event_loop_without_sending():
    root = FakeRoot()
    created = {}

    class FakeWindow:
        def __init__(self, received_root, *, credential_store) -> None:
            created["root"] = received_root
            created["store"] = credential_store
            created["start_calls"] = 0

    credential_store = object()
    result = app_main.main(
        root_factory=lambda: root,
        credential_store_factory=lambda: credential_store,
        window_factory=FakeWindow,
    )

    assert result == 0
    assert root.mainloop_called is True
    assert created == {"root": root, "store": credential_store, "start_calls": 0}
