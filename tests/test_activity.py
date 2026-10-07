from datetime import datetime

from botcapturar.activity import SessionActivityLog


def test_activity_log_keeps_latest_five_entries_newest_first():
    ticks = iter(datetime(2026, 10, 6, 14, 0, second) for second in range(7))
    activity = SessionActivityLog(clock=lambda: next(ticks))

    for number in range(7):
        activity.add(f"Evento {number}", "info")

    assert [entry.message for entry in activity.entries] == [
        "Evento 6",
        "Evento 5",
        "Evento 4",
        "Evento 3",
        "Evento 2",
    ]
    assert activity.entries[0].time_text == "14:00:06"


def test_activity_log_starts_empty_for_each_application_session():
    first_session = SessionActivityLog(clock=lambda: datetime(2026, 10, 6, 14, 0))
    first_session.add("Bot iniciado", "success")

    second_session = SessionActivityLog(clock=lambda: datetime(2026, 10, 6, 14, 1))

    assert [entry.message for entry in first_session.entries] == ["Bot iniciado"]
    assert second_session.entries == ()
