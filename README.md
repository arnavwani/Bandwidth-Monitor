# Per-Process Bandwidth Monitor

A real-time, kernel-level network monitoring tool that shows exactly which
process on your machine is using bandwidth, live — built using eBPF.

Most tools like Task Manager show total network usage; they don't break it
down per-process in real time. I built this to understand kernel-level
observability and see exactly where my bandwidth actually goes.

## How it works

![](https://asciiflow.com) [Network traffic in kernel]-->[eBPF probes hook tcp_sendmsg / tcp_recvmsg]; [eBPF probes hook tcp_sendmsg / tcp_recvmsg]-->[BCC pulls events out of the kernel into Python]; [BCC pulls events out of the kernel into Python]-->[Rolling aggregator tracks bytes/sec per process]; [Rolling aggregator tracks bytes/sec per process]-->[SQLite logs periodic snapshots for history]; [SQLite logs periodic snapshots for history]-->[Flask API serves live + historical data]; [Flask API serves live + historical data]-->[Dashboard (Chart.js) shows live bar charts];

- **eBPF probes** attach to `tcp_sendmsg` (outgoing) and `tcp_recvmsg` (incoming)
  kernel functions, tagging every event with the PID and process name that
  triggered it.
- **BCC** compiles and safely loads this C code into the kernel, and streams
  events back to Python via a perf buffer.
- **Rolling window aggregator** keeps only the last N seconds of events per
  process (default 10s), so the dashboard reflects *current* usage, not
  lifetime totals.
- **SQLite** periodically snapshots lifetime totals so historical usage can
  be queried later.
- **Flask** exposes `/api/current`, `/api/lifetime`, and `/api/history`
  endpoints consumed by the dashboard.

## Tech stack

- eBPF + BCC (kernel-level instrumentation)
- Python 3 (aggregation logic, Flask backend)
- SQLite (historical storage)
- Flask (REST API)
- Chart.js (live dashboard)

## Setup

Requires Linux (or WSL2 on Windows) with BCC installed.

```bash
sudo apt update
sudo apt install bpfcc-tools python3-bpfcc python3-flask
git clone <your-repo-url>
cd bandwidth-monitor
sudo python3 backend/monitor.py
```

Then open `http://localhost:5000` in your browser.

### CLI options

```bash
sudo python3 backend/monitor.py --port 8080 --window 15 --alert-threshold-kbps 500
```

- `--port`: dashboard port (default 5000)
- `--window`: rolling window size in seconds (default 10)
- `--log-interval`: seconds between DB snapshots (default 15)
- `--alert-threshold-kbps`: print a console alert if any process exceeds this rate

## Running tests

```bash
python3 tests/test_aggregation.py
```

## Challenges solved

- eBPF requires real kernel-level access; got this working under WSL2 on
  Windows after working through kernel compatibility issues with the custom
  WSL2 kernel build.
- Needed a rolling time-window data structure (not just running totals) to
  make the "live" numbers actually reflect current activity rather than
  all-time usage.

## Screenshots

See `screenshots/` for a demo of the live dashboard.
