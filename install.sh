#!/bin/bash
set -euo pipefail

# Cores para mensagens
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

fail() {
    echo -e "${RED}❌ $*${NC}" >&2
    exit 1
}

trap 'echo -e "${RED}❌ Instalação interrompida (linha $LINENO).${NC}" >&2' ERR

echo -e "${BLUE}🚀 Iniciando instalação do LinuxUtil Studio...${NC}"

# 1. Verificar dependências básicas
command -v python3 >/dev/null 2>&1 || fail "Python 3 não encontrado. Instale o Python 3 antes de continuar."
command -v rsync   >/dev/null 2>&1 || fail "rsync não encontrado. Instale com: sudo dnf install rsync  (ou apt install rsync)."

if ! python3 -m venv --help >/dev/null 2>&1; then
    fail "O módulo venv do Python não está disponível. Em Debian/Ubuntu: sudo apt install python3-venv."
fi

# 2. Definir diretórios
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
INSTALL_DIR="$HOME/.local/share/linuxutil-studio"

# 3. Preservar uma instalação anterior em vez de a apagar sem aviso
if [ -d "$INSTALL_DIR" ]; then
    BACKUP="$INSTALL_DIR.bak.$(date +%Y%m%d-%H%M%S)"
    echo -e "${BLUE}📦 Instalação anterior movida para: $BACKUP${NC}"
    mv "$INSTALL_DIR" "$BACKUP"
fi
mkdir -p "$INSTALL_DIR"

echo -e "${BLUE}📦 Copiando ficheiros...${NC}"
# rsync copia apenas o necessário, sem .git/venv/artefactos de build.
rsync -a --info=progress2 \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='install.sh' \
    --exclude='.opencode' \
    --exclude='tests' \
    --exclude='__pycache__' \
    --exclude='.local' \
    --exclude='*.AppImage' \
    --exclude='*.flatpak' \
    --exclude='flatpak/wheels' \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"

cd "$INSTALL_DIR"

# 4. Criar ambiente virtual
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}🐍 Criando ambiente virtual (.venv)...${NC}"
    python3 -m venv .venv
fi

# 5. Instalar dependências
echo -e "${BLUE}📥 Instalando dependências (PySide6)...${NC}"
./.venv/bin/pip install -U pip
./.venv/bin/pip install -r requirements.txt

# 6. Criar atalho no menu de aplicativos (.desktop)
echo -e "${BLUE}🎨 Criando atalho no menu de aplicativos...${NC}"
DESKTOP_FILE="$HOME/.local/share/applications/linuxutil-studio.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=LinuxUtil Studio
Comment=Instalador de ferramentas Linux
Exec=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/main.py
Icon=$INSTALL_DIR/assets/logo.svg
Terminal=false
Type=Application
Categories=Utility;
StartupNotify=true
EOF

chmod +x "$INSTALL_DIR/main.py" 2>/dev/null || true

echo -e "${GREEN}✅ Instalação concluída com sucesso!${NC}"
echo -e "${BLUE}A aplicação 'LinuxUtil Studio' agora deve aparecer no seu menu de aplicativos.${NC}"
