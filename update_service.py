"""GitHub Release update discovery and verified Windows installation helpers."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    release_url: str
    executable_url: str
    sha256: str
    notes: str = ""


class GitHubUpdateService:
    """Read only public GitHub Release metadata with no launch-time UI blocking."""

    def __init__(self, repository: str, current_version: str):
        self.repository = repository
        self.current_version = current_version

    @staticmethod
    def _version_parts(value: str):
        cleaned = str(value).strip().lstrip("vV").split("-")[0]
        return tuple(int(piece) for piece in cleaned.split(".") if piece.isdigit())

    def _request_json(self, url: str):
        request = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github+json", "User-Agent": "InfinixGTToolkit"})
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    def check(self):
        """Return UpdateInfo, None when current, or raise a concise RuntimeError."""
        api_url = f"https://api.github.com/repos/{self.repository}/releases/latest"
        try:
            release = self._request_json(api_url)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise RuntimeError(f"GitHub update check failed ({error.code})") from error
        except Exception as error:
            raise RuntimeError(f"GitHub update check failed: {error}") from error

        version = str(release.get("tag_name", "")).lstrip("vV")
        if not version or self._version_parts(version) <= self._version_parts(self.current_version):
            return None
        assets = {asset.get("name"): asset for asset in release.get("assets", [])}
        executable = next((asset for name, asset in assets.items()
                           if name and name.lower() == "infinixgttoolkit.exe"), None)
        manifest = next((asset for name, asset in assets.items()
                         if name and name.lower() == "update-manifest.json"), None)
        if not executable or not manifest:
            raise RuntimeError("The newest release is missing its verified installer assets")
        manifest_data = self._request_json(manifest["browser_download_url"])
        expected_hash = str(manifest_data.get("sha256", "")).upper()
        if len(expected_hash) != 64 or any(char not in "0123456789ABCDEF" for char in expected_hash):
            raise RuntimeError("The newest release has an invalid integrity manifest")
        return UpdateInfo(
            version=version,
            release_url=release.get("html_url", ""),
            executable_url=executable["browser_download_url"],
            sha256=expected_hash,
            notes=str(release.get("body", "")),
        )

    @staticmethod
    def download_verified(update: UpdateInfo, destination: str):
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".part")
        request = urllib.request.Request(update.executable_url, headers={"User-Agent": "InfinixGTToolkit"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as stream:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    stream.write(block)
            actual = hashlib.sha256(temporary.read_bytes()).hexdigest().upper()
            if actual != update.sha256:
                raise RuntimeError("Downloaded update did not pass SHA-256 verification")
            os.replace(temporary, target)
            return str(target)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except Exception:
                pass
            raise

    @staticmethod
    def install_after_exit(current_executable: str, downloaded_executable: str, version: str):
        """Start an elevated helper that archives, replaces, and restarts the app."""
        install_path = Path(current_executable)
        update_path = Path(downloaded_executable)
        archive_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "InfinixGTToolkit" / "Previous versions"
        helper = Path(tempfile.gettempdir()) / f"InfinixGTToolkit-update-{version}.ps1"
        script = f'''$ErrorActionPreference = 'Stop'
$target = '{str(install_path).replace("'", "''")}'
$update = '{str(update_path).replace("'", "''")}'
$archive = '{str(archive_dir).replace("'", "''")}'
$pidToWait = {os.getpid()}
Wait-Process -Id $pidToWait -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $archive -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (Test-Path -LiteralPath $target) {{ Copy-Item -LiteralPath $target -Destination (Join-Path $archive "InfinixGTToolkit-$stamp.exe") -Force }}
Copy-Item -LiteralPath $update -Destination "$target.new" -Force
Move-Item -LiteralPath "$target.new" -Destination $target -Force
Start-Process -FilePath $target
Remove-Item -LiteralPath $update -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
'''
        helper.write_text(script, encoding="utf-8")
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper)],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
