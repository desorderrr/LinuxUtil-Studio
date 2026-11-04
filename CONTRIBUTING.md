# Contributing

Thanks for taking the time to improve LinuxUtil Studio. This is a small,
readable codebase on purpose — patches that keep it that way are very welcome.

## Ground rules

1. **Never build a shell string for a package name.** Native, Flatpak and Snap
   installs are argv lists (`["dnf", "install", "-y", name]`). If a change needs
   a shell, it should be a reviewed script in `scripts/` instead.
2. **Installing is explicit.** Nothing may run just because the app opened. The
   user clicks, confirms, and authenticates through polkit.
3. **Scripts must be previewable.** Every setup script accepts `--dry-run`,
   prints the commands it would run, changes nothing and exits 0.
4. **Scripts must be idempotent.** Running them twice is normal and safe.
5. **No credentials, ever.** No passwords, tokens, sudoers edits or stored
   secrets.
6. **Keep it dependency-light.** The GUI needs PySide6; the tests need nothing
   beyond the standard library.
7. **Vendor repositories need a fallback.** Only add official, signed vendor
   repositories with pinned key fingerprints, a `--dry-run`, explicit GUI
   confirmation, ownership-aware removal, and a working Flatpak fallback.

## Adding an app

Append an entry to [`catalogue.json`](catalogue.json):

```json
{
    "id": "gimp",
    "name": "GIMP",
    "description": "Image editor for photo retouching and design.",
    "category": "Graphics",
    "package_type": "native",
    "package_name": "gimp"
}
```

- `id` must be unique and is also the logo filename: `assets/logos/<id>.svg`.
- Use `"packages": {"arch": "..."}` when the package is renamed per family.
- Prefer `native` when the distribution packages the app well; use `flatpak`
  when the app is only shipped that way or clearly works better sandboxed.
- Use `vendor` only for first-party repositories implemented in the reviewed
  `scripts/vendor_apps.sh`; include both fallback metadata fields and tests.
- Categories are fixed: Internet, Communication, Development, Gaming, Media,
  Graphics, Productivity, System, Utilities.

**Logos** come from [Simple Icons](https://simpleicons.org) (CC0). Download the
SVG to `assets/logos/<id>.svg`; if no logo exists the UI falls back to the icon
theme and then to a coloured initials tile, so a missing file is never fatal.
Logos are trademarks of their owners — only add them to identify the app.

Then check it:

```bash
python3 main.py --list
python3 main.py --install <id> --dry-run
python3 -m unittest discover -s tests -v
```

## Adding a gaming pack

Create `scripts/gaming_<family>.sh` following the existing scripts:

- `set -uo pipefail`, `printf` helpers, no interactive prompts.
- Parse `--dry-run` before touching anything; `run` must only print in that mode.
- Print a section (`==> ...`) per step so the log is readable.
- Install native packages **and** Flatpak apps; add Flathub with
  `--if-not-exists` instead of assuming it exists.
- Never edit `/etc/pacman.conf`, apt sources or RPM Fusion config. If a repo is
  missing, skip the package and explain how to enable it.
- Track failures in an array. Optional packages may be skipped; only fail when
  the core tools (Lutris, MangoHud) are missing.
- End with the "log out and back in" hint for GameMode/MangoHud groups.

Register the script in the `gaming-pack` entry of `catalogue.json`:

```json
"scripts": {"fedora": "gaming_fedora.sh", "debian": "gaming_debian.sh", "arch": "gaming_arch.sh"},
"check": ["lutris", "mangohud", "gamescope"]
```

Then run `bash scripts/gaming_<family>.sh --dry-run` and the test suite.

## Code style

- Python: 4 spaces, `snake_case`, small functions, no wildcard imports.
- UI strings are English; comments may be Portuguese or English — match the file
  you are editing.
- No new runtime dependencies without a good reason.
- Keep the diff focused; unrelated formatting changes make review harder.

## Testing

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py core/*.py ui/*.py
for f in scripts/*.sh; do bash -n "$f"; done
```

The tests skip the gaming-script check on distros without a pack instead of
failing, so they are safe to run anywhere. CI (`.github/workflows/tests.yml`)
runs them on Python 3.10 and 3.12.

## Commits

Short imperative subject, then a body explaining **why** when it is not obvious:

```text
Fix: escalate privileges via pkexec when sudo has no terminal

A GUI process has no controlling terminal, so plain sudo cannot prompt...
```

Prefixes used so far: `Feature:`, `Fix:`, `Docs:`, `Refactor:`.
