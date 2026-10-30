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
- **55 apps, real logos:** brand logos are bundled as SVG, with your icon theme and a drawn initials tile as fallbacks.
- **Auto-detection:** detects your distribution and picks the right package manager (`apt`, `dnf`, `pacman`, `zypper`).
- **Per-distro package names:** one catalogue entry, the correct package for your family (`libreoffice` vs `libreoffice-fresh`, `docker.io` vs `moby-engine`…).
- **Multi-format support:** install from native repositories, **Flatpak** or **Snap**.
- **Gaming packs:** one-click gaming setup scripts for Fedora, Ubuntu/Debian and Arch/CachyOS, with a **Preview** button that prints every command before anything runs.
- **Non-blocking installs:** installations run in a background thread, so the window never freezes.
- **Live logs:** every line of output is streamed to the console in real time, with colour coding.
- **Installed detection:** apps already present on the system are flagged automatically.
- **Search & filter:** find apps by name, description or category and narrow down by category.

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
python3 main.py --info                    # detected distro, manager, family, privilege tool
python3 main.py --list                    # catalogue + resolved package + installed state
python3 main.py --install spotify         # install an app by its catalogue ID
python3 main.py --install gaming-pack --dry-run   # show what a setup script would do
python3 main.py --cli                     # interactive mode
```

## The catalogue

Apps live in `catalogue.json`:

```json
{
    "id": "libreoffice",
    "name": "LibreOffice",
    "description": "Office suite: documents, spreadsheets and slides.",
    "category": "Productivity",
    "package_type": "native",
    "package_name": "libreoffice",
    "packages": {"arch": "libreoffice-fresh"}
}
```

- `package_type` may be `native` (uses the detected system manager), `flatpak`, `snap` or `script`.
- `package_name` is the name used by the underlying manager.
- `packages` (optional) overrides the name per family: `debian`, `fedora`, `arch`, `suse`. Great for packages that are renamed between distros.
- `scripts` (only for `script` entries) maps a family to a file in `scripts/`, and `check` lists the packages that prove the pack is already applied.
- `icon` (optional) is a freedesktop icon name. Missing one? The app tries the bundled SVG in `assets/logos/`, then a list of known theme names, then the app's initials.

## Gaming packs

`scripts/` holds one setup script per family, all idempotent and readable:

| Script | Distro |
| :--- | :--- |
| `gaming_fedora.sh` | Fedora, Nobara, RHEL |
| `gaming_debian.sh` | Ubuntu, Debian, Mint, Pop!_OS |
| `gaming_arch.sh` | Arch, CachyOS, Manjaro, EndeavourOS |

They install Lutris, MangoHud, GameMode, Gamescope, Wine/Winetricks, Vulkan tools
and drivers, then add Flathub and install Steam, Heroic, Bottles and Prism Launcher
from it. Steam comes from the official Flatpak on purpose: no RPM Fusion, no i386
multiarch and no `[multilib]` editing just to get a gaming machine.

**Preview first.** Every script accepts `--dry-run` and the app exposes it as the
**Preview** button — it prints each command and changes nothing:

```bash
bash scripts/gaming_arch.sh --dry-run
python3 main.py --install gaming-pack --dry-run
```

Without `--dry-run` the scripts ask for root once, through polkit.

## Project structure

```
main.py                  # entry point (GUI + CLI)
catalogue.json           # app catalogue (55 apps)
core/system_info.py      # distro + package manager detection, package resolution, command building
core/installer.py        # command execution, streaming and installed checks
core/catalogue_loader.py # catalogue loading/normalisation
ui/main_window.py        # PySide6 interface and background workers
ui/theme.py              # light/dark palettes, global QSS, saved preference
ui/icons.py              # bundled SVG logos → icon theme → generated fallback
assets/logos/            # brand logos (Simple Icons, CC0) — see assets/logos/README.md
scripts/                 # gaming setup scripts per distro family
```

## Supported distributions

| Family | Manager | Examples |
| :--- | :--- | :--- |
| Debian / Ubuntu | `apt` | Ubuntu, Debian, Mint, Pop!_OS, Zorin, Kali |
| Fedora | `dnf` | Fedora, Nobara, RHEL, Rocky, AlmaLinux |
| Arch | `pacman` | Arch, CachyOS, Manjaro, EndeavourOS, Garuda |
| openSUSE | `zypper` | openSUSE Leap / Tumbleweed |

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

LinuxUtil Studio never reads, stores, or logs credentials. Native, Flatpak and Snap
installs are executed as argv lists (no shell), so package names are never
interpreted by a shell. Gaming packs are shell scripts on purpose — they are plain
files in `scripts/`, you can read them, and **Preview** shows every command before
anything runs.

Run `python3 main.py --info` to see which method was detected on your machine.

## Credits

Brand logos come from [Simple Icons](https://simpleicons.org) (CC0 1.0) and remain
the trademarks of their owners; see `assets/logos/README.md`.

## License

MIT — see [LICENSE](LICENSE).
