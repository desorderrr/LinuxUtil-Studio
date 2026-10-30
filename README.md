# LinuxUtil Studio

**The Linux setup app, rebuilt.**

A native-looking Linux app that installs your everyday tools with your system's package manager — and shows you exactly what it is doing.

---

## Why

Setting up a new Linux machine is a list of downloads, a handful of `apt` or `dnf` commands and a browser tab you forgot to close. LinuxUtil Studio turns that list into a single window: pick what you want, click **Install**, watch it happen.

It is a UI-focused version of the logic used in **MacUtil**.

## Features

- **Native look:** built with PySide6 (Qt) for a smooth desktop experience.
- **Light & dark themes:** toggle with the sidebar button or `Ctrl+D`; the choice is remembered between runs.
- **Real app icons:** pulled from your icon theme, with a drawn initials placeholder when the theme has no match.
- **Auto-detection:** detects your distribution and picks the right package manager (`apt`, `dnf`, `pacman`, `zypper`).
- **Multi-format support:** install from native repositories, **Flatpak** or **Snap**.
- **Non-blocking installs:** installations run in a background thread, so the window never freezes.
- **Live logs:** every line of output is streamed to the console in real time, with colour coding.
- **Installed detection:** apps already present on the system are flagged automatically.
- **Search & filter:** find apps by name/description and narrow down by category.

## Installation & Running

### Prerequisites
- Python 3.10+
- A native package manager (`apt`, `dnf`, `pacman` or `zypper`)
- Optional: `flatpak` and/or `snap` for the apps that use those formats

### Setup

```bash
git clone https://github.com/desorderrr/LinuxUtil-Studio.git
cd LinuxUtil-Studio
pip install -r requirements.txt
python3 main.py
```

## CLI usage

The backend also works without a GUI:

```bash
python3 main.py --info          # detected distro, package manager, flatpak/snap
python3 main.py --list          # catalogue + which apps are already installed
python3 main.py --install git   # install an app by its catalogue ID
python3 main.py --cli           # interactive mode
```

## The catalogue

Apps live in `catalogue.json`:

```json
{
    "id": "spotify",
    "name": "Spotify",
    "description": "Music streaming client (Flatpak / Flathub).",
    "category": "Media",
    "package_name": "com.spotify.Client",
    "package_type": "flatpak"
}
```

- `package_type` may be `native` (uses the detected system manager), `flatpak` or `snap`.
- `package_name` is the name used by the underlying manager.
- `icon` (optional) is a freedesktop icon name, e.g. `"org.videolan.VLC"`. Without it the app tries a list of known names and finally falls back to the app's initials.

## Project structure

```
main.py                  # entry point (GUI + CLI)
catalogue.json           # app catalogue
core/system_info.py      # distro + package manager detection, command building
core/installer.py        # command execution, streaming and installed checks
core/catalogue_loader.py # catalogue loading/normalisation
ui/main_window.py        # PySide6 interface and background workers
ui/theme.py              # light/dark palettes, global QSS, saved preference
ui/icons.py              # icon theme lookup + generated fallback
```

## Supported distributions

| Family | Manager |
| :--- | :--- |
| Debian / Ubuntu / Mint / Pop!_OS | `apt` |
| Fedora / RHEL / CentOS | `dnf` |
| Arch / Manjaro / EndeavourOS | `pacman` |
| openSUSE | `zypper` |

## Privilege escalation

Installing system packages needs root. LinuxUtil Studio picks the safest option that
actually works for a GUI app:

| Situation | Command used |
| :--- | :--- |
| `sudo` configured without a password (`NOPASSWD`) | `sudo` |
| Normal desktop session with a polkit agent | `pkexec` — the system's own graphical password dialog |
| No graphical session, or no `pkexec` | `sudo` (run the app from a terminal) |

A GUI process launched from the application menu has **no controlling terminal**, so a
plain `sudo` cannot prompt for a password and fails with *"a terminal is required to
read the password"*. Using `pkexec` hands authentication to polkit, so the desktop
shows its standard prompt and the app never touches your password.

LinuxUtil Studio never reads, stores, or logs credentials. Commands are executed as
argv lists (no shell), so package names are never interpreted by a shell.

Run `python3 main.py --info` to see which method was detected on your machine.

## License

MIT — see [LICENSE](LICENSE).
