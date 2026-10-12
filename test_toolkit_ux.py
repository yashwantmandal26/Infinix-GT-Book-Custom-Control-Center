"""User-control regression checks; all hardware, hooks and persistence mocked."""
import copy
import io
import json
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from app_runtime import LightingHistory
import infinix_toolkit as toolkit


class HistoryTests(unittest.TestCase):
    def test_slider_coalescing_branching_and_snapshot_independence(self):
        config = copy.deepcopy(toolkit.DEFAULT_CONFIG)
        history = LightingHistory(config)
        config["brightness"] = 80
        history.record(config, now=1)
        config["brightness"] = 60
        history.record(config, now=1.1)
        self.assertEqual(len(history.states), 2)
        self.assertEqual(history.move(-1)["brightness"], 100)
        self.assertEqual(history.move(1)["brightness"], 60)
        history.move(-1)
        config["brightness"] = 50
        history.record(config, now=2)
        self.assertIsNone(history.move(1))
        config["zones"]["1"][0] = 99
        self.assertNotEqual(history.states[0]["zones"]["1"][0],99)

    def test_non_lighting_changes_do_not_enter_history(self):
        config = copy.deepcopy(toolkit.DEFAULT_CONFIG)
        history = LightingHistory(config, limit=4)
        config["close_to_tray"] = False
        history.record(config)
        self.assertEqual(len(history.states),1)
        for i in range(10):
            config["brightness"] = i
            history.record(config,now=i+100)
        self.assertEqual(len(history.states),4)


class UserControlsTests(unittest.TestCase):
    def test_group_undo_presets_and_close_preference(self):
        with ExitStack() as stack:
            for engine in (toolkit.HardwareEngine,toolkit.SerialEngine):
                for name in vars(engine):
                    if not name.startswith("_") and callable(getattr(engine,name)):
                        stack.enter_context(patch.object(engine,name,return_value=True))
            cls = toolkit.InfinixGTToolkitApp
            for name in vars(cls):
                if name.startswith("_start_") or name in ("_init_tray_icon","_manage_startup_shortcut"):
                    stack.enter_context(patch.object(cls,name))
            config = copy.deepcopy(toolkit.DEFAULT_CONFIG)
            config.update(autostart=False,win_key_lock=False,software_fn_lock=False)
            stack.enter_context(patch.object(cls,"_load_config",return_value=config))
            stack.enter_context(patch.object(toolkit.ConfigWriter,"submit"))
            stack.enter_context(patch.object(toolkit.keyboard,"on_press"))
            stack.enter_context(patch.object(toolkit.ctypes.windll.kernel32,"CreateMutexW",return_value=0))
            stack.enter_context(patch.object(toolkit.ctypes.windll.kernel32,"GetLastError",return_value=0))
            stack.enter_context(patch.object(toolkit.messagebox,"showinfo"))
            stack.enter_context(patch.object(toolkit.messagebox,"askyesno",return_value=True))
            app = cls()
            try:
                before = copy.deepcopy(app.zones)
                app.picked_rgb = [250,20,70]
                for z,var in app.zone_group_vars.items():
                    var.set(z in ("2","4"))
                app._apply_color_to_checked_zones()
                self.assertEqual(app.zones["1"],before["1"])
                self.assertEqual(app.zones["3"],before["3"])
                self.assertEqual(app.zones["2"],[250,20,70])
                after = copy.deepcopy(app.zones)
                app._move_lighting_history(-1)
                self.assertEqual(app.zones,before)
                app._move_lighting_history(1)
                self.assertEqual(app.zones,after)
                app.preset_name_entry.insert(0,"Evening")
                app._save_user_preset()
                app.preset_name_entry.delete(0,"end")
                app.preset_name_entry.insert(0,"Evening renamed")
                app._rename_user_preset()
                self.assertNotIn("Evening",app.config["user_presets"])
                self.assertIn("Evening renamed",app.config["user_presets"])
                with patch.object(app,"_on_mode_selected") as performance:
                    app._load_user_preset()
                    performance.assert_not_called()
                    app._set_user_preference("preset_include_power",True)
                    app._load_user_preset()
                    performance.assert_called_once()
                imported = dict(app.config["user_presets"]["Evening renamed"],preset_name="Imported")
                with patch("tkinter.filedialog.askopenfilename",return_value="preset.json"), \
                     patch("builtins.open",return_value=io.StringIO(json.dumps(imported))), \
                     patch.object(app,"_apply_lighting_hardware") as apply:
                    app._import_preset_file()
                    apply.assert_not_called()
                self.assertIn("Imported",app.config["user_presets"])
                app._delete_user_preset()
                self.assertNotIn("Imported",app.config["user_presets"])
                self.assertEqual(app.zones,after)
                with patch.object(app.root,"withdraw") as hide, patch.object(app,"_quit_app") as quit_app:
                    app._on_close_requested()
                    hide.assert_called_once()
                    app.config["close_to_tray"] = False
                    app._on_close_requested()
                    quit_app.assert_called_once()
            finally:
                app.running = False
                app.backzone_view.close()
                app._config_writer.close()
                for job in app.root.tk.call("after","info"):
                    app.root.after_cancel(job)
                app.root.destroy()


if __name__ == "__main__":
    unittest.main()
