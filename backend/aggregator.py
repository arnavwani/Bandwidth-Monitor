import threading
import time
from collections import deque, defaultdict

class RollingAggregator:
    """
    Tracks per-process byte events in a rolling time window,
    plus lifetime totals for historical logging.
    """
    def __init__(self, window_seconds=10):
        self.window_seconds = window_seconds
        self.events = defaultdict(deque)   # {process_name: deque[(timestamp, bytes, direction)]}
        self.lifetime_totals = defaultdict(lambda: {"sent": 0, "recv": 0})
        self.lock = threading.Lock()

    def add_event(self, name, num_bytes, direction):
        now = time.time()
        with self.lock:
            self.events[name].append((now, num_bytes, direction))
            key = "sent" if direction == 0 else "recv"
            self.lifetime_totals[name][key] += num_bytes
            self._trim(name, now)

    def _trim(self, name, now):
        dq = self.events[name]
        while dq and now - dq[0][0] > self.window_seconds:
            dq.popleft()

    def get_current_rates(self):
        """Returns bytes/sec sent and received per process, based on the rolling window."""
        now = time.time()
        result = {}
        with self.lock:
            for name, dq in self.events.items():
                self._trim(name, now)
                sent = sum(b for t, b, d in dq if d == 0)
                recv = sum(b for t, b, d in dq if d == 1)
                result[name] = {
                    "sent_bps": round(sent / self.window_seconds, 2),
                    "recv_bps": round(recv / self.window_seconds, 2),
                    "sent_kbps": round(sent / self.window_seconds / 1024, 2),
                    "recv_kbps": round(recv / self.window_seconds / 1024, 2),
                }
        return result

    def get_lifetime_totals(self):
        with self.lock:
            return {
                name: {
                    "sent_kb": round(v["sent"] / 1024, 2),
                    "recv_kb": round(v["recv"] / 1024, 2)
                }
                for name, v in self.lifetime_totals.items()
            }
