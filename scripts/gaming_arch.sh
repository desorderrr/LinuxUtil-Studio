#!/usr/bin/env bash
# LinuxUtil Studio -- Gaming Pack for Arch Linux / CachyOS / Manjaro / EndeavourOS
#
# Installs the usual Linux gaming stack:
#   native:  lutris, mangohud, gamemode, gamescope, vulkan-tools,
#            vulkan-radeon, vulkan-intel, wine + winetricks when multilib is on
#   flatpak: Steam, Heroic, Bottles, Prism Launcher
#
# Steam comes from the official Flatpak so the script never has to edit
# /etc/pacman.conf to enable [multilib].
#
# Usage:  ./gaming_arch.sh [--dry-run]
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
        run pacman -S --needed --noconfirm "$@"
        return 0
    fi
    if ! pacman -S --needed --noconfirm "$@" </dev/null; then
        note "bulk install failed, retrying one package at a time"
        local pkg
        for pkg in "$@"; do
            pacman -S --needed --noconfirm "$pkg" </dev/null || skip "$pkg"
        done
    fi
}

install_flatpaks() {
    local app
    for app in "$@"; do
        run flatpak install --system -y --noninteractive flathub "$app" </dev/null || skip "flatpak:$app"
    done
}

has_multilib() { grep -qE '^[[:space:]]*\[multilib\]' /etc/pacman.conf 2>/dev/null; }

command -v pacman >/dev/null 2>&1 || { printf '[!] pacman not found: this script is for Arch-based distros.\n' >&2; exit 1; }

step "System packages (official repositories)"
install_native lutris mangohud gamemode gamescope vulkan-tools vulkan-radeon vulkan-intel

step "Wine"
if has_multilib; then
    install_native wine winetricks
else
    note "multilib is disabled in /etc/pacman.conf, so wine was not installed."
    note "Enable the [multilib] repo and re-run, or just use Bottles (Flatpak)."
fi

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
printf '[+] Gaming pack ready. Reboot or log out and back in so GameMode and MangoHud pick up your user groups.\n'
