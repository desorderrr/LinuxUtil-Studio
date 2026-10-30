import sys
import html

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QPushButton, QTextEdit, QLineEdit, QFrame,
    QScrollArea,
)

from core.catalogue_loader import load_catalogue
from core.installer import Installer


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

    def __init__(self, app_data, install_callback):
        super().__init__()
        self.app_data = app_data
        self.setMinimumHeight(110)
        self.setObjectName("AppCard")
        self.setStyleSheet(
            "QFrame#AppCard { border: 1px solid #ddd; border-radius: 8px; "
            "background: #ffffff; }"
        )

        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 12, 15, 12)

        text_layout = QVBoxLayout()

        name_row = QHBoxLayout()
        self.name_label = QLabel(app_data["name"])
        self.name_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #222;")

        ptype = app_data.get("package_type", "native")
        colors = {"native": "#0A84FF", "flatpak": "#28a745", "snap": "#ff9800"}
        self.badge = QLabel(ptype.upper())
        self.badge.setStyleSheet(
            f"background-color: {colors.get(ptype, '#6c757d')}; color: white;"
            "border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        )

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #28a745; font-size: 11px; font-weight: bold;")

        name_row.addWidget(self.name_label)
        name_row.addWidget(self.badge)
        name_row.addWidget(self.status_label)
        name_row.addStretch()

        self.desc_label = QLabel(app_data["description"])
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #555; font-size: 12px;")

        text_layout.addLayout(name_row)
        text_layout.addWidget(self.desc_label)

        self.install_btn = QPushButton("Install")
        self.install_btn.setFixedSize(90, 32)
        self.install_btn.setCursor(Qt.PointingHandCursor)
        self.install_btn.setStyleSheet(
            "QPushButton { background-color: #0A84FF; color: white; border-radius: 4px;"
            " font-weight: bold; }"
            "QPushButton:hover { background-color: #007aff; }"
            "QPushButton:disabled { background-color: #adb5bd; }"
        )
        self.install_btn.clicked.connect(lambda: install_callback(self.app_data))

        layout.addLayout(text_layout)
        layout.addWidget(self.install_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

    def mark_installed(self, installed):
        if installed:
            self.status_label.setText("● Installed")
            self.install_btn.setText("Reinstall")

    def set_busy(self, busy):
        self.install_btn.setEnabled(not busy)
        if busy:
            self.status_label.setText("● Working...")
            self.status_label.setStyleSheet("color: #0A84FF; font-size: 11px; font-weight: bold;")


# ----------------------------------------------------------------------
# Janela principal
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LinuxUtil Studio")
        self.resize(1000, 720)

        self.catalogue = load_catalogue()
        self.cards = {}
        self.install_worker = None
        self.status_worker = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("background-color: #f8f9fa; border-right: 1px solid #dee2e6;")
        sidebar_layout = QVBoxLayout(sidebar)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search apps...")
        self.search_bar.setStyleSheet(
            "padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 10px;"
        )
        self.search_bar.textChanged.connect(self.filter_apps)
        sidebar_layout.addWidget(self.search_bar)

        self.category_list = QListWidget()
        self.category_list.setStyleSheet("border: none; font-size: 13px; background: transparent;")
        categories = ["All"] + sorted({app["category"] for app in self.catalogue})
        self.category_list.addItems(categories)
        self.category_list.currentTextChanged.connect(self.filter_apps)
        sidebar_layout.addWidget(self.category_list)

        # Área de conteúdo
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: #ffffff;")

        self.container_widget = QWidget()
        self.app_container = QVBoxLayout(self.container_widget)
        self.app_container.addStretch()

        self.scroll_area.setWidget(self.container_widget)
        content_layout.addWidget(self.scroll_area)

        top_layout.addWidget(sidebar)
        top_layout.addWidget(content_area)
        main_layout.addWidget(top_container)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(160)
        self.console.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: 'Courier New';"
            "padding: 10px; font-size: 12px;"
        )
        main_layout.addWidget(self.console)

        self.populate_apps()
        self.start_status_check()

    # ------------------------------------------------------------------
    # Catálogo / filtros
    # ------------------------------------------------------------------
    def populate_apps(self, apps=None):
        while self.app_container.count() > 1:
            child = self.app_container.takeAt(1)
            if child.widget():
                child.widget().deleteLater()

        self.cards.clear()
        if apps is None:
            apps = self.catalogue

        for app in apps:
            card = AppCard(app, self.handle_install)
            self.cards[app["id"]] = card
            self.app_container.insertWidget(0, card)

    def filter_apps(self):
        search_text = self.search_bar.text().lower()
        category = self.category_list.currentText()

        filtered = [
            app for app in self.catalogue
            if (search_text in app["name"].lower() or search_text in app["description"].lower())
            and (category == "All" or app["category"] == category)
        ]
        self.populate_apps(filtered)

    # ------------------------------------------------------------------
    # Verificação de estado
    # ------------------------------------------------------------------
    def start_status_check(self):
        self.status_worker = StatusWorker(self.catalogue)
        self.status_worker.found.connect(self.on_status_found)
        self.status_worker.start()

    def on_status_found(self, app_id, installed):
        card = self.cards.get(app_id)
        if card:
            card.mark_installed(installed)

    # ------------------------------------------------------------------
    # Instalação
    # ------------------------------------------------------------------
    def log(self, text, color="#d4d4d4"):
        self.console.append(f"<span style='color: {color};'>{html.escape(text)}</span>")
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def set_all_busy(self, busy):
        for card in self.cards.values():
            card.set_busy(busy)

    def handle_install(self, app_data):
        if self.install_worker and self.install_worker.isRunning():
            self.log("[!] An installation is already running.", "#dcdcaa")
            return

        pkg = app_data["package_name"]
        ptype = app_data.get("package_type")

        self.set_all_busy(True)
        self.log(f"[*] Starting installation of {app_data['name']} ({ptype or 'native'})...", "#569cd6")

        self.install_worker = InstallWorker(pkg, ptype)
        self.install_worker.line.connect(lambda line: self.log(line))
        self.install_worker.done.connect(lambda result: self.on_install_done(app_data, result))
        self.install_worker.start()

    def on_install_done(self, app_data, result):
        self.set_all_busy(False)
        card = self.cards.get(app_data["id"])

        if result["status"] == "success":
            self.log(f"[+] Success: {app_data['name']} installed.", "#4ec9b0")
            if card:
                card.mark_installed(True)
                card.status_label.setStyleSheet(
                    "color: #28a745; font-size: 11px; font-weight: bold;"
                )
        else:
            self.log(f"[-] Error: {result['message']}", "#f44747")
            if card:
                card.status_label.setText("")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
