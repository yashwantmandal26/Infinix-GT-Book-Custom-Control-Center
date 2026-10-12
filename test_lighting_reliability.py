"""No hardware writes: reproduce recurring traffic, disconnects and short writes."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import infinix_toolkit as toolkit


class FakeHid:
    def __init__(self):
        self.frames = []
        self.closed = False
        self.short_write = False

    def write(self, data):
        self.frames.append(bytes(data))
        return 3 if self.short_write else len(data)

    def open_path(self, path):
        self.path = path

    def close(self):
        self.closed = True


class LightingReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.engine = toolkit.HardwareEngine
        self.dev = FakeHid()
        for name, value in dict(_dev=self.dev, _watchdog_device=None,
                                _needs_mode_restore=False, _last_open_failure=0,
                                _last_error="").items():
            patcher = patch.object(self.engine, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.app = SimpleNamespace(running=True, heartbeat_active=True,
                                   _suspended=False, brightness=80,
                                   effect_mode="Solid",
                                   zones={str(i): (20*i, 180, 255) for i in range(1,5)})

    def tick(self):
        toolkit.InfinixGTToolkitApp._keyboard_heartbeat_tick(self.app)

    def test_five_minutes_of_heartbeats_do_not_relatch_or_reset_mode(self):
        for _ in range(120):  # 2.5-second heartbeat cadence, including 8–10 seconds
            self.tick()
        commands = [p[1] for p in self.dev.frames]
        self.assertEqual(commands.count(0x19), 1)
        self.assertNotIn(0x11, commands)
        self.assertEqual(commands.count(0x60), 120)
        self.assertEqual(commands.count(0x74), 120)

    def test_inactive_heartbeat_never_wakes_keyboard(self):
        for name, value in (("running",False),("heartbeat_active",False),
                            ("_suspended",True),("brightness",0)):
            with patch.object(self.app,name,value):
                self.tick()
        self.assertEqual(self.dev.frames, [])

    def test_dynamic_heartbeat_does_not_inject_static_zone_colors(self):
        self.app.effect_mode = "Aurora"
        for _ in range(5):
            self.tick()
        self.assertEqual([p[1] for p in self.dev.frames], [0x19])

    def test_reconnect_rearms_timeout_and_restores_mode_only_once(self):
        self.tick()
        self.engine._close_device()
        reopened = FakeHid()
        with patch.object(toolkit.hid,"enumerate",return_value=[
                dict(vendor_id=0x340E, product_id=0x8002, path=b"test-mi_01")]), \
             patch.object(toolkit.hid,"device",return_value=reopened):
            self.tick()
            self.tick()
        commands = [p[1] for p in reopened.frames]
        self.assertEqual(commands.count(0x19),1)
        self.assertEqual(commands.count(0x11),1)
        self.assertEqual(commands.count(0x74),2)

    def test_native_animation_restored_without_periodic_restart(self):
        self.app.effect_mode = "HwBreath"
        self.engine._needs_mode_restore = True
        self.tick()
        self.tick()
        self.assertEqual([p[1] for p in self.dev.frames], [0x19,0x12])

    def test_partial_writes_fail_and_invalidate_handle(self):
        self.dev.short_write = True
        self.assertFalse(self.engine.send_disable_auto_close())
        self.assertIsNone(self.engine._watchdog_device)
        self.assertIsNone(self.engine._dev)
        self.assertTrue(self.dev.closed)
        self.assertIn("3 of 64",self.engine.get_last_error())

    def test_partial_zone_frame_is_not_reported_as_success(self):
        self.dev.short_write = True
        self.assertFalse(self.engine.send_4zone_rgb(self.app.zones))
        self.assertEqual(len(self.dev.frames),1)
        self.assertIsNone(self.engine._dev)

    def test_rear_refresh_does_not_rewrite_ec_power_every_30_seconds(self):
        serial = SimpleNamespace(write=lambda data:len(data),flush=lambda:None)
        with patch.object(toolkit.SerialEngine,"_serial",serial), \
             patch.object(toolkit.SerialEngine,"_ec_power_state",True), \
             patch.object(toolkit.SerialEngine,"_last_power_refresh",0), \
             patch.object(toolkit.SerialEngine,"_retry_after",0), \
             patch.object(toolkit.SerialEngine,"_get_or_open_port",return_value=serial), \
             patch.object(self.engine,"set_ec_backlight_power") as power:
            self.assertTrue(toolkit.SerialEngine.send_backzone_rgb(1,0,180,255,1,80))
            power.assert_not_called()

    def test_rear_ec_write_failure_is_not_reported_as_success(self):
        with patch.object(self.engine,"_get_acpi_method_provider",return_value=None), \
             patch.object(self.engine,"_ec_read_ram",return_value=2), \
             patch.object(self.engine,"_ec_write_ram",return_value=False):
            self.assertFalse(self.engine.set_ec_backlight_power(True))


if __name__ == "__main__":
    unittest.main()
