"""Ícones dos cards.

Estratégia, em ordem de preferência:

1. ``icon`` do catálogo (nome de ícone do tema, ex. ``"vlc"``).
2. Lista de nomes conhecidos para aquele app (``ICON_CANDIDATES``).
3. Não achou? Desenha um quadrado arredondado com as iniciais do app.

Nada de arquivos de imagem no repositório e nada quebra em desktops sem
tema de ícones (GNOME puro, por exemplo).
"""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap

# Nomes alternativos usados por diferentes temas (Breeze, Adwaita, Papirus...).
ICON_CANDIDATES = {
    "git": ["git", "git-gui", "vcs-git"],
    "neovim": ["nvim", "neovim", "vim", "gvim"],
    "vscode": ["vscode", "code", "com.visualstudio.code", "text-editor"],
    "python3": ["python3", "python", "text-x-python"],
    "htop": ["htop", "utilities-system-monitor", "system-monitor"],
    "curl": ["curl", "network-transmit-receive", "web-browser"],
    "wget": ["wget", "network-down", "download"],
    "unzip": ["unzip", "package-x-generic", "archive-manager", "application-x-archive"],
    "vlc": ["vlc", "multimedia-player", "video-x-generic", "multimedia-video-player"],
    "gimp": ["gimp", "applications-graphics", "image-x-generic"],
    "spotify": ["spotify", "spotify-client", "multimedia-audio-player", "audio-x-generic"],
    "discord": ["discord", "internet-chat", "user-available", "internet-messenger"],
}

ICON_SIZE = 38

# Cores estáveis por app (funcionam nos dois temas) para o fallback desenhado.
FALLBACK_COLORS = [
    "#0a84ff", "#2f9e63", "#c2410c", "#7c5cff",
    "#0f9bb0", "#b8860b", "#d6336c", "#4b7bec",
]


def _stable_color(key):
    if not key:
        return FALLBACK_COLORS[0]
    total = sum(ord(ch) for ch in key)
    return FALLBACK_COLORS[total % len(FALLBACK_COLORS)]


def _theme_icon(candidates):
    for name in candidates:
        if not name:
            continue
        if not QIcon.hasThemeIcon(name):
            continue
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    return None


def _fallback_pixmap(name, color, size=ICON_SIZE):
    """Quadrado arredondado com as iniciais — sempre funciona, em qualquer tema."""
    pixmap = QPixmap(size, size)
    pixmap.setDevicePixelRatio(1.0)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    base = QColor(color)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    painter.fillPath(path, base)

    initials = "".join(part[0] for part in name.split() if part)[:2].upper() or "?"
    font = QFont()
    font.setPixelSize(int(size * 0.42))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, initials)
    painter.end()
    return pixmap


def app_icon(app_data, accent="#0a84ff"):
    """Retorna um QIcon para o app, com fallback desenhado."""
    candidates = []
    if app_data.get("icon"):
        candidates.append(app_data["icon"])
    candidates.extend(ICON_CANDIDATES.get(app_data.get("id", ""), []))

    icon = _theme_icon(candidates)
    if icon is not None:
        return icon

    color = _stable_color(app_data.get("id") or app_data.get("name", ""))
    return QIcon(_fallback_pixmap(app_data.get("name", "?"), color))


def icon_size():
    return QSize(ICON_SIZE, ICON_SIZE)
