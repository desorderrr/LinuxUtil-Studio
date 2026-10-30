"""Temas (claro / escuro) do LinuxUtil Studio.

As cores ficam centralizadas aqui: o QSS cuida da estrutura e os widgets que
precisam de cor dinâmica (badges, status, console) leem de ``get_palette()``.
"""

from PySide6.QtCore import QSettings

SETTINGS_ORG = "LinuxUtilStudio"
SETTINGS_APP = "LinuxUtilStudio"
THEME_KEY = "ui/theme"

PALETTES = {
    "light": {
        "bg": "#f4f5f7",
        "surface": "#ffffff",
        "surface_alt": "#fafbfc",
        "border": "#e1e4e8",
        "text": "#1d1d1f",
        "text_muted": "#6b7280",
        "accent": "#0a84ff",
        "accent_hover": "#0071e3",
        "accent_soft": "#e8f0fe",
        "success": "#1a7f37",
        "warning": "#b45309",
        "danger": "#c62828",
        "console_bg": "#1e1e1e",
        "console_text": "#d4d4d4",
        "console_cmd": "#569cd6",
        "console_ok": "#4ec9b0",
        "console_err": "#f44747",
        "console_warn": "#dcdcaa",
        "sidebar": "#fafbfc",
        "shadow": "#00000018",
    },
    "dark": {
        "bg": "#17191d",
        "surface": "#212429",
        "surface_alt": "#1d2024",
        "border": "#32363d",
        "text": "#e6e8eb",
        "text_muted": "#9aa1ab",
        "accent": "#3d9bff",
        "accent_hover": "#5aa9ff",
        "accent_soft": "#1e3050",
        "success": "#4ec9b0",
        "warning": "#e0a83c",
        "danger": "#f0645c",
        "console_bg": "#121417",
        "console_text": "#cfd3d8",
        "console_cmd": "#7fb3e8",
        "console_ok": "#6fd6bd",
        "console_err": "#ff7b72",
        "console_warn": "#e3d38a",
        "sidebar": "#1d2024",
        "shadow": "#00000040",
    },
}

BADGE_COLORS = {
    "light": {"native": "#0a84ff", "flatpak": "#1a7f37", "snap": "#c2410c"},
    "dark": {"native": "#3d9bff", "flatpak": "#2ea043", "snap": "#e07a3f"},
}


def get_palette(name="light"):
    return PALETTES.get(name, PALETTES["light"])


def badge_color(theme, package_type):
    return BADGE_COLORS.get(theme, BADGE_COLORS["light"]).get(package_type, "#6c757d")


def stylesheet(name="light"):
    """QSS global. ``{chave}`` é substituído pelo valor da paleta."""
    p = get_palette(name)
    return f"""
QMainWindow, QWidget#Central {{
    background-color: {p['bg']};
    color: {p['text']};
}}
QWidget {{
    color: {p['text']};
}}

QFrame#Sidebar {{
    background-color: {p['sidebar']};
    border-right: 1px solid {p['border']};
}}
QLabel#Brand {{
    color: {p['text']};
    font-size: 15px;
    font-weight: 700;
}}
QLabel#BrandSub {{
    color: {p['text_muted']};
    font-size: 11px;
}}

QLineEdit#SearchBar {{
    background-color: {p['surface']};
    border: 1px solid {p['border']};
    border-radius: 6px;
    padding: 7px 9px;
    selection-background-color: {p['accent']};
}}
QLineEdit#SearchBar:focus {{
    border: 1px solid {p['accent']};
}}

QListWidget#CategoryList {{
    border: none;
    background: transparent;
    outline: none;
    font-size: 13px;
}}
QListWidget#CategoryList::item {{
    padding: 6px 8px;
    border-radius: 6px;
    color: {p['text_muted']};
}}
QListWidget#CategoryList::item:hover {{
    background-color: {p['accent_soft']};
    color: {p['text']};
}}
QListWidget#CategoryList::item:selected {{
    background-color: {p['accent_soft']};
    color: {p['accent']};
    font-weight: 600;
}}

QWidget#ContentArea, QWidget#CardContainer, QScrollArea#AppScroll,
QScrollArea#AppScroll > QWidget > QWidget {{
    background-color: {p['bg']};
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p['border']};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p['text_muted']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0;
}}

QLabel#EmptyState {{
    color: {p['text_muted']};
    font-size: 13px;
    padding: 40px;
}}

QTextEdit#Console {{
    background-color: {p['console_bg']};
    color: {p['console_text']};
    border: none;
    border-top: 1px solid {p['border']};
    padding: 10px;
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 12px;
}}

QPushButton#ThemeToggle {{
    background-color: transparent;
    border: 1px solid {p['border']};
    border-radius: 6px;
    padding: 6px 8px;
    color: {p['text_muted']};
    font-size: 12px;
}}
QPushButton#ThemeToggle:hover {{
    background-color: {p['accent_soft']};
    color: {p['accent']};
    border: 1px solid {p['accent']};
}}
"""


def load_saved_theme():
    settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
    value = settings.value(THEME_KEY, "light")
    return value if value in PALETTES else "light"


def save_theme(name):
    QSettings(SETTINGS_ORG, SETTINGS_APP).setValue(THEME_KEY, name)
