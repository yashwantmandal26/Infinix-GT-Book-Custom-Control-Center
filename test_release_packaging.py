"""The main launcher must not be left on a stale build after packaging."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def package_module(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "package_release", Path(__file__).parent / "scripts" / "package-release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = tmp_path
    return module


def test_sync_launcher_installs_matching_binary_and_manifest(package_module, tmp_path):
    release = tmp_path / "release"
    release.mkdir()
    executable = release / "InfinixGTToolkit.exe"
    executable.write_bytes(b"new build")
    manifest = release / "update-manifest.json"
    manifest.write_text('{"version": "new"}')
    (tmp_path / executable.name).write_bytes(b"old build")
    package_module.sync_launcher(executable, manifest)
    assert (tmp_path / executable.name).read_bytes() == b"new build"
    assert (tmp_path / manifest.name).read_bytes() == manifest.read_bytes()


@pytest.mark.parametrize("fail_install", (False, True))
def test_locked_launcher_is_preserved_and_failed_install_rolls_back(
        package_module, tmp_path, monkeypatch, fail_install):
    executable = tmp_path / "new.exe"
    executable.write_bytes(b"new build")
    manifest = tmp_path / "new.json"
    manifest.write_text('{}')
    launcher = tmp_path / "InfinixGTToolkit.exe"
    launcher.write_bytes(b"running build")
    original_replace = Path.replace
    attempts = []

    def replace(path, target):
        attempts.append(path)
        if len(attempts) == 1:
            raise PermissionError("Executable is running")
        if fail_install:
            raise OSError("Install failed")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", replace)
    if fail_install:
        with pytest.raises(OSError, match="Install failed"):
            package_module.sync_launcher(executable, manifest)
        assert launcher.read_bytes() == b"running build"
    else:
        package_module.sync_launcher(executable, manifest)
        assert launcher.read_bytes() == b"new build"
        backups = list((tmp_path / "build" / "previous-launcher").glob("*.exe"))
        assert len(backups) == 1
        assert backups[0].read_bytes() == b"running build"
