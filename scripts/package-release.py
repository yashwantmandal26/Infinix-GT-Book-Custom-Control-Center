"""Package a built executable, matching manifest, notices and portable ZIP."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def app_version():
    tree = ast.parse((ROOT / "infinix_toolkit.py").read_text(encoding="utf-8"))
    return next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in n.targets))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default="dist/InfinixGTToolkit.exe")
    parser.add_argument("--tag")
    args = parser.parse_args()
    version = app_version()
    if args.tag and args.tag != "v" + version:
        raise SystemExit(f"Tag {args.tag!r} does not match APP_VERSION {version!r}")
    executable = Path(args.exe).resolve()
    if not executable.is_file():
        raise SystemExit(f"Executable not found: {executable}")
    out = ROOT / "release"
    out.mkdir(exist_ok=True)
    target = out / "InfinixGTToolkit.exe"
    if executable != target:
        shutil.copy2(executable, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest().upper()
    manifest = out / "update-manifest.json"
    manifest.write_text(json.dumps({"version": version, "sha256": digest}, indent=2) + "\n", encoding="utf-8")
    archive = out / f"Infinix-GT-Book-Control-Center-{version}-Windows.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for item in (target, manifest):
            z.write(item, item.name)
        z.write(ROOT / "RUN_ME.md", "README.md")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            z.write(ROOT / name, name)
        z.write(ROOT / "docs" / "VALIDATION.md", "docs/VALIDATION.md")
        for p in (ROOT / "third_party_licenses").rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(ROOT))
    checksums = out / "SHA256SUMS.txt"
    checksums.write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n"
                                 for p in (target, manifest, archive)), encoding="utf-8")
    print(f"Packaged {version}: {archive}")

if __name__ == "__main__":
    main()
