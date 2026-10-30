import platform
import subprocess
import shutil

class SystemInfo:
    def __init__(self):
        self.os_name = platform.system().lower()
        self.distro = self._get_distro()
        self.package_manager = self._get_package_manager()
        self.has_flatpak = shutil.which("flatpak") is not None
        self.has_snap = shutil.which("snap") is not None

    def _get_distro(self):
        try:
            import distro
            return distro.id()
        except ImportError:
            import os
            if os.path.exists("/etc/debian_version"): return "debian"
            if os.path.exists("/etc/fedora-release"): return "fedora"
            if os.path.exists("/etc/arch-release"): return "arch"
            return "unknown"

    def _get_package_manager(self):
        dist = self.distro
        if dist in ["debian", "ubuntu", "linuxmint", "pop"]:
            return "apt"
        elif dist in ["fedora", "rhel", "centos"]:
            return "dnf"
        elif dist in ["arch", "manjaro", "endeavouros"]:
            return "pacman"
        elif dist in ["opensuse", "suse"]:
            return "zypper"
        else:
            return None

    def get_install_command(self, package_name, package_type=None):
        if package_type == "flatpak" and self.has_flatpak:
            return f"flatpak install -y flathub {package_name}"
        if package_type == "snap" and self.has_snap:
            return f"sudo snap install {package_name}"

        pm = self.package_manager
        if pm == "apt":
            return f"sudo apt update && sudo apt install -y {package_name}"
        elif pm == "dnf":
            return f"sudo dnf install -y {package_name}"
        elif pm == "pacman":
            return f"sudo pacman -S --noconfirm {package_name}"
        elif pm == "zypper":
            return f"sudo zypper install -y {package_name}"
        return None

    def __repr__(self):
        return f"<SystemInfo: {self.distro} ({self.package_manager}) | Flatpak: {self.has_flatpak} | Snap: {self.has_snap}>"
