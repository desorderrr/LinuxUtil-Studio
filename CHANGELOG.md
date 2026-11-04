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
- Distribution detection reads `/etc/os-release` and recognizes compatible
  distributions through `ID_LIKE`, including openSUSE.
- Invalid catalogue shapes now fail with an explicit entry and field error.
- Installation-state checks report timeouts instead of silently showing an app
  as not installed.
- Flatpak builds no longer require pip to be installed in the host Python
  environment.
- Fedora app removal now preserves automatically installed dependencies.

### Changed

- Running installations can be cancelled; already completed system changes
  are not rolled back.
- `install.sh` validates `rsync` and `python3-venv`, moves a previous install
  to a timestamped backup instead of deleting it, and no longer fails when
  `chmod` cannot touch the venv interpreter.

### Added

- Remove action for detected native, Flatpak and Snap apps; setup scripts are
  deliberately excluded and package data/dependencies are not explicitly purged.
- Added confirmed, previewable official vendor-repository installs for VS Code
  and Brave on Debian, Fedora and openSUSE, with Flatpak fallbacks and
  ownership-aware source removal.
- RPM signing keys are checked against pinned fingerprints before use; openSUSE
  imports only the verified vendor repository key during installation.
- Tagged releases run the test suite, build a Flatpak bundle and checksum, and
  attach both to the GitHub release.
- Documented the catalogue's package-source policy and VS Code's official
  distro packages versus its checksummed Flathub build.
- Audited upstream installation channels and recorded the strongest
  distro-specific alternatives without silently adding vendor repositories.
- `flatpak/build.sh` downloads the PySide6 wheels and builds the bundle from a
  clean clone.
- Flatpak sandbox detection: package operations are delegated to the host via
  `flatpak-spawn --host`.
- Test covering the `--dry-run` guarantee.
- Tests covering distro aliases, invalid catalogue data, command failures and
  installation cancellation.

## [1.0.0] - 2026-11-01

### Added

- 55-app catalogue across 9 categories with per-distro package names.
- Native (`apt`, `dnf`, `pacman`, `zypper`), Flatpak and Snap backends.
- Gaming setup packs for Fedora, Debian/Ubuntu and Arch/CachyOS.
- PySide6 GUI with light/dark themes and SVG app logos.
- CLI (`--list`, `--info`, `--install`, `--cli`, `--dry-run`).
- `install.sh`, AppImage and Flatpak distribution.
- Test suite, GitHub Actions CI and documentation.
