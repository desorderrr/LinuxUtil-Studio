import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QListWidget, QLabel, QPushButton, 
                                QTextEdit, QLineEdit, QFrame, QScrollArea)
from PySide6.QtCore import Qt
from core.catalogue_loader import load_catalogue

class AppCard(QFrame):
    """Widget para representar um aplicativo individual."""
    def __init__(self, app_data, install_callback):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel)
        self.setMinimumHeight(110)
        self.setStyleSheet("QFrame { border: 1px solid #ddd; border-radius: 8px; padding: 10px; }")
        
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        
        # Container para Texto
        text_layout = QVBoxLayout()
        
        name_row = QHBoxLayout()
        self.name_label = QLabel(app_data['name'])
        self.name_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #222;")
        
        ptype = app_data.get('package_type', 'apt')
        self.badge = QLabel(ptype.upper())
        self.badge.setStyleSheet(f"""
            background-color: {'#0A84FF' if ptype == 'apt' else '#28a745' if ptype == 'flatpak' else '#ff9800'};
            color: white; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;
        """)
        
        name_row.addWidget(self.name_label)
        name_row.addWidget(self.badge)
        name_row.addStretch()
        
        self.desc_label = QLabel(app_data['description'])
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #555; font-size: 12px;")
        
        text_layout.addLayout(name_row)
        text_layout.addWidget(self.desc_label)
        
        # Botão de Ação
        self.install_btn = QPushButton("Install")
        self.install_btn.setFixedSize(80, 32)
        self.install_btn.setStyleSheet("""
            QPushButton { background-color: #0A84FF; color: white; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #007aff; }
        """)
        self.install_btn.clicked.connect(lambda: install_callback(app_data))
        
        layout.addLayout(text_layout)
        layout.addWidget(self.install_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LinuxUtil Studio")
        self.resize(1000, 700)
        
        self.catalogue = load_catalogue()
        
        # Widget Principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Área Superior (Sidebar + Content)
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
        self.search_bar.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 10px;")
        self.search_bar.textChanged.connect(self.filter_apps)
        sidebar_layout.addWidget(self.search_bar)
        
        self.category_list = QListWidget()
        self.category_list.setStyleSheet("border: none; font-size: 13px; background: transparent;")
        categories = ["All"] + sorted(list(set(app['category'] for app in self.catalogue)))
        self.category_list.addItems(categories)
        self.category_list.currentTextChanged.connect(self.filter_apps)
        sidebar_layout.addWidget(self.category_list)
        
        # Área de Conteúdo com Scroll
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background-color: white;")
        
        self.container_widget = QWidget()
        self.app_container = QVBoxLayout(self.container_widget)
        self.app_container.addStretch()
        
        self.scroll_area.setWidget(self.container_widget)
        content_layout.addWidget(self.scroll_area)
        
        top_layout.addWidget(sidebar)
        top_layout.addWidget(content_area)
        
        main_layout.addWidget(top_container)

        # Console de Saída (Rodapé)
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(150)
        self.console.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-family: 'Courier New'; padding: 10px; font-size: 12px;")
        main_layout.addWidget(self.console)

        self.populate_apps()

    def populate_apps(self, apps=None):
        # Limpar container
        while self.app_container.count() > 1:
            child = self.app_container.takeAt(1)
            if child.widget():
                child.widget().deleteLater()

        if apps is None:
            apps = self.catalogue

        for app in apps:
            card = AppCard(app, self.handle_install)
            self.app_container.insertWidget(0, card)

    def filter_apps(self):
        search_text = self.search_bar.text().lower()
        category = self.category_list.currentText()
        
        filtered = []
        for app in self.catalogue:
            match_search = search_text in app['name'].lower() or search_text in app['description'].lower()
            match_category = (category == "All") or (app['category'] == category)
            if match_search and match_category:
                filtered.append(app)
                
        self.populate_apps(filtered)

    def handle_install(self, app_data):
        pkg = app_data['package_name']
        ptype = app_data.get('package_type', 'apt')
        
        self.console.append(f"<span style='color: #569cd6;'>[*] Starting installation of {app_data['name']} ({ptype})...</span>")
        
        from core.installer import Installer
        installer = Installer()
        result = installer.run_install(pkg, ptype)
        
        if result['status'] == 'success':
            self.console.append(f"<span style='color: #4ec9b0;'>[+] Success: {app_data['name']} installed successfully!</span>")
        else:
            self.console.append(f"<span style='color: #f44747;'>[-] Error: {result['message']}</span>")

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
