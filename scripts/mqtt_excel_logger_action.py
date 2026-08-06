#!/usr/bin/env python3
"""
Raiv-Tracker MQTT -> Excel logger (GitHub Actions edition)
===========================================================

This is a *bounded* variant of the standalone `mqtt_excel_logger.py` script,
built to run once per scheduled GitHub Actions invocation instead of forever
in the background:

    connect -> listen for LISTEN_SECONDS -> append any readings to today's
    Excel file in logs/ -> exit

The calling workflow (.github/workflows/mqtt-excel-logger.yml) then commits
and pushes logs/ if anything changed. Same "long format" row layout and same
daily-file-rotation logic as the standalone script, so files produced by
either one drop into the same logs/ folder with the same structure:

    Timestamp | Truck | Tag | Value | Datatype | Topic

WHY A BOUNDED LISTEN WINDOW INSTEAD OF FOREVER
------------------------------------------------
GitHub Actions has no "always-on" job type -- every run has to start, do its
work, and finish. Scheduled workflows are the closest thing GitHub offers to
a recurring background job, so this script listens for a short window each
time it's invoked (default 90 seconds) and captures whatever tag readings
publish during that window, then exits.

COVERAGE TRADE-OFF -- READ THIS
---------------------------------
Tags publish roughly once a minute. If this workflow runs every 10 minutes
and only listens for ~90 seconds each time, it will typically catch ONE
reading per tag per run, not all ~10 readings that occurred in between.
That means roughly 10x fewer data points than the standalone always-on
script would capture over the same span. If you need true minute-by-minute
history, run mqtt_excel_logger.py continuously on an always-on machine
instead (see the main project's README) -- this Actions version trades
resolution for running entirely inside GitHub, at no cost and with no
server to maintain.

GitHub also does not guarantee scheduled workflows fire exactly on time --
they can be delayed, especially during high load, and are disabled
automatically after 60 days of repository inactivity (any commit resets
that clock).
"""

import json
import os
import ssl
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from openpyxl import Workbook, load_workbook


MQTT_HOST = os.environ.get("MQTT_HOST", "353a1aaf7a42437797d72a6699405ee1.s1.eu.hivemq.cloud")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "Raiv-Excel-Logger")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD")
TOPIC_FILTER = os.environ.get("TOPIC_FILTER", "raiv-tracker/#")
LOG_DIR = Path(os.environ.get("LOG_DIR", "logs"))
LISTEN_SECONDS = float(os.environ.get("LISTEN_SECONDS", "90"))

HEADERS = ["Timestamp", "Truck", "Tag", "Value", "Datatype", "Topic"]


def log(msg):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def truck_label(topic):
    parts = topic.split("/")
    raw_id = parts[1] if len(parts) > 1 else topic
    digits = "".join(ch for ch in raw_id if ch.isdigit())
    return f"Truck {digits}" if digits else raw_id


class ExcelLogger:
    """Same daily-rotation behaviour as the standalone script's ExcelLogger,
    trimmed down since this process only ever lives for LISTEN_SECONDS."""

    def __init__(self, log_dir):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_date = None
        self.wb = None
        self.ws = None
        self.path = None
        self.rows_added = 0

    def _path_for(self, day):
        return self.log_dir / f"raiv_tracker_{day.isoformat()}.xlsx"

    def _ensure_workbook_for(self, day):
        if day == self.current_date:
            return
        if self.wb is not None:
            self.save()
        path = self._path_for(day)
        if path.exists():
            self.wb = load_workbook(path)
            self.ws = self.wb.active
            log(f"Resuming existing log file: {path} ({self.ws.max_row - 1} rows so far today)")
        else:
            self.wb = Workbook()
            self.ws = self.wb.active
            self.ws.title = "Log"
            self.ws.append(HEADERS)
            log(f"Started new log file: {path}")
        self.path = path
        self.current_date = day

    def add_row(self, timestamp, truck, tag, value, datatype, topic):
        self._ensure_workbook_for(timestamp.date())
        self.ws.append([
            timestamp.isoformat(timespec="seconds"),
            truck,
            tag,
            value,
            datatype,
            topic,
        ])
        self.rows_added += 1

    def save(self):
        if self.wb is None:
            return
        tmp_path = self.path.with_suffix(".xlsx.tmp")
        self.wb.save(tmp_path)
        os.replace(tmp_path, self.path)


def main():
    if not MQTT_PASSWORD:
        log("MQTT_PASSWORD is not set (expected from the HIVEMQ_MQTT_PASSWORD "
            "Actions secret). Exiting without logging anything this run.")
        sys.exit(0)  # don't fail the workflow run over a config issue

    excel_logger = ExcelLogger(LOG_DIR)
    received_lock = threading.Lock()

    def on_connect(client, userdata, connect_flags, reason_code, properties):
        if reason_code == 0:
            log(f"Connected to {MQTT_HOST}:{MQTT_PORT}")
            client.subscribe(TOPIC_FILTER, qos=0)
            log(f"Subscribed to '{TOPIC_FILTER}', listening for {LISTEN_SECONDS:.0f}s...")
        else:
            log(f"Connect failed: {reason_code}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            log(f"Skipping non-JSON message on {msg.topic}")
            return

        truck = truck_label(msg.topic)
        metrics = payload.get("metrics") if isinstance(payload, dict) else None
        if not metrics:
            metrics = [payload] if isinstance(payload, dict) else []

        with received_lock:
            for metric in metrics:
                name = metric.get("name")
                if not name:
                    continue
                timestamp = metric_timestamp(metric)
                excel_logger.add_row(
                    timestamp=timestamp,
                    truck=truck,
                    tag=name,
                    value=metric.get("value"),
                    datatype=metric.get("datatype"),
                    topic=msg.topic,
                )

    def metric_timestamp(metric):
        ts = metric.get("timestamp")
        if isinstance(ts, (int, float)):
            try:
                seconds = ts / 1000 if ts > 1e12 else ts
                return datetime.fromtimestamp(seconds)
            except (ValueError, OSError, OverflowError):
                pass
        return datetime.now()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"raiv-excel-logger-action-{os.getpid()}",
        clean_session=True,
    )
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as exc:  # noqa: BLE001
        log(f"Could not connect this run: {exc!r} -- will try again next scheduled run.")
        sys.exit(0)

    client.loop_start()
    time.sleep(LISTEN_SECONDS)
    client.loop_stop()
    client.disconnect()

    excel_logger.save()
    log(f"Done. Logged {excel_logger.rows_added} rows this run "
        f"({'no file changes' if excel_logger.rows_added == 0 else excel_logger.path.name}).")


if __name__ == "__main__":
    main()
