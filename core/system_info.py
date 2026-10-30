import os
import platform
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

# Famílias usadas no catálogo para escolher o nome do pacote certo.
FAMILY_BY_MANAGER = {
    "apt": "debian",
    "dnf": "fedora",
    "pacman": "arch",
    "zypper": "suse",
}


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
            if os.path.exists("/etc/debian_version"):
                return "debian"
            if os.path.exists("/etc/fedora-release"):
                return "fedora"
            if os.path.exists("/etc/arch-release"):
                return "arch"
            return "unknown"

    def _get_package_manager(self):
        dist = self.distro or ""
        if dist in ["debian", "ubuntu", "linuxmint", "pop", "pop_os", "elementary", "zorin", "kali"]:
            return "apt"
        elif dist in ["fedora", "rhel", "centos", "rocky", "almalinux", "nobara"]:
            return "dnf"
        elif dist in ["arch", "manjaro", "endeavouros", "cachyos", "garuda", "artix"]:
            return "pacman"
        elif dist in ["opensuse", "suse", "opensuse-leap", "opensuse-tumbleweed"]:
            return "zypper"
        return None

    # ------------------------------------------------------------------
    # Família / nomes de pacote
    # ------------------------------------------------------------------
    @property
    def family(self):
        """``debian``, ``fedora``, ``arch``, ``suse`` ou ``None``."""
        return FAMILY_BY_MANAGER.get(self.package_manager)

    def resolve_package(self, app):
        """Nome do pacote certo para esta distro.

        O catálogo pode trazer ``"packages": {"arch": "libreoffice-fresh"}``
        para os casos em que o nome muda entre distros.
        """
        packages = app.get("packages") or {}
        family = self.family
        if family and packages.get(family):
            return packages[family]
        return app.get("package_name")

    def resolve_script(self, app):
        """Caminho do script de uma entrada ``package_type: script``."""
        scripts = app.get("scripts") or {}
        family = self.family
        name = scripts.get(family) if family else None
        if not name:
            return None
        path = os.path.join(SCRIPTS_DIR, name)
        return path if os.path.exists(path) else None

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------
    def get_install_commands(self, app, dry_run=False):
        """Lista de comandos (argv) a executar em sequência.

        ``dry_run`` só é suportado pelas entradas do tipo script: corre o script
        em modo de simulação, sem privilégios e sem alterar o sistema.
        """
        package_type = app.get("package_type", "native")

        if package_type == "script":
            path = self.resolve_script(app)
            if not path:
                return []
            if dry_run:
                return [["bash", path, "--dry-run"]]
            return [[self.privilege_tool, "bash", path]]

        if package_type == "flatpak":
            # O flatpak pede autorização sozinho (polkit) para instalações de sistema.
            if not self.has_flatpak:
                return []
            return [["flatpak", "install", "-y", "flathub", app["package_name"]]]

        if package_type == "snap":
            if not self.has_snap:
                return []
            return [[self.privilege_tool, "snap", "install", app["package_name"]]]

        package_name = self.resolve_package(app)
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

    def get_install_command(self, app, dry_run=False):
        """Compatibilidade: retorna os comandos como string legível."""
        commands = self.get_install_commands(app, dry_run=dry_run)
        if not commands:
            return None
        return " && ".join(" ".join(cmd) for cmd in commands)

    def get_check_command(self, app):
        """Comando usado para saber se o pacote já está instalado."""
        package_type = app.get("package_type", "native")
        if package_type == "flatpak":
            return ["flatpak", "info", app["package_name"]]
        if package_type == "snap":
            return ["snap", "list", app["package_name"]]

        package_name = self.resolve_package(app)
        if not package_name:
            return None
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
            f"<SystemInfo: {self.distro} ({self.package_manager}/{self.family}) | "
            f"Flatpak: {self.has_flatpak} | Snap: {self.has_snap}>"
        )
