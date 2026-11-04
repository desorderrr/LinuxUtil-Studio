import subprocess
from core.system_info import SystemInfo


class Installer:
    def __init__(self):
        self.sys_info = SystemInfo()

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    @staticmethod
    def _command_ok(cmd, timeout=15):
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
            )
            return result.returncode == 0
        except Exception:
            return False

    def is_installed(self, app):
        """Verifica se o app já está presente no sistema.

        Entradas do tipo ``script`` (packs) declaram em ``check`` os pacotes que
        provam que o pack já foi aplicado.
        """
        if app.get("package_type") == "script":
            checks = app.get("check") or []
            if not checks:
                return False
            return all(
                self._command_ok(
                    self.sys_info.get_check_command(
                        {"package_name": name, "package_type": "native"}
                    )
                )
                for name in checks
            )

        cmd = self.sys_info.get_check_command(app)
        if not cmd:
            return False
        if app.get("package_type", "native") != "script":
            cmd = self.sys_info.host_wrap(cmd)
        return self._command_ok(cmd)

    # ------------------------------------------------------------------
    # Instalação
    # ------------------------------------------------------------------
    @staticmethod
    def _explain_failure(cmd, returncode):
        """Traduz códigos de saída conhecidos numa mensagem legível."""
        if cmd[0] == "pkexec" and returncode == 126:
            return "Autorização cancelada (o pedido de password foi fechado)."
        if cmd[0] == "pkexec" and returncode == 127:
            return "Autorização recusada pelo sistema (polkit)."
        if cmd[0] == "sudo" and returncode == 1:
            return (
                "O sudo não conseguiu pedir a password (sem terminal). "
                "Corre a app a partir de um terminal ou configura o sudo sem password."
            )
        return f"Command failed (exit {returncode}): {' '.join(cmd)}"

    def _no_installer_message(self, app):
        package_type = app.get("package_type", "native")
        name = app.get("name", app.get("id", "?"))
        if package_type == "flatpak" and not self.sys_info.has_flatpak:
            return f"{name} needs Flatpak, which is not installed on this system."
        if package_type == "snap" and not self.sys_info.has_snap:
            return f"{name} needs Snap, which is not installed on this system."
        if package_type == "script":
            family = self.sys_info.family or "this distro"
            return f"No setup script available for {family}."
        if not self.sys_info.package_manager:
            return f"No supported package manager found for {name}."
        return f"No suitable installer found for {name} on this system."

    def run_install(self, app, on_output=None, dry_run=False):
        """
        Executa a instalação (ou a pré-visualização, quando ``dry_run``).

        on_output: callable(str) opcional, chamado a cada linha de log
                   (usado pela GUI para streaming em tempo real).
        """
        commands = self.sys_info.get_install_commands(app, dry_run=dry_run)
        if not commands:
            return {
                "status": "error",
                "message": self._no_installer_message(app),
                "output": [],
            }

        full_output = []
        name = app.get("name", app.get("id", "?"))

        def emit(line):
            full_output.append(line)
            if on_output:
                try:
                    on_output(line)
                except Exception:
                    pass

        # Para pacotes nativos/flatpak/snap o dry-run é puramente informativo:
        # mostramos os comandos mas não executamos nada. Os packs (scripts)
        # correm o próprio script com --dry-run, por isso continuam no loop.
        if dry_run and app.get("package_type", "native") != "script":
            for cmd in commands:
                emit(f"$ {' '.join(self.sys_info.host_wrap(cmd))}")
            return {
                "status": "success",
                "message": f"Preview for {name} finished (nothing was changed).",
                "output": full_output,
                "dry_run": True,
            }

        for raw_cmd in commands:
            cmd = (
                raw_cmd
                if app.get("package_type") == "script"
                else self.sys_info.host_wrap(raw_cmd)
            )
            emit(f"$ {' '.join(cmd)}")
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                for line in process.stdout:
                    emit(line.rstrip())
                process.wait()

                if process.returncode != 0:
                    return {
                        "status": "error",
                        "message": self._explain_failure(cmd, process.returncode),
                        "output": full_output,
                    }
            except FileNotFoundError:
                return {
                    "status": "error",
                    "message": f"Command not found: {cmd[0]}",
                    "output": full_output,
                }
            except Exception as e:
                return {"status": "error", "message": str(e), "output": full_output}

        if dry_run:
            return {
                "status": "success",
                "message": f"Preview for {name} finished (nothing was changed).",
                "output": full_output,
                "dry_run": True,
            }

        return {
            "status": "success",
            "message": f"Successfully installed {name}",
            "output": full_output,
        }
