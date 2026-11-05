import sys
import os
import argparse
import subprocess

# Componentes da UI (opcionais: o app funciona em modo CLI sem PySide6)
try:
    from ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

from core.system_info import SystemInfo
from core.installer import Installer
from core.catalogue_loader import load_catalogue


def print_system_info():
    info = SystemInfo()
    print("--- LinuxUtil Studio: system info ---")
    print(f"Distro         : {info.distro}")
    print(f"Package manager: {info.package_manager}")
    print(f"Family         : {info.family}")
    print(f"Flatpak        : {'yes' if info.has_flatpak else 'no'}")
    print(f"Snap           : {'yes' if info.has_snap else 'no'}")
    if info.family == "arch":
        print(f"AUR helpers    : {', '.join(info.aur_helpers) if info.aur_helpers else 'none (yay/paru not detected)'}")
    print(f"Privilege tool : {info.privilege_tool}")
    print(f"GUI available  : {'yes' if GUI_AVAILABLE else 'no (install PySide6)'}")


def list_apps():
    catalogue = load_catalogue()
    installer = Installer()
    info = installer.sys_info
    print(f"{'ID':<14} {'TYPE':<9} {'TARGET':<34} {'STATUS':<10} NAME")
    print("-" * 100)
    for app in catalogue:
        ptype = info.resolve_package_type(app)
        if ptype is None:
            target = "-"
        elif ptype == "script":
            target = os.path.basename(info.resolve_script(app) or "-")
        elif ptype == "flatpak":
            target = info.resolve_package_name(app)
        elif ptype == "snap":
            target = info.resolve_package_name(app)
        else:
            target = info.resolve_package_name(app) or "-"
        try:
            installed = installer.is_installed(app)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(
                f"Warning: could not check installation state for {app['id']}: {error}",
                file=sys.stderr,
            )
            status = "unknown"
        else:
            status = "installed" if installed else "-"
        print(f"{app['id']:<14} {ptype:<9} {target:<34} {status:<10} {app['name']} ({app['category']})")
    return catalogue


def install(app_id, dry_run=False):
    catalogue = load_catalogue()
    target = next((a for a in catalogue if a["id"] == app_id), None)
    if not target:
        print(f"App '{app_id}' not found in the catalogue.")
        return 1

    installer = Installer()
    ptype = installer.sys_info.resolve_package_type(target)
    if ptype == "vendor" and not dry_run:
        print(
            f"Installing {target['name']} from its official vendor repository "
            "(asks for your password)...\n"
        )
    elif ptype == "script" and not dry_run:
        print(f"Running setup script for {target['name']} (asks for your password)...\n")
    elif dry_run:
        print(f"Preview for {target['name']} (nothing will be installed)...\n")
    else:
        print(f"Installing {target['name']} ({ptype})...\n")

    result = installer.run_install(
        target,
        on_output=lambda line: print(line, flush=True),
        dry_run=dry_run,
    )
    print(f"\nResult: {result['status']} - {result['message']}")
    return 0 if result["status"] == "success" else 1


def remove(app_id):
    catalogue = load_catalogue()
    target = next((a for a in catalogue if a["id"] == app_id), None)
    if not target:
        print(f"App '{app_id}' not found in the catalogue.")
        return 1

    installer = Installer()
    if target.get("package_type") == "script":
        print("Setup scripts and gaming packs cannot be removed automatically.")
        return 1
    if not installer.is_installed(target):
        print(f"{target['name']} is not detected as installed.")
        return 1

    print(f"Removing {target['name']}...\n")
    result = installer.run_remove(
        target,
        on_output=lambda line: print(line, flush=True),
    )
    print(f"\nResult: {result['status']} - {result['message']}")
    return 0 if result["status"] == "success" else 1


def run_cli(dry_run=False):
    info = SystemInfo()
    installer = Installer()
    print("--- LinuxUtil Studio (CLI) ---")
    print(f"Detected: {info.distro} | Manager: {info.package_manager}")
    print("-" * 30)

    catalogue = list_apps()

    print("-" * 30)
    try:
        choice = input("App ID to install (or 'q' to quit): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0

    if choice.lower() in ("q", ""):
        return 0

    target = next((a for a in catalogue if a["id"] == choice), None)
    if not target:
        print("Invalid selection.")
        return 1

    result = installer.run_install(
        target,
        on_output=lambda line: print(line, flush=True),
        dry_run=dry_run,
    )
    print(f"Result: {result['status']} - {result['message']}")
    return 0 if result["status"] == "success" else 1


def main():
    parser = argparse.ArgumentParser(description="LinuxUtil Studio - the Linux setup app, rebuilt.")
    parser.add_argument("--cli", action="store_true", help="run in interactive CLI mode")
    parser.add_argument("--list", action="store_true", help="list catalogue apps and exit")
    parser.add_argument("--info", action="store_true", help="show detected system info and exit")
    parser.add_argument("--install", metavar="ID", help="install an app by catalogue ID and exit")
    parser.add_argument("--remove", metavar="ID", help="remove an app by catalogue ID and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --install/--cli: preview setup scripts without changing anything")
    parser.add_argument("--updates", action="store_true",
                        help="list available system package updates and exit")
    args = parser.parse_args()

    if args.info:
        print_system_info()
        return 0
    if args.list:
        list_apps()
        return 0
    if args.updates:
        info = SystemInfo()
        print(f"--- Available updates ({info.package_manager}) ---")
        ups = info.available_updates()
        if not ups:
            print("No updates available (or could not query).")
            return 0
        for u in ups:
            print(u)
        print(f"\n{len(ups)} package(s) can be updated.")
        return 0
    if args.install:
        return install(args.install, dry_run=args.dry_run)
    if args.remove:
        return remove(args.remove)
    if args.cli or not GUI_AVAILABLE:
        if not GUI_AVAILABLE and not args.cli:
            print("PySide6 not found - falling back to CLI mode.\n")
        return run_cli(dry_run=args.dry_run)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
