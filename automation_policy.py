"""Pure policy decisions for performance automation.

This module owns priority and manual-override timing without importing the GUI
or device layer, so automation behavior can be tested independently.
"""
import datetime
import time


class AutomationPolicy:
    @staticmethod
    def manual_until(config) -> float:
        try:
            return max(0.0, float(config.get("manual_mode_until", 0.0)))
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def block_reason(cls, config, now=None) -> str:
        if bool(config.get("automation_paused", False)):
            return "paused"
        current = time.time() if now is None else now
        if cls.manual_until(config) > current:
            return "manual"
        return ""

    @classmethod
    def status_text(cls, config, now=None) -> str:
        reason = cls.block_reason(config, now)
        if reason == "paused":
            return "Paused — manual controls still work"
        if reason == "manual":
            until = datetime.datetime.fromtimestamp(cls.manual_until(config)).strftime("%H:%M")
            return f"Manual mode protected until {until}"
        return "Running — automatic changes will be listed here"

    @staticmethod
    def protect_manual(config, now=None) -> int:
        try:
            minutes = max(5, min(120, int(config.get("manual_override_minutes", 30))))
        except (TypeError, ValueError):
            minutes = 30
        current = time.time() if now is None else now
        config["manual_override_minutes"] = minutes
        config["manual_mode_until"] = current + minutes * 60
        return minutes

    @staticmethod
    def resume(config) -> None:
        config["automation_paused"] = False
        config["manual_mode_until"] = 0.0

    @staticmethod
    def select_rule(*, critical_battery=False, game=False, high_load=False,
                    low_load=False, on_ac=None):
        """Return the highest-priority requested mode and its reason."""
        if critical_battery:
            return "Quiet", "Critical battery"
        if game:
            return "Beast", "Game or creative app"
        if high_load:
            return "Beast", "Sustained high workload"
        if on_ac is False:
            return "Quiet", "Running on battery"
        if low_load or on_ac is True:
            return "Balanced", "Normal workload"
        return None, "No rule requested a change"
