from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from ..models import SpamProfile
from ..targeting.window_targeting import collect_targets_by_profile
from .postmessage import send_key

logger = logging.getLogger(__name__)


@dataclass
class EngineStatus:
    enabled: bool = False
    active_profile_names: list[str] | None = None


class SpamEngine:
    def __init__(
        self,
        allowed_executables_supplier: Callable[[], list[str]],
        on_tick: Callable[[EngineStatus], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._allowed_executables_supplier = allowed_executables_supplier
        self._on_tick = on_tick
        self._on_error = on_error
        self._state = EngineStatus(active_profile_names=[])
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._active_profiles: list[SpamProfile] = []
        self._last_run_at: dict[str, float] = {}
        self._last_debug_emit_at: dict[str, float] = {}
        self._paused_until: float = 0.0

    @property
    def status(self) -> EngineStatus:
        with self._lock:
            return EngineStatus(
                enabled=self._state.enabled,
                active_profile_names=list(self._state.active_profile_names or []),
            )

    def set_active_profiles(self, profiles: list[SpamProfile]) -> None:
        with self._lock:
            self._active_profiles = list(profiles)
            self._state.active_profile_names = [profile.name for profile in profiles]
            active_names = set(self._state.active_profile_names)
            self._last_run_at = {
                name: last_run for name, last_run in self._last_run_at.items() if name in active_names
            }
            self._last_debug_emit_at = {
                name: emitted_at
                for name, emitted_at in self._last_debug_emit_at.items()
                if name in active_names
            }
        logger.debug("Active profiles updated: %s", self._state.active_profile_names)
        self._emit_status()

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._state.enabled = enabled
        logger.info("Spam engine enabled set to %s", enabled)
        self._emit_status()

    def pause_temporarily(self, duration_seconds: float) -> None:
        duration = max(0.0, duration_seconds)
        pause_until = time.monotonic() + duration
        with self._lock:
            if pause_until > self._paused_until:
                self._paused_until = pause_until

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info("Spam engine worker started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Spam engine worker stopped")

    def _emit_status(self) -> None:
        if self._on_tick is not None:
            self._on_tick(self.status)

    def _emit_error(self, message: str) -> None:
        if self._on_error is not None:
            self._on_error(message)

    def _worker(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                enabled = self._state.enabled
                profiles = list(self._active_profiles)
                paused_until = self._paused_until
            if not enabled or not profiles:
                self._stop_event.wait(0.05)
                continue
            now = time.monotonic()
            if now < paused_until:
                self._stop_event.wait(min(0.05, paused_until - now))
                continue

            cycle_started = time.perf_counter()
            sleep_seconds = 0.05
            due_profiles: list[SpamProfile] = []
            for profile in profiles:
                last_run = self._last_run_at.get(profile.name, 0.0)
                interval_seconds = max(0.01, profile.interval_ms / 1000.0)
                due = now - last_run >= interval_seconds
                if due:
                    due_profiles.append(profile)
                else:
                    remaining = interval_seconds - (now - last_run)
                    if remaining < sleep_seconds:
                        sleep_seconds = max(0.01, remaining)

            targets_by_profile: dict[str, list] = {}
            allowed: list[str] = []
            if due_profiles:
                try:
                    allowed = self._allowed_executables_supplier()
                    targets_by_profile = collect_targets_by_profile(due_profiles, allowed)
                except Exception:
                    logger.exception("Target discovery failed in worker cycle")

            for profile in due_profiles:
                targets = targets_by_profile.get(profile.name, [])
                sent_count = 0
                for target in targets:
                    try:
                        if send_key(target.hwnd, profile.spam_key):
                            sent_count += 1
                    except ValueError as exc:
                        self._emit_error(
                            f"Invalid spam key for profile '{profile.name}': {exc}"
                        )
                        logger.exception(
                            "Invalid send_key for profile '%s' hwnd=%s key=%s",
                            profile.name,
                            target.hwnd,
                            profile.spam_key,
                        )
                        continue
                    except Exception:
                        logger.exception(
                            "send_key failed for profile '%s' hwnd=%s key=%s",
                            profile.name,
                            target.hwnd,
                            profile.spam_key,
                        )
                        continue
                last_emit = self._last_debug_emit_at.get(profile.name, 0.0)
                if now - last_emit >= 1.0:
                    logger.debug(
                        "Tick profile=%s key=%s interval_ms=%d allowed=%s targets=%d sent=%d",
                        profile.name,
                        profile.spam_key,
                        profile.interval_ms,
                        allowed,
                        len(targets),
                        sent_count,
                    )
                    self._last_debug_emit_at[profile.name] = now
                self._last_run_at[profile.name] = now

            cycle_elapsed_ms = (time.perf_counter() - cycle_started) * 1000
            if cycle_elapsed_ms >= 10:
                logger.debug("worker_cycle_ms=%.2f due_profiles=%d", cycle_elapsed_ms, len(due_profiles))

            self._stop_event.wait(sleep_seconds)
