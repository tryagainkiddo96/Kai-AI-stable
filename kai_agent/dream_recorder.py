"""Dream Recorder — poetic daily summaries from CTOS journal."""
from __future__ import annotations

import threading
import time
from datetime import datetime


class DreamRecorder:
    """At idle times, compresses the day's events into a poetic dream log."""

    def __init__(self, db, ask_fn=None):
        self.db = db
        self._ask_fn = ask_fn
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._last_dream_date = ""

    def start(self):
        if self._enabled:
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._enabled = False

    def _loop(self):
        while self._enabled:
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                if today != self._last_dream_date:
                    latest = self.db.latest_dream()
                    if not latest or latest.get("date") != today:
                        self._record_dream(today)
                        self._last_dream_date = today
            except Exception:
                pass
            time.sleep(300)

    def _record_dream(self, date: str):
        start_of_day = datetime.strptime(date, "%Y-%m-%d").timestamp()
        events = self.db.query_journal(limit=100, since=start_of_day)
        urban = self.db.get_urban_events(limit=50, since=start_of_day)

        if len(events) < 3 and len(urban) < 3:
            return

        all_events = events + urban
        event_count = len(all_events)
        event_types = {}
        for e in all_events:
            et = e.get("event_type", e.get("type", "unknown"))
            event_types[et] = event_types.get(et, 0) + 1

        lines = [f"Day {date} — {event_count} events recorded"]
        for et, cnt in sorted(event_types.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {et}: {cnt}")

        if self._ask_fn:
            try:
                import threading as _thr
                result_container = []
                def _try_ask():
                    try:
                        result_container.append(self._ask_fn(
                            f"Summarize today's events as a poetic first-person dream log. "
                            f"Events: {lines[0]}. "
                            f"Write 2-3 sentences in a surreal, dreamlike style. Do not use markdown."
                        ))
                    except Exception:
                        result_container.append(None)
                t = _thr.Thread(target=_try_ask, daemon=True)
                t.start()
                t.join(timeout=15)
                dream_text = result_container[0] if result_container and result_container[0] else "\n".join(lines)
            except Exception:
                dream_text = "\n".join(lines)
        else:
            dream_text = "\n".join(lines)

        self.db.save_dream(date, dream_text[:2000], raw_event_count=event_count)

    def get_dreams(self, limit: int = 10) -> list[dict]:
        return self.db.get_dreams(limit=limit)

    def get_latest(self) -> dict:
        return self.db.latest_dream()
