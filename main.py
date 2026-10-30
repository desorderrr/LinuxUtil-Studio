import sys
import argparse

# Importar componentes da UI se estivermos no modo GUI
try:
    from ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

from core.system_info import SystemInfo
from core.installer import Installer
from core.catalogue_loader import load_catalogue

def run_cli_test():
    print("--- LinuxUtil Studio (CLI Test Mode) ---")
    sys_info = SystemInfo()
    print(f"Detected System: {sys_info.distro}")
    print(f"Package Manager: {sys_info.package_manager}")
    print("-" * 30)

    catalogue = load_catalogue()
    
    print("Available Apps:")
    for app in catalogue:
        ptype = app.get('package_type', 'apt')
        print(f"[{app['id']}] {app['name']} - {app['description']} ({app['category']}) [{ptype}]")
    
    print("-" * 30)
    choice = input("Enter an App ID to install (or 'q' to quit): ")
    
    if choice.lower() == 'q':
        sys.exit()

    target_app = next((app for app in catalogue if app['id'] == choice), None)
    
    if target_app:
        print(f"Starting installation of {target_app['name']}...")
        installer = Installer()
        result = installer.run_install(target_app['package_name'], target_app.get('package_type'))
        print(f"Result: {result['status']}")
        if result['status'] == 'success':
            print("Successfully installed!")
        else:
            print(f"Error: {result['message']}")
    else:
        print("Invalid selection.")

def main():
    parser = argparse.ArgumentParser(description="LinuxUtil Studio")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode for debugging")
    args = parser.parse_args()

    if args.cli or not GUI_AVAILABLE:
        run_cli_test()
    else:
        # Modo GUI
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
