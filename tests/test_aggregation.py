import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from aggregator import RollingAggregator


def test_add_event_updates_lifetime_totals():
    agg = RollingAggregator(window_seconds=5)
    agg.add_event("chrome", 1024, 0)  # sent
    agg.add_event("chrome", 2048, 1)  # recv
    totals = agg.get_lifetime_totals()
    assert totals["chrome"]["sent_kb"] == 1.0
    assert totals["chrome"]["recv_kb"] == 2.0
    print("test_add_event_updates_lifetime_totals passed")


def test_rolling_window_expires_old_events():
    agg = RollingAggregator(window_seconds=1)
    agg.add_event("spotify", 1024, 0)
    time.sleep(1.5)
    rates = agg.get_current_rates()
    # after window expires, rate should be 0 since event aged out
    assert rates["spotify"]["sent_kbps"] == 0.0
    print("test_rolling_window_expires_old_events passed")


def test_multiple_processes_tracked_independently():
    agg = RollingAggregator(window_seconds=5)
    agg.add_event("chrome", 500, 0)
    agg.add_event("spotify", 300, 0)
    totals = agg.get_lifetime_totals()
    assert "chrome" in totals
    assert "spotify" in totals
    assert totals["chrome"]["sent_kb"] != totals["spotify"]["sent_kb"]
    print("test_multiple_processes_tracked_independently passed")


if __name__ == "__main__":
    test_add_event_updates_lifetime_totals()
    test_rolling_window_expires_old_events()
    test_multiple_processes_tracked_independently()
    print("\nAll tests passed.")
