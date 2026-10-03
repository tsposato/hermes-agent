"""With no timezone configured, cron schedules follow the server-local zone across DST."""

import time
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("croniter")
pytestmark = pytest.mark.skipif(not hasattr(time, "tzset"), reason="needs time.tzset (POSIX)")

import hermes_time
from cron.jobs import compute_next_run

MORNING = {"kind": "cron", "expr": "30 7 * * *"}


@pytest.fixture
def melbourne_server_local(monkeypatch):
    """Server-local zone = Australia/Melbourne, Hermes ``timezone`` unset."""
    monkeypatch.delenv("HERMES_TIMEZONE", raising=False)
    monkeypatch.setenv("TZ", "Australia/Melbourne")
    time.tzset()
    hermes_time.reset_cache()
    monkeypatch.setattr("cron.jobs.get_timezone", lambda: None)
    yield
    monkeypatch.undo()
    time.tzset()
    hermes_time.reset_cache()


def _wall(iso: str):
    dt = datetime.fromisoformat(iso).astimezone()  # server-local
    return dt.hour, dt.minute


def test_spring_forward_day_fires_at_0730_local(melbourne_server_local):
    last = datetime(2026, 10, 3, 7, 30, 20, tzinfo=timezone(timedelta(hours=10)))
    nxt = compute_next_run(MORNING, last_run_at=last.isoformat())
    assert nxt.endswith("+11:00"), nxt
    assert _wall(nxt) == (7, 30)


def test_fall_back_day_fires_at_0730_local(melbourne_server_local):
    last = datetime(2027, 4, 3, 7, 30, 20, tzinfo=timezone(timedelta(hours=11)))
    nxt = compute_next_run(MORNING, last_run_at=last.isoformat())
    assert nxt.endswith("+10:00"), nxt
    assert _wall(nxt) == (7, 30)


def test_full_year_walk_never_drifts(melbourne_server_local):
    last = datetime(2026, 1, 1, 7, 30).astimezone()
    for _ in range(365):
        nxt = compute_next_run(MORNING, last_run_at=last.isoformat())
        assert _wall(nxt) == (7, 30), f"drift after {last.isoformat()}: {nxt}"
        last = datetime.fromisoformat(nxt)
