"""Bounded process-local timing evidence; no Journal or filesystem dependency."""
from src import config as parameters
from collections import deque
import threading
import time


class HealthDiagnostics:
    def __init__(self, limit=parameters.HEALTH_DIAGNOSTIC_LIMIT):
        self.lock = threading.Lock()
        self.events = deque(maxlen=limit)
        self.latest = {}
        self.counts = {}

    def record(self, name, *, retain=True, **values):
        event = dict(event=name, monotonic_s=time.monotonic(), **values)
        with self.lock:
            previous = self.latest.get(name, {})
            for key in ('wait_ms', 'interval_ms', 'duration_ms'):
                if isinstance(event.get(key), (int, float)):
                    event['max_'+key] = max(event[key], previous.get('max_'+key, 0))
            self.latest[name] = event
            self.counts[name] = self.counts.get(name, 0)+1
            if retain:
                self.events.append(event)

    def snapshot(self):
        with self.lock:
            return dict(latest=dict(self.latest), counts=dict(self.counts), events=list(self.events))
