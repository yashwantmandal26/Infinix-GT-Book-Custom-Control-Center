"""Serialized, non-blocking execution for hardware commands.

The GUI submits named operations here instead of starting ad-hoc threads. One
worker preserves command order, duplicate keys are rejected while pending, and
short transient failures receive a bounded retry.
"""
from dataclasses import dataclass
from queue import Queue
import threading
import time
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class CommandResult:
    key: str
    ok: bool
    value: Any = None
    error: str = ""
    attempts: int = 1


class HardwareCommandController:
    """Run hardware writes sequentially without blocking the UI thread."""

    def __init__(self, dispatch: Callable, retry_delay: float = 0.25):
        self._dispatch = dispatch
        self._retry_delay = retry_delay
        self._queue = Queue()
        self._lock = threading.Lock()
        self._pending = set()
        self._closed = False
        self._worker = threading.Thread(
            target=self._run, name="HardwareCommands", daemon=True)
        self._worker.start()

    def submit(
        self,
        key: str,
        operation: Callable[[], Any],
        callback: Callable[[CommandResult], None],
        *,
        retries: int = 1,
        error_provider: Optional[Callable[[], str]] = None,
    ) -> bool:
        """Queue a command; return False when the same control is already busy."""
        with self._lock:
            if self._closed or key in self._pending:
                return False
            self._pending.add(key)
        self._queue.put((key, operation, callback, max(0, retries), error_provider))
        return True

    def pending(self, key: str) -> bool:
        with self._lock:
            return key in self._pending

    def close(self, timeout: float = 1.5) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._queue.put(None)
        self._worker.join(timeout)

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            key, operation, callback, retries, error_provider = item
            ok, value, error, attempts = False, None, "", 0
            for attempt in range(retries + 1):
                attempts = attempt + 1
                try:
                    value = operation()
                    ok = bool(value)
                    if not ok:
                        error = error_provider() if error_provider else "Command was rejected"
                except Exception as exc:
                    error = str(exc)
                    ok = False
                if ok:
                    error = ""
                    break
                if attempt < retries:
                    time.sleep(self._retry_delay)
            with self._lock:
                self._pending.discard(key)
            result = CommandResult(key, ok, value, error, attempts)
            try:
                self._dispatch(callback, result)
            except Exception:
                pass


def format_reliability_report(checks):
    """Return a concise diagnostics block from (name, state, detail) rows."""
    rows = []
    for name, state, detail in checks:
        marker = {"pass": "PASS", "warn": "CHECK", "fail": "FAIL"}.get(state, "INFO")
        rows.append(f"{marker}  {name}: {detail}")
    return "\n".join(rows)
