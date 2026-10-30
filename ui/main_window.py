import sys
import html

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QTextEdit, QLineEdit,
    QFrame, QScrollArea,
)

from core.catalogue_loader import load_catalogue
from core.installer import Installer
from ui import icons, theme as theme_mod


# ----------------------------------------------------------------------
# Workers (executam fora da thread da interface)
# ----------------------------------------------------------------------
class InstallWorker(QThread):
    """Roda a instalação em background e transmite o log linha a linha."""
    line = Signal(str)
    done = Signal(dict)

    def __init__(self, package_name, package_type):
        super().__init__()
        self.package_name = package_name
        self.package_type = package_type

    def run(self):
        installer = Installer()
        result = installer.run_install(
            self.package_name,
            self.package_type,
            on_output=self.line.emit,
        )
        self.done.emit(result)


class StatusWorker(QThread):
    """Verifica em background quais apps do catálogo já estão instalados."""
    found = Signal(str, bool)

    def __init__(self, apps):
        super().__init__()
        self.apps = apps

    def run(self):
        installer = Installer()
        for app in self.apps:
            try:
                installed = installer.is_installed(
                    app["package_name"], app.get("package_type")
                )
            except Exception:
                installed = False
            self.found.emit(app["id"], installed)


# ----------------------------------------------------------------------
# Card de aplicativo
# ----------------------------------------------------------------------
class AppCard(QFrame):
    """Widget para representar um aplicativo individual."""

    def __init__(self, app_data, install_callback, palette, theme_name):
        super().__init__()
        self.app_data = app_data
        self.palette = palette
        self.theme_name = theme_name
        self.setMinimumHeight(92)
        self.setObjectName("AppCard")
        self.setStyleSheet(
            "QFrame#AppCard {{ border: 1px solid {border}; border-radius: 10px;"
            " background: {surface}; }}"
            "QFrame#AppCard:hover {{ border: 1px solid {accent}; }}".format(**palette)
        )

        layout = QHBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(14, 12, 14, 12)

        # Ícone (tema do sistema ou iniciais desenhadas)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(icons.ICON_SIZE, icons.ICON_SIZE)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_label.setPixmap(icons.app_icon(app_data, palette["accent"]).pixmap(
            icons.ICON_SIZE, icons.ICON_SIZE))
        layout.addWidget(self.icon_label, alignment=Qt.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        self.name_label = QLabel(app_data["name"])
        self.name_label.setStyleSheet(
            "font-weight: 600; font-size: 14px; color: {}; background: transparent;".format(
                palette["text"]))
        name_row.addWidget(self.name_label)

        ptype = app_data.get("package_type", "native")
        self.badge = QLabel(ptype.upper())
        self.badge.setStyleSheet(
            "background-color: {}; color: white; border-radius: 4px;"
            " padding: 1px 6px; font-size: 9px; font-weight: 700;".format(
                theme_mod.badge_color(theme_name, ptype))
        )
        name_row.addWidget(self.badge, alignment=Qt.AlignVCenter)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: {}; font-size: 11px; font-weight: 600; background: transparent;".format(
                palette["success"]))
        name_row.addWidget(self.status_label, alignment=Qt.AlignVCenter)
        name_row.addStretch()

        self.desc_label = QLabel(app_data["description"])
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(
            "color: {}; font-size: 12px; background: transparent;".format(
                palette["text_muted"]))

        text_layout.addLayout(name_row)
        text_layout.addWidget(self.desc_label)

        self.install_btn = QPushButton("Install")
        self.install_btn.setFixedSize(92, 32)
        self.install_btn.setCursor(Qt.PointingHandCursor)
        self._style_button(palette)

        self.install_btn.clicked.connect(lambda: install_callback(self.app_data))

        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(self.install_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

    def _style_button(self, p):
        self.install_btn.setStyleSheet(
            "QPushButton {{ background-color: {accent}; color: #ffffff; border: none;"
            " border-radius: 6px; font-weight: 600; font-size: 12px; }}"
            "QPushButton:hover {{ background-color: {accent_hover}; }}"
            "QPushButton:disabled {{ background-color: {border}; color: {text_muted}; }}".format(**p)
        )

    # -- estado ---------------------------------------------------------
    def mark_installed(self, installed):
        if installed:
            self.status_label.setText("● Installed")
            self.install_btn.setText("Reinstall")
        else:
            self.status_label.setText("")
            self.install_btn.setText("Install")

    def set_busy(self, busy):
        self.install_btn.setEnabled(not busy)
        if busy:
            self.status_label.setText("● Working...")
            self.status_label.setStyleSheet(
                "color: {}; font-size: 11px; font-weight: 600; background: transparent;".format(
                    self.palette["accent"]))


# ----------------------------------------------------------------------
# Janela principal
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LinuxUtil Studio")
        self.resize(1040, 740)

        self.catalogue = load_catalogue()
        self.cards = {}
        self.installed_state = set()
        self.install_worker = None
        self.status_worker = None
        self.busy = False

        self.theme_name = theme_mod.load_saved_theme()
        self.palette = theme_mod.get_palette(self.theme_name)

        central_widget = QWidget()
        central_widget.setObjectName("Central")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # ---------------- Sidebar ----------------
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(248)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(10)

        brand = QLabel("LinuxUtil Studio")
        brand.setObjectName("Brand")
        self.brand_sub = QLabel("")
        self.brand_sub.setObjectName("BrandSub")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(self.brand_sub)

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("SearchBar")
        self.search_bar.setPlaceholderText("Search apps...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self.filter_apps)
        sidebar_layout.addWidget(self.search_bar)

        self.category_list = QListWidget()
        self.category_list.setObjectName("CategoryList")
        all_item = QListWidgetItem("All")
        all_item.setData(Qt.UserRole, "All")
        self.category_list.addItem(all_item)
        for category in sorted({app["category"] for app in self.catalogue}):
            count = sum(1 for app in self.catalogue if app["category"] == category)
            item = QListWidgetItem(f"{category}  ·  {count}")
            item.setData(Qt.UserRole, category)
            self.category_list.addItem(item)
        self.category_list.setCurrentRow(0)
        self.category_list.currentRowChanged.connect(self.filter_apps)
        sidebar_layout.addWidget(self.category_list, stretch=1)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("ThemeToggle")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("Alternar tema claro/escuro (Ctrl+D)")
        self.theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        # ---------------- Conteúdo ----------------
        content_area = QWidget()
        content_area.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(18, 18, 18, 18)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("AppScroll")
        self.scroll_area.setWidgetResizable(True)

        self.container_widget = QWidget()
        self.container_widget.setObjectName("CardContainer")
        self.app_container = QVBoxLayout(self.container_widget)
        self.app_container.setSpacing(10)
        self.app_container.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.container_widget)
        content_layout.addWidget(self.scroll_area)

        top_layout.addWidget(sidebar)
        top_layout.addWidget(content_area, stretch=1)
        main_layout.addWidget(top_container, stretch=1)

        # ---------------- Console ----------------
        self.console = QTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(170)
        main_layout.addWidget(self.console)

        self.theme_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        self.theme_shortcut.activated.connect(self.toggle_theme)

        self.apply_theme(self.theme_name)
        self._update_summary()
        self.populate_apps()
        self.start_status_check()

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------
    def apply_theme(self, name):
        self.theme_name = name
        self.palette = theme_mod.get_palette(name)
        self.setStyleSheet(theme_mod.stylesheet(name))

        is_dark = name == "dark"
        self.theme_btn.setText("☀  Light mode" if is_dark else "🌙  Dark mode")

        # O console mantém fundo escuro nos dois temas, mas o tom acompanha.
        self.console.setStyleSheet(
            "QTextEdit#Console {{ background-color: {console_bg}; color: {console_text};"
            " border: none; padding: 10px; font-size: 12px;"
            " font-family: 'JetBrains Mono', 'DejaVu Sans Mono', 'Courier New', monospace; }}"
            .format(**self.palette))

    def toggle_theme(self):
        new_theme = "light" if self.theme_name == "dark" else "dark"
        theme_mod.save_theme(new_theme)
        self.apply_theme(new_theme)
        # Recria os cards para aplicar as cores do novo tema.
        self.populate_apps(self._current_filter())

    # ------------------------------------------------------------------
    # Catálogo / filtros
    # ------------------------------------------------------------------
    def _current_filter(self):
        text = self.search_bar.text().strip().lower()
        item = self.category_list.currentItem()
        category = item.data(Qt.UserRole) if item else "All"
        return [
            app for app in self.catalogue
            if (not text or text in app["name"].lower() or text in app["description"].lower())
            and (category in ("", "All") or app["category"] == category)
        ]

    def _clear_cards(self):
        while self.app_container.count():
            item = self.app_container.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards.clear()

    def populate_apps(self, apps=None):
        self._clear_cards()
        if apps is None:
            apps = self.catalogue

        if not apps:
            empty = QLabel("No apps match your search.")
            empty.setObjectName("EmptyState")
            empty.setAlignment(Qt.AlignCenter)
            self.app_container.addWidget(empty)
            self.app_container.addStretch()
            return

        for app in apps:
            card = AppCard(app, self.handle_install, self.palette, self.theme_name)
            # Preserva o estado conhecido ao filtrar ou trocar de tema.
            card.mark_installed(app["id"] in self.installed_state)
            card.set_busy(self.busy)
            self.cards[app["id"]] = card
            self.app_container.addWidget(card)

        self.app_container.addStretch()

    def filter_apps(self):
        self.populate_apps(self._current_filter())

    def _update_summary(self):
        self.brand_sub.setText(
            f"{len(self.catalogue)} apps · {len(self.installed_state)} installed")

    # ------------------------------------------------------------------
    # Verificação de estado
    # ------------------------------------------------------------------
    def start_status_check(self):
        self.status_worker = StatusWorker(self.catalogue)
        self.status_worker.found.connect(self.on_status_found)
        self.status_worker.start()

    def on_status_found(self, app_id, installed):
        if installed:
            self.installed_state.add(app_id)
        else:
            self.installed_state.discard(app_id)
        card = self.cards.get(app_id)
        if card:
            card.mark_installed(installed)
            card.set_busy(self.busy)
        self._update_summary()

    # ------------------------------------------------------------------
    # Instalação
    # ------------------------------------------------------------------
    def log(self, text, color=None):
        color = color or self.palette["console_text"]
        self.console.append(f"<span style='color: {color};'>{html.escape(text)}</span>")
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum())

    def set_all_busy(self, busy):
        self.busy = busy
        for card in self.cards.values():
            card.set_busy(busy)

    def handle_install(self, app_data):
        if self.install_worker and self.install_worker.isRunning():
            self.log("[!] An installation is already running.", self.palette["console_warn"])
            return

        pkg = app_data["package_name"]
        ptype = app_data.get("package_type")

        self.console.clear()
        self.set_all_busy(True)
        self.log(
            f"[*] Installing {app_data['name']} ({ptype or 'native'})...",
            self.palette["console_cmd"],
        )

        self.install_worker = InstallWorker(pkg, ptype)
        self.install_worker.line.connect(lambda line: self.log(line))
        self.install_worker.done.connect(
            lambda result: self.on_install_done(app_data, result))
        self.install_worker.start()

    def on_install_done(self, app_data, result):
        self.set_all_busy(False)
        card = self.cards.get(app_data["id"])

        if result["status"] == "success":
            self.installed_state.add(app_data["id"])
            self._update_summary()
            self.log(f"[+] Done: {app_data['name']} installed.", self.palette["console_ok"])
            if card:
                card.mark_installed(True)
        else:
            self.log(f"[-] Error: {result['message']}", self.palette["console_err"])
            if card:
                card.mark_installed(app_data["id"] in self.installed_state)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
