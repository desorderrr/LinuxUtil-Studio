import os
import signal
import subprocess
import threading
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
        except FileNotFoundError:
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
            for name in checks:
                cmd = self.sys_info.get_check_command(
                    {"package_name": name, "package_type": "native"}
                )
                if not cmd or not self._command_ok(self.sys_info.host_wrap(cmd)):
                    return False
            return True

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
        package_type = self.sys_info.resolve_package_type(app)
        name = app.get("name", app.get("id", "?"))
        if package_type == "flatpak" and not self.sys_info.has_flatpak:
            return f"{name} needs Flatpak, which is not installed on this system."
        if package_type == "snap" and not self.sys_info.has_snap:
            return f"{name} needs Snap, which is not installed on this system."
        if app.get("package_type") == "vendor" and package_type is None:
            return f"No supported vendor installer or fallback is available for {name}."
        if package_type == "script":
            family = self.sys_info.family or "this distro"
            return f"No setup script available for {family}."
        if not self.sys_info.package_manager:
            return f"No supported package manager found for {name}."
        return f"No suitable installer found for {name} on this system."

    def run_install(self, app, on_output=None, dry_run=False, cancel_event=None):
        """
        Executa a instalação (ou a pré-visualização, quando ``dry_run``).

        on_output: callable(str) opcional, chamado a cada linha de log
                   (usado pela GUI para streaming em tempo real).
        cancel_event: threading.Event opcional para cancelar o comando ativo.
        """
        commands = self.sys_info.get_install_commands(app, dry_run=dry_run)
        if not commands:
            return {
                "status": "error",
                "message": self._no_installer_message(app),
                "output": [],
            }

        name = app.get("name", app.get("id", "?"))

        # Para pacotes nativos/flatpak/snap o dry-run é puramente informativo:
        # mostramos os comandos mas não executamos nada. Os packs (scripts)
        # correm o próprio script com --dry-run, por isso continuam no loop.
        if dry_run and self.sys_info.resolve_package_type(app) not in {"script", "vendor"}:
            full_output = []
            for cmd in commands:
                line = f"$ {' '.join(self.sys_info.host_wrap(cmd))}"
                full_output.append(line)
                if on_output:
                    on_output(line)
            return {
                "status": "success",
                "message": f"Preview for {name} finished (nothing was changed).",
                "output": full_output,
                "dry_run": True,
            }

        result = self._execute_commands(
            app, commands, on_output=on_output, cancel_event=cancel_event
        )
        if result["status"] != "success":
            return result

        if dry_run:
            return {
                "status": "success",
                "message": f"Preview for {name} finished (nothing was changed).",
                "output": result["output"],
                "dry_run": True,
            }

        return {
            "status": "success",
            "message": f"Successfully installed {name}",
            "output": result["output"],
        }

    def _execute_commands(self, app, commands, on_output=None, cancel_event=None):
        full_output = []
        name = app.get("name", app.get("id", "?"))

        def emit(line):
            full_output.append(line)
            if on_output:
                on_output(line)

        def stop_process_group(process):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                process.wait()

        for raw_cmd in commands:
            if cancel_event and cancel_event.is_set():
                return {
                    "status": "cancelled",
                    "message": f"Operation on {name} was cancelled before the next command.",
                    "output": full_output,
                }

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
                    start_new_session=True,
                )
                command_finished = threading.Event()

                def stop_process_on_cancel():
                    while process.poll() is None and not command_finished.wait(0.1):
                        if cancel_event and cancel_event.is_set():
                            stop_process_group(process)
                            return

                cancel_watcher = None
                if cancel_event:
                    cancel_watcher = threading.Thread(
                        target=stop_process_on_cancel, daemon=True
                    )
                    cancel_watcher.start()

                try:
                    with process.stdout:
                        for line in process.stdout:
                            emit(line.rstrip())
                    process.wait()
                finally:
                    if process.poll() is None:
                        stop_process_group(process)
                    command_finished.set()
                    if cancel_watcher:
                        cancel_watcher.join(timeout=1)

                if cancel_event and cancel_event.is_set():
                    return {
                        "status": "cancelled",
                        "message": f"Operation on {name} was cancelled. Completed changes were not rolled back.",
                        "output": full_output,
                    }
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
            except Exception as error:
                return {"status": "error", "message": str(error), "output": full_output}

        return {"status": "success", "output": full_output}

    def run_remove(self, app, on_output=None, cancel_event=None):
        """Remove uma aplicação individual; scripts compostos não são removíveis."""
        name = app.get("name", app.get("id", "?"))
        if app.get("package_type") == "script":
            return {
                "status": "error",
                "message": "Setup scripts and gaming packs cannot be removed automatically.",
                "output": [],
            }

        commands = self.sys_info.get_remove_commands(app)
        if not commands:
            return {
                "status": "error",
                "message": f"No supported removal command available for {name}.",
                "output": [],
            }

        result = self._execute_commands(
            app, commands, on_output=on_output, cancel_event=cancel_event
        )
        if result["status"] != "success":
            return result

        return {
            "status": "success",
            "message": f"Successfully removed {name}",
            "output": result["output"],
        }
