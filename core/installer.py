import subprocess
from core.system_info import SystemInfo


class Installer:
    def __init__(self):
        self.sys_info = SystemInfo()

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    def is_installed(self, package_name, package_type=None):
        """Verifica se o pacote já está presente no sistema."""
        cmd = self.sys_info.get_check_command(package_name, package_type)
        if not cmd:
            return False
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False

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

    def run_install(self, package_name, package_type=None, on_output=None):
        """
        Executa a instalação.

        on_output: callable(str) opcional, chamado a cada linha de log
                   (usado pela GUI para streaming em tempo real).
        """
        commands = self.sys_info.get_install_commands(package_name, package_type)
        if not commands:
            return {
                "status": "error",
                "message": f"No suitable installer found for {package_name} on this system.",
                "output": [],
            }

        full_output = []

        def emit(line):
            full_output.append(line)
            if on_output:
                try:
                    on_output(line)
                except Exception:
                    pass

        for cmd in commands:
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

        return {
            "status": "success",
            "message": f"Successfully installed {package_name}",
            "output": full_output,
        }
