import sys
import html
import os
import subprocess
import threading

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QTextEdit, QLineEdit,
    QFrame, QScrollArea, QMessageBox,
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

    def __init__(self, app_data, dry_run=False, operation="install"):
        super().__init__()
        self.app_data = app_data
        self.dry_run = dry_run
        self.operation = operation
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        installer = Installer()
        if self.operation == "remove":
            result = installer.run_remove(
                self.app_data,
                on_output=self.line.emit,
                cancel_event=self.cancel_event,
            )
        else:
            result = installer.run_install(
                self.app_data,
                on_output=self.line.emit,
                dry_run=self.dry_run,
                cancel_event=self.cancel_event,
            )
        self.done.emit(result)


class StatusWorker(QThread):
    """Verifica em background quais apps do catálogo já estão instalados."""
    found = Signal(str, bool)
    failed = Signal(str, str)

    def __init__(self, apps):
        super().__init__()
        self.apps = apps

    def run(self):
        installer = Installer()
        for app in self.apps:
            try:
                installed = installer.is_installed(app)
            except (OSError, subprocess.TimeoutExpired) as error:
                self.failed.emit(app["id"], str(error))
                continue
            self.found.emit(app["id"], installed)


# ----------------------------------------------------------------------
# Card de aplicativo
# ----------------------------------------------------------------------
class AppCard(QFrame):
    """Widget para representar um aplicativo individual."""

    def __init__(
        self, app_data, install_callback, remove_callback, palette, theme_name,
        resolved_package_type=None,
    ):
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
        display_type = resolved_package_type or ptype
        self.is_script = ptype == "script"
        self.is_vendor = ptype == "vendor" and display_type == "vendor"
        self.badge = QLabel(
            "SCRIPT" if self.is_script else "VENDOR" if self.is_vendor else display_type.upper()
        )
        self.badge.setStyleSheet(
            "background-color: {}; color: white; border-radius: 4px;"
            " padding: 1px 6px; font-size: 9px; font-weight: 700;".format(
                theme_mod.badge_color(theme_name, display_type))
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

        self.install_btn = QPushButton("Run setup" if self.is_script else "Install")
        self.install_btn.setFixedSize(104, 32)
        self.install_btn.setCursor(Qt.PointingHandCursor)
        self._style_button(palette)

        self.install_btn.clicked.connect(lambda: install_callback(self.app_data))

        self.remove_btn = None
        if not self.is_script:
            self.remove_btn = QPushButton("Remove")
            self.remove_btn.setFixedSize(78, 32)
            self.remove_btn.setCursor(Qt.PointingHandCursor)
            self.remove_btn.setVisible(False)
            self._style_remove_button(self.remove_btn)
            self.remove_btn.clicked.connect(lambda: remove_callback(self.app_data))

        self.preview_btn = None
        if self.is_script or self.is_vendor:
            self.preview_btn = QPushButton("Preview")
            self.preview_btn.setFixedSize(78, 32)
            self.preview_btn.setCursor(Qt.PointingHandCursor)
            self.preview_btn.setToolTip("Show planned commands without changing the system")
            self._style_secondary(self.preview_btn)
            self.preview_btn.clicked.connect(
                lambda: install_callback(self.app_data, True))

        layout.addLayout(text_layout, stretch=1)
        if self.preview_btn is not None:
            layout.addWidget(self.preview_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
        if self.remove_btn is not None:
            layout.addWidget(self.remove_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.install_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

    def _style_button(self, p):
        self.install_btn.setStyleSheet(
            "QPushButton {{ background-color: {accent}; color: #ffffff; border: none;"
            " border-radius: 6px; font-weight: 600; font-size: 12px; }}"
            "QPushButton:hover {{ background-color: {accent_hover}; }}"
            "QPushButton:disabled {{ background-color: {border}; color: {text_muted}; }}".format(**p)
        )

    def _style_secondary(self, button):
        p = self.palette
        button.setStyleSheet(
            "QPushButton {{ background-color: transparent; color: {text_muted};"
            " border: 1px solid {border}; border-radius: 6px;"
            " font-weight: 600; font-size: 12px; }}"
            "QPushButton:hover {{ color: {accent}; border: 1px solid {accent}; }}"
            "QPushButton:disabled {{ color: {border}; }}".format(**p)
        )

    def _style_remove_button(self, button):
        p = self.palette
        button.setStyleSheet(
            "QPushButton {{ background-color: transparent; color: {danger};"
            " border: 1px solid {danger}; border-radius: 6px;"
            " font-weight: 600; font-size: 12px; }}"
            "QPushButton:hover {{ background-color: {danger}; color: #ffffff; }}"
            "QPushButton:disabled {{ color: {text_muted}; border-color: {border}; }}"
            .format(**p)
        )

    # -- estado ---------------------------------------------------------
    def mark_installed(self, installed):
        if self.remove_btn is not None:
            self.remove_btn.setVisible(installed)
        if installed:
            self.status_label.setText("● Installed")
            self.install_btn.setText("Rerun" if self.is_script else "Reinstall")
        else:
            self.status_label.setText("")
            self.install_btn.setText("Run setup" if self.is_script else "Install")

    def set_busy(self, busy, active=False, label="Working..."):
        self.install_btn.setEnabled(not busy)
        if self.preview_btn is not None:
            self.preview_btn.setEnabled(not busy)
        if self.remove_btn is not None:
            self.remove_btn.setEnabled(not busy)

        if busy and active:
            self.status_label.setText(f"● {label}")
            self.status_label.setStyleSheet(
                "color: {}; font-size: 11px; font-weight: 600; background: transparent;".format(
                    self.palette["accent"]))
        elif busy:
            # Os outros cards ficam só desactivados; não mudam de estado.
            return
        else:
            self.status_label.setStyleSheet(
                "color: {}; font-size: 11px; font-weight: 600; background: transparent;".format(
                    self.palette["success"]))


# ----------------------------------------------------------------------
# Janela principal
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LinuxUtil Studio")
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "logo.svg",
        )
        self.logo_path = logo_path
        self.setWindowIcon(QIcon(logo_path))
        self.resize(1040, 740)

        self.catalogue = load_catalogue()
        self.installer = Installer()
        self.cards = {}
        self.installed_state = set()
        self.install_worker = None
        self.status_worker = None
        self.busy = False
        self.busy_label = "Working..."
        self.active_app_id = None

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

        logo_label = QLabel()
        logo_label.setPixmap(QIcon(self.logo_path).pixmap(44, 44))
        sidebar_layout.addWidget(logo_label)

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
        all_item = QListWidgetItem(f"All  ·  {len(self.catalogue)}")
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
        self.console.setVisible(False)  # aparece na primeira instalação
        self.cancel_install_btn = QPushButton("Cancel installation")
        self.cancel_install_btn.setVisible(False)
        self.cancel_install_btn.clicked.connect(self.cancel_installation)
        main_layout.addWidget(self.cancel_install_btn, alignment=Qt.AlignRight)
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
            if (not text or text in app["name"].lower() or text in app["description"].lower()
                or text in app["category"].lower())
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
            card = AppCard(
                app, self.handle_install, self.handle_remove, self.palette, self.theme_name,
                self.installer.sys_info.resolve_package_type(app),
            )
            # Preserva o estado conhecido ao filtrar ou trocar de tema.
            card.mark_installed(app["id"] in self.installed_state)
            card.set_busy(
                self.busy,
                active=app["id"] == self.active_app_id,
                label=self.busy_label,
            )
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
    def start_status_check(self, apps=None):
        self.status_worker = StatusWorker(apps or self.catalogue)
        self.status_worker.found.connect(self.on_status_found)
        self.status_worker.failed.connect(self.on_status_failed)
        self.status_worker.start()

    def on_status_found(self, app_id, installed):
        if installed:
            self.installed_state.add(app_id)
        else:
            self.installed_state.discard(app_id)
        card = self.cards.get(app_id)
        if card:
            card.mark_installed(installed)
            card.set_busy(
                self.busy,
                active=app_id == self.active_app_id,
                label=self.busy_label,
            )
        self._update_summary()

    def on_status_failed(self, app_id, message):
        self.console.setVisible(True)
        self.log(
            f"[!] Could not check installation state for {app_id}: {message}",
            self.palette["console_warn"],
        )

    # ------------------------------------------------------------------
    # Instalação
    # ------------------------------------------------------------------
    def log(self, text, color=None):
        color = color or self.palette["console_text"]
        self.console.append(f"<span style='color: {color};'>{html.escape(text)}</span>")
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum())

    def set_all_busy(self, busy, active_id=None, label="Working..."):
        self.busy = busy
        self.active_app_id = active_id if busy else None
        self.busy_label = label
        self.cancel_install_btn.setVisible(busy)
        self.cancel_install_btn.setEnabled(busy)
        self.cancel_install_btn.setText("Cancel installation")
        for app_id, card in self.cards.items():
            card.set_busy(busy, active=app_id == self.active_app_id, label=label)

    def cancel_installation(self):
        if self.install_worker and self.install_worker.isRunning():
            self.install_worker.cancel()
            self.cancel_install_btn.setEnabled(False)
            self.cancel_install_btn.setText("Cancelling...")
            self.log(
                "[!] Cancellation requested. Changes already completed will not be rolled back.",
                self.palette["console_warn"],
            )

    def handle_install(self, app_data, dry_run=False):
        if self.install_worker and self.install_worker.isRunning():
            self.log("[!] An installation is already running.", self.palette["console_warn"])
            return

        ptype = self.installer.sys_info.resolve_package_type(app_data)

        if not dry_run:
            if ptype == "script" and not self._confirm_script(app_data):
                return
            if ptype == "vendor" and not self._confirm_vendor(app_data):
                return

        self.console.clear()
        self.console.setVisible(True)
        self.set_all_busy(
            True,
            app_data["id"],
            "Previewing..." if dry_run else "Working...",
        )

        if dry_run:
            self.log(
                f"[i] Preview of {app_data['name']} (nothing will be installed)...",
                self.palette["console_cmd"],
            )
        elif ptype in {"script", "vendor"}:
            self.log(
                f"[*] Running {app_data['name']} setup...",
                self.palette["console_cmd"],
            )
        else:
            self.log(
                f"[*] Installing {app_data['name']} ({ptype})...",
                self.palette["console_cmd"],
            )

        self.install_worker = InstallWorker(app_data, dry_run=dry_run)
        self.install_worker.line.connect(lambda line: self.log(line))
        self.install_worker.done.connect(
            lambda result: self.on_install_done(app_data, result))
        self.install_worker.start()

    def handle_remove(self, app_data):
        if self.install_worker and self.install_worker.isRunning():
            return

        answer = QMessageBox.question(
            self,
            "Remove application?",
            "<b>{}</b> will be removed using <b>{}</b>.<br><br>"
            "The app will not request deletion of user data or automatically "
            "remove unused dependencies. Continue?".format(
                html.escape(app_data["name"]),
                html.escape(
                    self.installer.sys_info.resolve_package_type(app_data).upper()
                ),
            ),
            QMessageBox.Cancel | QMessageBox.Ok,
            QMessageBox.Cancel,
        )
        if answer != QMessageBox.Ok:
            return

        self.console.clear()
        self.console.setVisible(True)
        self.set_all_busy(True, app_data["id"], "Removing...")
        self.log(
            f"[*] Removing {app_data['name']}...",
            self.palette["console_warn"],
        )
        self.install_worker = InstallWorker(app_data, operation="remove")
        self.install_worker.line.connect(lambda line: self.log(line))
        self.install_worker.done.connect(
            lambda result: self.on_remove_done(app_data, result)
        )
        self.install_worker.start()

    def on_remove_done(self, app_data, result):
        self.set_all_busy(False)
        card = self.cards.get(app_data["id"])
        if result["status"] == "success":
            self.installed_state.discard(app_data["id"])
            self._update_summary()
            self.log(
                f"[+] Removed: {app_data['name']}. User data was not explicitly deleted.",
                self.palette["console_ok"],
            )
            if card:
                card.mark_installed(False)
        elif result["status"] == "cancelled":
            self.log(f"[!] {result['message']}", self.palette["console_warn"])
            self.start_status_check([app_data])
        else:
            self.log(f"[-] Error: {result['message']}", self.palette["console_err"])
            self.start_status_check([app_data])
        if card and result["status"] != "success":
            card.mark_installed(app_data["id"] in self.installed_state)

    def _confirm_script(self, app_data):
        """Pede confirmação antes de correr um script que mexe no sistema."""
        script = self.installer.sys_info.resolve_script(app_data)
        if not script:
            family = self.installer.sys_info.family or "your distro"
            self.log(f"[-] No setup script available for {family}.",
                     self.palette["console_err"])
            return False

        manager = self.installer.sys_info.package_manager or "the system package manager"
        answer = QMessageBox.question(
            self,
            "Run setup script?",
            "<b>{}</b> will install packages with <b>{}</b> and Flatpak, and will "
            "ask for your password.<br><br>Script: <code>{}</code><br><br>"
            "Use <b>Preview</b> to see every command first.<br>Continue?".format(
                html.escape(app_data["name"]), manager, os.path.basename(script)),
            QMessageBox.Cancel | QMessageBox.Ok,
            QMessageBox.Cancel,
        )
        return answer == QMessageBox.Ok

    def _confirm_vendor(self, app_data):
        manager = self.installer.sys_info.package_manager or "the system package manager"
        family = self.installer.sys_info.family or "your distribution"
        vendor = "Microsoft" if app_data["id"] == "vscode" else "Brave Software"
        answer = QMessageBox.question(
            self,
            "Add vendor repository?",
            "<b>{}</b> will add the official {} package repository for <b>{}</b>, "
            "verify its signing key, and install with <b>{}</b>.<br><br>"
            "Remove will uninstall the package and remove only repository/key "
            "files created by LinuxUtil Studio. Existing repository files are "
            "left untouched.<br><br>Use <b>Preview</b> to inspect the planned "
            "steps first. Continue?".format(
                html.escape(app_data["name"]),
                html.escape(vendor),
                html.escape(family),
                html.escape(manager),
            ),
            QMessageBox.Cancel | QMessageBox.Ok,
            QMessageBox.Cancel,
        )
        return answer == QMessageBox.Ok

    def on_install_done(self, app_data, result):
        self.set_all_busy(False)
        card = self.cards.get(app_data["id"])

        if result["status"] == "cancelled":
            self.log(f"[!] {result['message']}", self.palette["console_warn"])
            self.start_status_check([app_data])
            if card:
                card.mark_installed(app_data["id"] in self.installed_state)
            return

        if result["status"] == "success" and result.get("dry_run"):
            self.log(
                f"[i] {app_data['name']}: preview finished, nothing was changed.",
                self.palette["console_ok"],
            )
            if card:
                card.mark_installed(app_data["id"] in self.installed_state)
            return

        if result["status"] == "success":
            self.installed_state.add(app_data["id"])
            self._update_summary()
            self.log(f"[+] Done: {app_data['name']} installed.", self.palette["console_ok"])
            if card:
                card.mark_installed(True)
        else:
            self.log(f"[-] Error: {result['message']}", self.palette["console_err"])
            self.start_status_check([app_data])
            if card:
                card.mark_installed(app_data["id"] in self.installed_state)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
