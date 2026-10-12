# Publishing to GitHub

This folder is a standalone project. Its local Git repository is configured for:
`https://github.com/yashwantmandal26/Infinix-GT-Book-Custom-Control-Center.git`.
No remote writes were performed while packaging it.

## First source upload

Use GitHub Desktop to add this existing local repository and commit the files.
If publishing to a new repository, change `origin` to that repository URL and
change `UPDATE_REPOSITORY` in `infinix_toolkit.py` before building. If using the
existing repository, reconcile its existing history before pushing; **do not
force-push this standalone initial history over an existing project**. One safe
option is to clone the existing repository separately, copy these source files
into that checkout (excluding `.git`, `.venv`, builds and EXEs), and commit there.

For a new, empty repository, these commands can be used after setting origin:

```powershell
git add .
git commit -m "Prepare editable control center with disabled Arcade Beta"
git push -u origin main
```

The ignore file keeps EXEs, build output and local settings out of source commits.

## Release a new version

1. Update `APP_VERSION`, `BUILD_DATE`, and release metadata in `infinix_toolkit.py`.
2. Update numeric and string versions in `version_info.txt` to match.
3. Run `scripts/test.ps1`, then `scripts/build.ps1`. Test the built EXE on GL613.
4. Commit, push, then create a new matching tag (for example `v4.5.1`).
5. The workflow builds on Windows, runs the focused tests and creates a **draft**
   GitHub Release. Review its assets/notes, then click Publish release.

```powershell
git tag v4.5.1
git push origin v4.5.1
```

The example tag is only appropriate after changing the app version to 4.5.1.
The workflow rejects a tag that differs from APP_VERSION.

## Manual release alternative

Run `scripts/build.ps1`; attach everything from `release/` to a GitHub Release.
Keep the executable asset named `InfinixGTToolkit.exe` and attach the matching
`update-manifest.json`. Never pair a new EXE with an old hash manifest.
The portable ZIP includes user-facing instructions and notices. Existing users
receive updates only for a newer, published, non-prerelease version on the
repository configured inside their app. Drafts do not trigger updates.

## Share with another user

Send the portable ZIP or the GitHub Release link. They extract it and run the
EXE without Python. Share the project ZIP/GitHub repository with contributors
who want to change the code. The packaged folder contains no copied user presets,
OEM executables, extracted OEM DLLs or live controller probe programs.
