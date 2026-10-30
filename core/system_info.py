import os
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
        self._privilege_tool = None

    # ------------------------------------------------------------------
    # Escalada de privilégios
    # ------------------------------------------------------------------
    @property
    def privilege_tool(self):
        """Comando a usar para correr algo como root.

        ``sudo`` só serve se estiver configurado sem password ou se houver um
        terminal onde pedir a password. Uma app GUI lançada pelo menu não tem
        terminal, por isso nesse caso usa-se ``pkexec`` (diálogo do polkit).
        """
        if self._privilege_tool is not None:
            return self._privilege_tool

        self._privilege_tool = "sudo"
        if shutil.which("sudo") is None:
            self._privilege_tool = "pkexec" if shutil.which("pkexec") else "sudo"
            return self._privilege_tool

        # sudo sem password (sudoers/NOPASSWD)? então é o caminho mais simples.
        try:
            if subprocess.run(
                ["sudo", "-n", "true"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).returncode == 0:
                return self._privilege_tool
        except Exception:
            pass

        graphical = bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
        if graphical and shutil.which("pkexec"):
            self._privilege_tool = "pkexec"
        return self._privilege_tool

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
            # O flatpak pede autorização sozinho (polkit) para instalações de sistema.
            return [["flatpak", "install", "-y", "flathub", package_name]] if self.has_flatpak else []
        if package_type == "snap":
            if not self.has_snap:
                return []
            return [[self.privilege_tool, "snap", "install", package_name]]

        pm = self.package_manager
        priv = self.privilege_tool
        if pm == "apt":
            return [
                [priv, "apt-get", "update"],
                [priv, "apt-get", "install", "-y", package_name],
            ]
        if pm == "dnf":
            return [[priv, "dnf", "install", "-y", package_name]]
        if pm == "pacman":
            return [[priv, "pacman", "-S", "--noconfirm", package_name]]
        if pm == "zypper":
            return [[priv, "zypper", "install", "-y", package_name]]
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
