# LinuxUtil Studio

**The Linux setup app, rebuilt.**

A native-looking Linux app that installs your everyday tools with your system's package manager — and shows you exactly what it is doing.

---

## Why

Setting up a new Linux machine is a list of downloads, a handful of `apt` or `dnf` commands and a browser tab you forgot to close. LinuxUtil Studio turns that list into a single window: pick what you want, click **Install**, watch it happen.

It is a UI-focused version of the logic used in **MacUtil**.

## Features

- **Native Look:** Built with PySide6 (Qt) for a smooth, professional desktop experience.
- **Auto-Detection:** Automatically detects your Distribution (Ubuntu, Fedora, Arch, openSUSE, etc.) and uses the correct native package manager (`apt`, `dnf`, `pacman`, `zypper`).
- **Multi-Format Support:** Install apps from Native repositories, **Flatpak**, or **Snap** with a single click.
- **Search & Filter:** Quickly find the apps you need by name, description, or category.
- **Real-time Logs:** A dedicated console shows exactly what is happening during installation with color-coded output.
- **Easy Management:** Browse through a catalogue of apps organized by category.

## Installation & Running

### Prerequisites
- Python 3.10+
- Your system's package manager (apt, dnf, or pacman are supported)

### Setup
1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd linuxutil-studio
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python3 main.py
   ```

*To run in CLI mode for debugging:*
```bash
python3 main.py --cli
```

## Catalogue
The catalogue is managed in `catalogue.json`. You can add your own custom scripts and apps easily by adding entries to this file.

### Supported Distributions:
- Debian/Ubuntu (apt)
- Fedora/RHEL (dnf)
- Arch Linux (pacman)

## License
MIT — see [LICENSE](LICENSE)
