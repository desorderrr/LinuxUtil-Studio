#!/usr/bin/env bash
# LinuxUtil Studio -- Gaming Pack for openSUSE (Leap / Tumbleweed)
#
# Installs the usual Linux gaming stack:
#   native:  lutris, mangohud, gamemode, gamescope, wine, winetricks,
#            vulkan-tools, Mesa Vulkan drivers
#   flatpak: Steam, Heroic, Bottles, Prism Launcher
#
# Steam comes from the official Flatpak on purpose: no extra repositories and
# no 32-bit setup, and it ships its own runtime.
#
# Usage:  ./gaming_suse.sh [--dry-run]
#         --dry-run only prints the commands, nothing is installed.

set -uo pipefail

DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
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

# Deteta se um pacote existe nos repositórios configurados (sem instalar).
pkg_available() {
    local output column
    output="$(zypper search -x "$1" 2>/dev/null)" || return 1
    while IFS='|' read -r -a columns; do
        for column in "${columns[@]}"; do
            column="${column#"${column%%[![:space:]]*}"}"
            column="${column%"${column##*[![:space:]]}"}"
            [[ "$column" == "$1" ]] && return 0
        done
    done <<< "$output"
    return 1
}

install_native() {
    local pkgs=("$@")
    # Filtrar pacotes inexistentes (detecção de disponibilidade).
    local available=()
    local p
    for p in "${pkgs[@]}"; do
        if (( DRY_RUN )); then
            available+=("$p")
        elif pkg_available "$p"; then
            available+=("$p")
        else
            skip "not-available:$p"
        fi
    done
    if (( ${#available[@]} == 0 )); then
        note "no available packages in this group"
        return 0
    fi
    if (( DRY_RUN )); then
        run zypper install -y "${available[@]}"
        return 0
    fi
    if ! zypper install -y --no-recommends "${available[@]}" </dev/null; then
        note "bulk install failed, retrying one package at a time"
        for p in "${available[@]}"; do
            zypper install -y "$p" </dev/null || skip "$p"
        done
    fi
}

install_flatpaks() {
    local app
    for app in "$@"; do
        run flatpak install --system -y --noninteractive flathub "$app" </dev/null || skip "flatpak:$app"
    done
}

command -v zypper >/dev/null 2>&1 || { printf '[!] zypper not found: this script is for openSUSE.\n' >&2; exit 1; }

step "System packages (openSUSE repositories)"
install_native lutris mangohud gamemode gamescope wine winetricks vulkan-tools Mesa-vulkan-drivers

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
