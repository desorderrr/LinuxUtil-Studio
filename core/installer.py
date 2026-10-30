import subprocess
from core.system_info import SystemInfo

class Installer:
    def __init__(self):
        self.sys_info = SystemInfo()

    def run_install(self, package_name, package_type=None):
        command = self.sys_info.get_install_command(package_name, package_type)
        if not command:
            return {"status": "error", "message": f"No suitable installer found for {package_name} on this system."}

        try:
            # Executa o comando
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                shell=True
            )

            output = []
            for line in process.stdout:
                clean_line = line.strip()
                print(clean_line) # Debug inicial
                output.append(clean_line)
            
            process.wait()
            
            if process.returncode == 0:
                return {"status": "success", "message": f"Successfully installed {package_name}", "output": output}
            else:
                return {"status": "error", "message": f"Failed to install {package_name}", "output": output}

        except Exception as e:
            return {"status": "error", "message": str(e)}
