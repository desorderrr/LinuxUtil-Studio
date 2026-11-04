#!/bin/bash
# Constrói o bundle Flatpak a partir de um clone limpo.
#
# Uso:
#   bash flatpak/build.sh            # gera linuxutil-studio.flatpak
#   bash flatpak/build.sh --install  # instala também no perfil do utilizador
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
WHEELS="$HERE/wheels"
BUILD_DIR="${TMPDIR:-/tmp}/linuxutil-studio-flatpak-build"
REPO_DIR="${TMPDIR:-/tmp}/linuxutil-studio-flatpak-repo"
BUNDLE="$ROOT/linuxutil-studio.flatpak"

command -v flatpak-builder >/dev/null || {
    echo "Erro: flatpak-builder não está instalado." >&2
    echo "  Fedora: sudo dnf install flatpak-builder" >&2
    echo "  Debian/Ubuntu: sudo apt install flatpak-builder" >&2
    exit 1
}

# O SDK é necessário para compilar/copiar as dependências Python.
if ! flatpak list --runtime 2>/dev/null | grep -q "org.freedesktop.Sdk.*25.08"; then
    echo "Erro: falta o SDK org.freedesktop.Sdk//25.08." >&2
    echo "  flatpak install flathub org.freedesktop.Sdk//25.08" >&2
    exit 1
fi

# As wheels ficam fora do git (são ~260 MB). Baixamo-las numa pasta local
# antes do build; o manifesto instala-as com --no-index, sem rede no sandbox.
if [ ! -d "$WHEELS" ] || [ -z "$(ls -A "$WHEELS" 2>/dev/null)" ]; then
    echo "A descarregar as wheels do PySide6..."
    mkdir -p "$WHEELS"
    PIP_ENV="$(mktemp -d "${TMPDIR:-/tmp}/linuxutil-studio-pip.XXXXXX")"
    trap 'rm -rf -- "$PIP_ENV"' EXIT
    python3 -m venv "$PIP_ENV"
    "$PIP_ENV/bin/python" -m pip download -r "$ROOT/requirements.txt" -d "$WHEELS"
fi

flatpak-builder --force-clean --state-dir="$BUILD_DIR.state" "$BUILD_DIR" \
    --repo="$REPO_DIR" "$HERE/com.linuxutilstudio.Studio.yml"

flatpak build-bundle "$REPO_DIR" "$BUNDLE" com.linuxutilstudio.Studio

echo "Bundle criado: $BUNDLE"

if [ "${1:-}" = "--install" ]; then
    flatpak install --user -y "$BUNDLE"
    echo "Instalado. Corre com: flatpak run com.linuxutilstudio.Studio"
fi
