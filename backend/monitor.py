import argparse
import threading
import time
import os
import sys

from bcc import BPF
from flask import Flask, jsonify, send_from_directory

sys.path.insert(0, os.path.dirname(__file__))
from aggregator import RollingAggregator
import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
EBPF_SRC = os.path.join(BASE_DIR, "..", "ebpf", "probes.c")


def load_ebpf():
    with open(EBPF_SRC, "r") as f:
        bpf_code = f.read()
    try:
        b = BPF(text=bpf_code)
        b.attach_kprobe(event=b.get_syscall_fnname("sendto"), fn_name="trace_sendto")
        b.attach_kretprobe(event=b.get_syscall_fnname("recvfrom"), fn_name="trace_recvfrom")
        return b
    except Exception as e:
        print(f"[FATAL] Failed to load/attach eBPF program: {e}")
        print("This usually means: (1) you're not running as root (use sudo), or")
        print("(2) your kernel doesn't expose the required probe points.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Per-process bandwidth monitor using eBPF")
    parser.add_argument("--port", type=int, default=5000, help="Port to serve dashboard on")
    parser.add_argument("--window", type=int, default=10, help="Rolling window size in seconds")
    parser.add_argument("--log-interval", type=int, default=15, help="Seconds between DB snapshots")
    parser.add_argument("--alert-threshold-kbps", type=float, default=None,
                         help="Print an alert if any process exceeds this KB/s")
    args = parser.parse_args()

    print("Initializing database...")
    db.init_db()

    print("Loading eBPF program into kernel...")
    b = load_ebpf()
    print("eBPF probes attached successfully.")

    aggregator = RollingAggregator(window_seconds=args.window)

    def handle_event(cpu, data, size):
        try:
            event = b["events"].event(data)
            name = event.comm.decode("utf-8", "replace")
            aggregator.add_event(name, event.bytes, event.direction)

            if args.alert_threshold_kbps:
                rates = aggregator.get_current_rates()
                proc_rate = rates.get(name, {})
                total_kbps = proc_rate.get("sent_kbps", 0) + proc_rate.get("recv_kbps", 0)
                if total_kbps > args.alert_threshold_kbps:
                    print(f"[ALERT] {name} is using {total_kbps} KB/s (threshold: {args.alert_threshold_kbps})")
        except Exception as e:
            print(f"[WARN] Error handling event: {e}")

    b["events"].open_perf_buffer(handle_event, page_cnt=64)

    def poll_events():
        while True:
            try:
                b.perf_buffer_poll(timeout=100)
            except Exception as e:
                print(f"[WARN] perf_buffer_poll error: {e}")

    def periodic_logging():
        while True:
            time.sleep(args.log_interval)
            try:
                totals = aggregator.lifetime_totals
                db.log_snapshot(totals)
            except Exception as e:
                print(f"[WARN] Failed to log snapshot: {e}")

            try:
                evicted = aggregator.evict_stale()
                if evicted:
                    print(f"[INFO] Evicted {len(evicted)} idle process(es): {evicted}")
            except Exception as e:
                print(f"[WARN] Failed to evict stale processes: {e}")

    threading.Thread(target=poll_events, daemon=True).start()
    threading.Thread(target=periodic_logging, daemon=True).start()

    app = Flask(__name__)

    @app.route("/")
    def dashboard():
        return send_from_directory(FRONTEND_DIR, "dashboard.html")

    @app.route("/api/current")
    def api_current():
        return jsonify(aggregator.get_current_rates())

    @app.route("/api/lifetime")
    def api_lifetime():
        return jsonify(aggregator.get_lifetime_totals())

    @app.route("/api/history")
    def api_history():
        return jsonify(db.get_history(since_seconds=3600))

    print(f"Dashboard running at http://localhost:{args.port}")
    print(f"Rolling window: {args.window}s | DB logging every {args.log_interval}s")
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
