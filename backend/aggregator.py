import threading
import time
from collections import deque, defaultdict

class RollingAggregator:
    def __init__(self, window_seconds=10, idle_eviction_seconds=60):
        self.window_seconds = window_seconds
        self.idle_eviction_seconds = idle_eviction_seconds
        self.events = defaultdict(deque)   # {process_name: deque[(timestamp, bytes, direction)]}
        self.lifetime_totals = defaultdict(lambda: {"sent": 0, "recv": 0})
        self.last_seen = {}                # {process_name: timestamp of most recent event}
        self.lock = threading.Lock()

    def add_event(self, name, num_bytes, direction):
        now = time.time()
        with self.lock:
            self.events[name].append((now, num_bytes, direction))
            key = "sent" if direction == 0 else "recv"
            self.lifetime_totals[name][key] += num_bytes
            self.last_seen[name] = now
            self._trim(name, now)

    def evict_stale(self):
        """Drop processes that haven't sent/received anything in
        `idle_eviction_seconds`, so short-lived processes don't accumulate
        in memory forever for the life of the monitor."""
        now = time.time()
        with self.lock:
            stale = [
                name for name, ts in self.last_seen.items()
                if now - ts > self.idle_eviction_seconds
            ]
            for name in stale:
                self.events.pop(name, None)
                self.lifetime_totals.pop(name, None)
                self.last_seen.pop(name, None)
        return stale

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
