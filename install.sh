#!/bin/bash
set -e

# Cores para mensagens
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Iniciando instalação do LinuxUtil Studio...${NC}"

# 1. Verificar dependências básicas
if ! command -v python3 &> /dev/null; then
    echo "❌ Erro: Python 3 não encontrado. Por favor, instale o Python antes de continuar."
    exit 1
fi

# 2. Definir diretórios
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
INSTALL_DIR="$HOME/.local/share/linuxutil-studio"

echo -e "${BLUE}📦 Preparando pasta de instalação em: $INSTALL_DIR${NC}"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

echo -e "${BLUE}📦 Copiando ficheiros...${NC}"
# Usar rsync com filtros para evitar recursividade e copiar apenas o necessário
rsync -av --progress \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='install.sh' \
    --exclude='.opencode' \
    --exclude='tests' \
    --exclude='__pycache__' \
    --exclude=".local" \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"

cd "$INSTALL_DIR"

# 3. Criar ambiente virtual
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}🐍 Criando ambiente virtual (.venv)...${NC}"
    python3 -m venv .venv
fi

# 4. Instalar dependências
echo -e "${BLUE}📥 Instalando dependências (PySide6)...${NC}"
./.venv/bin/pip install -U pip
./.venv/bin/pip install -r requirements.txt

# 5. Criar atalho no menu de aplicativos (.desktop)
echo -e "${BLUE}🎨 Criando atalho no menu de aplicativos...${NC}"
DESKTOP_FILE="$HOME/.local/share/applications/linuxutil-studio.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=LinuxUtil Studio
Comment=Instalador de ferramentas Linux
Exec=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/main.py
Icon=$INSTALL_DIR/assets/logos/vscode.svg
Terminal=false
Type=Application
Categories=Utility;Development;
StartupNotify=true
EOF

# Garantir permissões corretas
chmod +x "$INSTALL_DIR/main.py" 2>/dev/null || true

echo -e "${GREEN}✅ Instalação concluída com sucesso!${NC}"
echo -e "${BLUE}A aplicação 'LinuxUtil Studio' agora deve aparecer no seu menu de aplicativos.${NC}"
