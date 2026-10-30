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
            if os.path.exists("/etc/debian_version"):
                return "debian"
            if os.path.exists("/etc/fedora-release"):
                return "fedora"
            if os.path.exists("/etc/arch-release"):
                return "arch"
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
        return None

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def get_install_commands(self, package_name, package_type=None):
        """Retorna uma lista de comandos (argv) a executar em sequência."""
        if package_type == "flatpak":
            return [["flatpak", "install", "-y", "flathub", package_name]] if self.has_flatpak else []
        if package_type == "snap":
            return [["sudo", "snap", "install", package_name]] if self.has_snap else []

        pm = self.package_manager
        if pm == "apt":
            return [
                ["sudo", "apt-get", "update"],
                ["sudo", "apt-get", "install", "-y", package_name],
            ]
        if pm == "dnf":
            return [["sudo", "dnf", "install", "-y", package_name]]
        if pm == "pacman":
            return [["sudo", "pacman", "-S", "--noconfirm", package_name]]
        if pm == "zypper":
            return [["sudo", "zypper", "install", "-y", package_name]]
        return []

    def get_install_command(self, package_name, package_type=None):
        """Compatibilidade: retorna o primeiro comando como string legível."""
        commands = self.get_install_commands(package_name, package_type)
        if not commands:
            return None
        return " && ".join(" ".join(cmd) for cmd in commands)

    def get_check_command(self, package_name, package_type=None):
        """Comando usado para saber se o pacote já está instalado (saída vazia = não instalado)."""
        if package_type == "flatpak":
            return ["flatpak", "info", package_name]
        if package_type == "snap":
            return ["snap", "list", package_name]

        pm = self.package_manager
        if pm == "apt":
            return ["dpkg", "-s", package_name]
        if pm in ("dnf", "zypper"):
            return ["rpm", "-q", package_name]
        if pm == "pacman":
            return ["pacman", "-Q", package_name]
        return None

    def __repr__(self):
        return (
            f"<SystemInfo: {self.distro} ({self.package_manager}) | "
            f"Flatpak: {self.has_flatpak} | Snap: {self.has_snap}>"
        )
