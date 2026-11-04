# Changelog

All notable changes to LinuxUtil Studio are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- CLI interactive mode (`--cli`) no longer crashes because `installer` was
  never initialised.
- `--dry-run` now prints native/Flatpak/Snap commands without executing them
  (previously only setup scripts honoured the flag).

### Changed

- `install.sh` validates `rsync` and `python3-venv`, moves a previous install
  to a timestamped backup instead of deleting it, and no longer fails when
  `chmod` cannot touch the venv interpreter.

### Added

- `flatpak/build.sh` downloads the PySide6 wheels and builds the bundle from a
  clean clone.
- Flatpak sandbox detection: package operations are delegated to the host via
  `flatpak-spawn --host`.
- Test covering the `--dry-run` guarantee.

## [1.0.0] - 2026-11-01

### Added

- 55-app catalogue across 9 categories with per-distro package names.
- Native (`apt`, `dnf`, `pacman`, `zypper`), Flatpak and Snap backends.
- Gaming setup packs for Fedora, Debian/Ubuntu and Arch/CachyOS.
- PySide6 GUI with light/dark themes and SVG app logos.
- CLI (`--list`, `--info`, `--install`, `--cli`, `--dry-run`).
- `install.sh`, AppImage and Flatpak distribution.
- Test suite, GitHub Actions CI and documentation.
