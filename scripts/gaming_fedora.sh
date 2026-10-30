#!/usr/bin/env bash
# LinuxUtil Studio -- Gaming Pack for Fedora
#
# Installs the usual Linux gaming stack:
#   native:  lutris, mangohud, gamemode, gamescope, wine, winetricks,
#            vulkan-tools, mesa-vulkan-drivers
#   flatpak: Steam, Heroic, Bottles, Prism Launcher
#
# Steam comes from the official Flatpak on purpose: no RPM Fusion and no
# 32-bit repo changes, and it ships its own runtime.
#
# Usage:  ./gaming_fedora.sh [--dry-run]
#         --dry-run only prints the commands, nothing is installed.

set -uo pipefail

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    esac
done

FAILED=()

step() { printf '\n==> %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
run() {
    if (( DRY_RUN )); then
        printf '    [dry-run] %s\n' "$*"
    else
        printf '    $ %s\n' "$*"
        "$@"
    fi
}
skip() { FAILED+=("$1"); printf '    [!] skipped: %s\n' "$1"; }

install_native() {
    if (( DRY_RUN )); then
        run dnf install -y "$@"
        return 0
    fi
    if ! dnf install -y --setopt=install_weak_deps=False "$@" </dev/null; then
        note "bulk install failed, retrying one package at a time"
        local pkg
        for pkg in "$@"; do
            dnf install -y "$pkg" </dev/null || skip "$pkg"
        done
    fi
}

install_flatpaks() {
    local app
    for app in "$@"; do
        run flatpak install --system -y --noninteractive flathub "$app" </dev/null || skip "flatpak:$app"
    done
}

command -v dnf >/dev/null 2>&1 || { printf '[!] dnf not found: this script is for Fedora.\n' >&2; exit 1; }

step "System packages (Fedora repositories)"
install_native lutris mangohud gamemode gamescope wine winetricks vulkan-tools mesa-vulkan-drivers

step "Flatpak and Flathub"
if ! command -v flatpak >/dev/null 2>&1; then
    install_native flatpak
fi
run flatpak remote-add --if-not-exists --system flathub https://flathub.org/repo/flathub.flatpakrepo

step "Games and launchers (Flatpak)"
install_flatpaks com.valvesoftware.Steam com.heroicgameslauncher.hgl com.usebottles.bottles org.prismlauncher.PrismLauncher

step "Done"
if (( DRY_RUN )); then
    printf '[+] Preview finished -- nothing was changed.\n'
    exit 0
fi

missing=()
for bin in lutris mangohud; do
    command -v "$bin" >/dev/null 2>&1 || missing+=("$bin")
done

if (( ${#missing[@]} )); then
    printf '[!] Core gaming tools are missing: %s\n' "${missing[*]}" >&2
    (( ${#FAILED[@]} )) && printf '[!] Skipped: %s\n' "${FAILED[*]}" >&2
    exit 1
fi

if (( ${#FAILED[@]} )); then
    printf '[i] Pack installed, %d optional item(s) skipped: %s\n' \
        "${#FAILED[@]}" "${FAILED[*]}"
fi
printf '[+] Gaming pack ready. Log out and back in so GameMode and MangoHud pick up your user groups.\n'
