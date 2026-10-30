"""Ícones dos cards.

Estratégia, em ordem de preferência:

1. Logo do app em ``assets/logos/<id>.svg`` (Simple Icons, CC0), desenhado
   sobre um azulejo arredondado para ficar legível nos dois temas.
2. ``icon`` do catálogo / lista de nomes do tema (``ICON_CANDIDATES``).
3. Não achou? Desenha um quadrado arredondado com as iniciais do app.

O fallback desenhado garante que nada quebra em desktops sem tema de ícones.
"""

import os
import re

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap

try:  # QtSvg vem no PySide6-Essentials, mas não custa proteger.
    from PySide6.QtSvg import QSvgRenderer
except ImportError:  # pragma: no cover
    QSvgRenderer = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(PROJECT_ROOT, "assets", "logos")

# Nomes alternativos usados por diferentes temas (Breeze, Adwaita, Papirus...).
ICON_CANDIDATES = {
    "chrome": ["google-chrome", "chrome", "web-browser"],
    "chromium": ["chromium", "chromium-browser", "web-browser"],
    "firefox": ["firefox", "firefox-esr", "web-browser"],
    "vscode": ["vscode", "code", "com.visualstudio.code", "text-editor"],
    "python3": ["python3", "python", "text-x-python"],
    "htop": ["htop", "utilities-system-monitor", "system-monitor"],
    "btop": ["btop", "utilities-system-monitor", "system-monitor"],
    "curl": ["curl", "network-transmit-receive", "web-browser"],
    "wget": ["wget", "network-down", "download"],
    "unzip": ["unzip", "package-x-generic", "archive-manager", "application-x-archive"],
    "vlc": ["vlc", "multimedia-player", "video-x-generic", "multimedia-video-player"],
    "gimp": ["gimp", "applications-graphics", "image-x-generic"],
    "mpv": ["mpv", "multimedia-player", "video-x-generic"],
    "spotify": ["spotify", "spotify-client", "multimedia-audio-player", "audio-x-generic"],
    "discord": ["discord", "internet-chat", "user-available", "internet-messenger"],
    "slack": ["slack", "internet-chat", "internet-messenger"],
    "telegram": ["telegram", "internet-chat", "internet-messenger"],
    "steam": ["steam", "applications-games", "applications-games"],
    "lutris": ["lutris", "applications-games"],
    "libreoffice": ["libreoffice", "libreoffice-startcenter", "x-office-document"],
    "thunderbird": ["thunderbird", "internet-mail"],
    "gparted": ["gparted", "drive-harddisk", "dialog-information"],
    "timeshift": ["timeshift", "drive-harddisk"],
    "gaming-pack": ["applications-games", "applications-games"],
    "flatseal": ["flatseal", "com.github.tchx84.Flatseal", "applications-system"],
}

ICON_SIZE = 38

# Cores de marca usadas quando não há SVG: o fallback fica parecido com o app.
BRAND_COLORS = {
    "vscode": "#007ACC",
    "slack": "#4A154B",
    "vlc": "#FF8800",
    "bottles": "#2C3E50",
    "prism": "#3C8527",
    "mangohud": "#E0A030",
    "gamemode": "#7C3AED",
    "gamescope": "#2F9E63",
    "gparted": "#3E9E4E",
    "timeshift": "#00A3E0",
    "flatseal": "#5C6BC0",
    "btop": "#0F9BB0",
    "darktable": "#B8860B",
    "chromium": "#4285F4",
    "gaming-pack": "#C2410C",
    "wget": "#0F9BB0",
    "unzip": "#B8860B",
    "vscodium": "#2F80ED",
}

# Cores estáveis por app (funcionam nos dois temas) para o fallback desenhado.
FALLBACK_COLORS = [
    "#0a84ff", "#2f9e63", "#c2410c", "#7c5cff",
    "#0f9bb0", "#b8860b", "#d6336c", "#4b7bec",
]

_FILL_RE = re.compile(rb'fill="(#[0-9a-fA-F]{3,6})"')
_LOGO_CACHE = {}


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


def _tile_color(svg_bytes):
    """Fundo do azulejo: claro para logos escuros, escuro para logos claros."""
    match = _FILL_RE.search(svg_bytes)
    color = QColor(match.group(1).decode()) if match else QColor()
    if not color.isValid():
        return "#f4f5f7"
    luminance = 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
    return "#1b1d21" if luminance > 0.72 else "#f4f5f7"


def _logo_pixmap(app_id, size=ICON_SIZE):
    """Renderiza o logo SVG do app num azulejo arredondado, ou None."""
    if QSvgRenderer is None or not app_id:
        return None

    key = (app_id, size)
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]

    path = os.path.join(LOGO_DIR, f"{app_id}.svg")
    if not os.path.exists(path):
        return None

    with open(path, "rb") as handle:
        data = handle.read()

    renderer = QSvgRenderer(QByteArray(data))
    if not renderer.isValid():
        return None

    scale = 2  # desenha em 2x para ficar nítido em ecrãs HiDPI
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    tile = QPainterPath()
    tile.addRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    painter.fillPath(tile, QColor(_tile_color(data)))

    inset = size * 0.19
    renderer.render(painter, QRectF(inset, inset, size - 2 * inset, size - 2 * inset))
    painter.end()

    _LOGO_CACHE[key] = pixmap
    return pixmap


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
    """Retorna um QIcon para o app: logo SVG → ícone do tema → iniciais."""
    app_id = app_data.get("id", "")

    pixmap = _logo_pixmap(app_id)
    if pixmap is not None:
        return QIcon(pixmap)

    candidates = []
    if app_data.get("icon"):
        candidates.append(app_data["icon"])
    candidates.extend(ICON_CANDIDATES.get(app_id, []))

    icon = _theme_icon(candidates)
    if icon is not None:
        return icon

    color = BRAND_COLORS.get(app_id) or _stable_color(app_id or app_data.get("name", ""))
    return QIcon(_fallback_pixmap(app_data.get("name", "?"), color))


def icon_size():
    return QSize(ICON_SIZE, ICON_SIZE)
