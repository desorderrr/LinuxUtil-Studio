import os
import platform
import shlex
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

VENDOR_APP_FAMILIES = {
    "vscode": {"debian", "fedora", "suse"},
    "brave": {"debian", "fedora", "suse"},
}


class SystemInfo:
    def __init__(self):
        self.os_name = platform.system().lower()
        self.is_flatpak = os.path.exists("/.flatpak-info")
        self.has_flatpak_spawn = shutil.which("flatpak-spawn") is not None
        self.distro_like = []
        self.distro = self._get_distro()
        self.package_manager = self._get_package_manager()
        # Dentro do sandbox o binário `flatpak` pode não existir; o próprio app
        # já é Flatpak, por isso assumimos que o host tem Flatpak.
        self.has_flatpak = self.is_flatpak or shutil.which("flatpak") is not None
        self.has_snap = self._host_has("snap")
        self._privilege_tool = None
        self.aur_helpers = self._detect_aur_helpers()

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

        # Dentro do Flatpak não há sudo/pkexec locais: perguntamos ao host.
        if self.is_flatpak:
            self._privilege_tool = "pkexec" if self._host_has("pkexec") else "sudo"
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

    def host_wrap(self, cmd):
        """Executa no host quando a app corre dentro do sandbox Flatpak.

        Sem isto, ``dnf``/``apt``/``pacman`` e o ``pkexec`` não existem (ou não
        têm permissões) dentro do sandbox. ``flatpak-spawn --host`` delega no
        sistema real; o manifesto pede ``--talk-name=org.freedesktop.Flatpak``.
        """
        if self.is_flatpak and self.has_flatpak_spawn:
            # --directory=/ evita herdar o cwd /app/... que não existe no host.
            return ["flatpak-spawn", "--host", "--directory=/"] + list(cmd)
        return list(cmd)

    def _host_run(self, cmd, timeout=10):
        """Corre um comando no host (ou localmente fora do Flatpak)."""
        if self.is_flatpak and self.has_flatpak_spawn:
            cmd = ["flatpak-spawn", "--host", "--directory=/"] + list(cmd)
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )

    def _host_has(self, binary):
        try:
            return self._host_run(["sh", "-c", f"command -v {binary}"]).returncode == 0
        except Exception:
            return False

    def _detect_aur_helpers(self):
        """Detecta helpers AUR (yay/paru) no Arch, sem os instalar.

        Devolve a lista de helpers disponíveis, por ordem de preferência.
        Fora do Arch (ou sem nenhum) devolve lista vazia.
        """
        if self.family != "arch":
            return []
        found = []
        for helper in ("yay", "paru", "trizen", "pikaur"):
            if self._host_has(helper):
                found.append(helper)
        return found

    def _get_distro(self):
        os_release = {}
        if self.is_flatpak:
            try:
                os_release = self._parse_os_release(
                    self._host_run(["cat", "/etc/os-release"]).stdout
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            try:
                with open("/etc/os-release", encoding="utf-8") as handle:
                    os_release = self._parse_os_release(handle.read())
            except (OSError, UnicodeError):
                pass

        if os_release.get("ID"):
            self.distro_like = os_release.get("ID_LIKE", "").split()
            return os_release["ID"].lower()

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

    @staticmethod
    def _parse_os_release(contents):
        values = {}
        for line in contents.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            try:
                parts = shlex.split(value, comments=False)
            except ValueError:
                continue
            if parts:
                values[key] = parts[0]
        return values

    def _get_package_manager(self):
        dist = self.distro or ""
        manager_by_distro = {
            "debian": "apt",
            "ubuntu": "apt",
            "linuxmint": "apt",
            "pop": "apt",
            "pop_os": "apt",
            "elementary": "apt",
            "zorin": "apt",
            "kali": "apt",
            "fedora": "dnf",
            "rhel": "dnf",
            "centos": "dnf",
            "rocky": "dnf",
            "almalinux": "dnf",
            "nobara": "dnf",
            "arch": "pacman",
            "manjaro": "pacman",
            "endeavouros": "pacman",
            "cachyos": "pacman",
            "garuda": "pacman",
            "artix": "pacman",
            "opensuse": "zypper",
            "opensuse-leap": "zypper",
            "opensuse-tumbleweed": "zypper",
            "suse": "zypper",
        }
        for candidate in (dist, *self.distro_like):
            manager = manager_by_distro.get(candidate.lower())
            if manager:
                return manager

        # Fallback: dentro do Flatpak a distro pode não ser detetável,
        # por isso perguntamos ao host qual o gestor disponível.
        if self.is_flatpak:
            for manager, binary in (
                ("apt", "apt-get"), ("dnf", "dnf"),
                ("pacman", "pacman"), ("zypper", "zypper"),
            ):
                if self._host_has(binary):
                    return manager
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

    def resolve_package_type(self, app):
        package_type = app.get("package_type", "native")
        if package_type != "vendor":
            return package_type
        if (
            self.family == "arch"
            and getattr(self, "aur_helpers", [])
            and app.get("aur_package")
        ):
            return "aur"
        machine = platform.machine().lower()
        supported_arches = {"x86_64", "amd64", "aarch64", "arm64"}
        if (
            not self.is_flatpak
            and self.family in VENDOR_APP_FAMILIES.get(app["id"], set())
            and machine in supported_arches
        ):
            return "vendor"
        return app.get("fallback_type")

    def resolve_package_name(self, app):
        if self.resolve_package_type(app) == "aur":
            return app["aur_package"]
        if (
            app.get("package_type") == "vendor"
            and self.resolve_package_type(app) == app.get("fallback_type")
        ):
            return app.get("fallback_package_name")
        if app.get("package_type") in {"flatpak", "snap"}:
            return app.get("package_name")
        return self.resolve_package(app)

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

        ``dry_run`` corre scripts e instaladores vendor em modo de simulação,
        sem privilégios ou alterações; para pacotes mostra os comandos.
        """
        package_type = self.resolve_package_type(app)
        if package_type is None:
            return []

        if package_type == "script":
            path = self.resolve_script(app)
            if not path:
                return []
            if dry_run:
                return [["bash", path, "--dry-run"]]
            return [[self.privilege_tool, "bash", path]]

        if package_type == "vendor":
            path = os.path.join(SCRIPTS_DIR, "vendor_apps.sh")
            if not os.path.isfile(path):
                return []
            if dry_run:
                return [["bash", path, app["id"], "install", "--dry-run"]]
            return [[self.privilege_tool, "bash", path, app["id"], "install"]]

        if package_type == "flatpak":
            # O flatpak pede autorização sozinho (polkit) para instalações de sistema.
            if not self.has_flatpak:
                return []
            return [[
                "flatpak", "install", "-y", "flathub",
                self.resolve_package_name(app),
            ]]

        if package_type == "snap":
            if not self.has_snap:
                return []
            return [[self.privilege_tool, "snap", "install", app["package_name"]]]

        package_name = self.resolve_package_name(app)
        pm = self.package_manager
        if pm == "pacman" and getattr(self, "aur_helpers", []):
            return [[
                self.aur_helpers[0], "-S", "--needed", "--noconfirm", package_name,
            ]]
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

    def get_remove_commands(self, app):
        """Lista comandos para remover apenas a aplicação, sem dependências órfãs."""
        package_type = self.resolve_package_type(app)
        if package_type in {None, "script"}:
            return []
        if package_type == "vendor":
            path = os.path.join(SCRIPTS_DIR, "vendor_apps.sh")
            if not os.path.isfile(path):
                return []
            return [[self.privilege_tool, "bash", path, app["id"], "remove"]]
        if package_type == "flatpak":
            if not self.has_flatpak:
                return []
            return [[
                "flatpak", "uninstall", "--noninteractive", "-y",
                self.resolve_package_name(app),
            ]]
        if package_type == "snap":
            if not self.has_snap:
                return []
            return [[self.privilege_tool, "snap", "remove", app["package_name"]]]

        package_name = self.resolve_package_name(app)
        if not package_name:
            return []
        pm = self.package_manager
        priv = self.privilege_tool
        if pm == "apt":
            return [[priv, "apt-get", "remove", "-y", package_name]]
        if pm == "dnf":
            return [[priv, "dnf", "remove", "--no-autoremove", "-y", package_name]]
        if pm == "pacman":
            return [[priv, "pacman", "-R", "--noconfirm", package_name]]
        if pm == "zypper":
            return [[priv, "zypper", "remove", "-y", package_name]]
        return []

    def get_install_command(self, app, dry_run=False):
        """Compatibilidade: retorna os comandos como string legível."""
        commands = self.get_install_commands(app, dry_run=dry_run)
        if not commands:
            return None
        return " && ".join(" ".join(cmd) for cmd in commands)

    def get_check_command(self, app):
        """Comando usado para saber se o pacote já está instalado."""
        package_type = self.resolve_package_type(app)
        if package_type is None:
            return None
        if package_type == "flatpak":
            return ["flatpak", "info", self.resolve_package_name(app)]
        if package_type == "snap":
            return ["snap", "list", app["package_name"]]

        package_name = self.resolve_package_name(app)
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

    def available_updates(self, timeout=60):
        """Lista (apenas consulta, sem instalar) os pacotes com atualização.

        Devolve uma lista de nomes de pacote. Erros de consulta são lançados
        para que CLI e GUI os distingam de uma lista vazia. Nunca atualiza.
        """
        pm = self.package_manager
        cmd = None
        if pm == "apt":
            cmd = ["apt", "list", "--upgradable"]
        elif pm == "dnf":
            cmd = ["dnf", "check-update", "-q"]
        elif pm == "pacman":
            cmd = ["pacman", "-Qu"]
        elif pm == "zypper":
            cmd = ["zypper", "list-updates"]
        if not cmd:
            raise RuntimeError(
                f"Update checking is not supported for package manager {pm or 'unknown'}."
            )

        result = self._host_run(cmd, timeout=timeout) if self.is_flatpak else subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0 and not (pm == "dnf" and result.returncode == 100):
            details = (result.stderr or result.stdout or "").strip()
            message = f"{pm} update check failed (exit {result.returncode})"
            raise RuntimeError(f"{message}: {details}" if details else message)

        ARCH_SUFFIXES = (".x86_64", ".i686", ".noarch", ".aarch64", ".armv7hl")
        names = []
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if not line or line.startswith("Listing...") or line.startswith("Last metadata"):
                continue
            if line.lower() in ("upgrades", "packages", "repository"):
                continue
            # apt: "pkg/version arch [upgradable from: ...]"
            if pm == "apt" and "/" in line:
                names.append(line.split("/", 1)[0].strip())
                continue
            # pacman: "pkg oldver -> newver"
            if pm == "pacman" and " -> " in line:
                names.append(line.split()[0].strip())
                continue
            # zypper: status | repository | name | current | available | arch
            if pm == "zypper":
                if "|" not in line:
                    continue
                columns = [column.strip() for column in line.split("|")]
                if len(columns) < 6:
                    continue
                name = columns[2]
                if not name or name.lower() == "name" or set(name) <= {"-", "+"}:
                    continue
                names.append(name)
                continue
            parts = line.split()
            if len(parts) >= 1:
                token = parts[0]
                if token.lower() in ("upgrades", "packages", "repository", "last"):
                    continue
                for suf in ARCH_SUFFIXES:
                    if token.endswith(suf):
                        token = token[: -len(suf)]
                names.append(token)
        # dedup preserving order
        seen = set()
        out = []
        for n in names:
            if n and n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def __repr__(self):
        return (
            f"<SystemInfo: {self.distro} ({self.package_manager}/{self.family}) | "
            f"Flatpak: {self.has_flatpak} | Snap: {self.has_snap}>"
        )
