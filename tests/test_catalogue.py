"""Testes do LinuxUtil Studio, sem dependências externas.

Correr com:

    python3 -m unittest discover -s tests -v

Os testes de catálogo não precisam de PySide6: validam o JSON, os logos e os
scripts de gaming. O teste de script só corre a família do sistema atual,
por isso é seguro em Fedora, Debian/Ubuntu e Arch.
"""

import os
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.catalogue_loader import load_catalogue  # noqa: E402
from core.installer import Installer  # noqa: E402
from core.system_info import SystemInfo  # noqa: E402

CATEGORIES = {
    "Internet", "Communication", "Development", "Gaming", "Media",
    "Graphics", "Productivity", "System", "Utilities",
}
PACKAGE_TYPES = {"native", "flatpak", "snap", "script", "vendor"}
FAMILIES = {"debian", "fedora", "arch", "suse"}
REQUIRED_FIELDS = ("id", "name", "description", "category", "package_name", "package_type")


class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apps = load_catalogue()
        cls.by_id = {app["id"]: app for app in cls.apps}

    def test_ids_are_unique(self):
        self.assertEqual(len(self.apps), len(self.by_id), "há IDs repetidos no catálogo")

    def test_required_fields(self):
        for app in self.apps:
            for field in REQUIRED_FIELDS:
                self.assertIn(field, app, app.get("id"))
                self.assertTrue(str(app[field]).strip(), f"{app['id']}: campo vazio {field}")

    def test_categories_are_known(self):
        for app in self.apps:
            self.assertIn(app["category"], CATEGORIES, app["id"])

    def test_package_types_are_known(self):
        for app in self.apps:
            self.assertIn(app["package_type"], PACKAGE_TYPES, app["id"])

    def test_package_overrides_use_known_families(self):
        for app in self.apps:
            for family in app.get("packages") or {}:
                self.assertIn(family, FAMILIES, app["id"])

    def test_vendor_entries_have_flatpak_fallbacks(self):
        for app in self.apps:
            if app["package_type"] == "vendor":
                self.assertEqual(app.get("fallback_type"), "flatpak", app["id"])
                self.assertTrue(app.get("fallback_package_name"), app["id"])

    def test_scripts_exist_and_are_declared(self):
        for app in self.apps:
            if app["package_type"] != "script":
                continue
            self.assertTrue(app.get("scripts"), app["id"])
            for name in app["scripts"].values():
                path = os.path.join(ROOT, "scripts", name)
                self.assertTrue(os.path.isfile(path), f"{app['id']}: falta {path}")
            self.assertTrue(app.get("check"), f"{app['id']}: sem lista 'check'")

    def test_bundled_logos_are_svg(self):
        logo_dir = os.path.join(ROOT, "assets", "logos")
        for app in self.apps:
            path = os.path.join(logo_dir, app["id"] + ".svg")
            if not os.path.exists(path):
                continue
            with open(path, "rb") as handle:
                head = handle.read(200)
            self.assertIn(b"<svg", head, path)

    def test_invalid_catalogue_shape_is_rejected(self):
        for contents, expected in (
            ('{"apps": []}', "JSON array"),
            ('[null]', "JSON object"),
            ('[{"id": "test"}]', "'name'"),
            (
                '[{"id": "test", "name": "Test", "description": "Test", '
                '"package_name": "test", "package_type": "unknown"}]',
                "unsupported 'package_type'",
            ),
            (
                '[{"id": "test", "name": "Test", "description": "Test", '
                '"package_name": "test", "aur_package": ""}]',
                "invalid 'aur_package'",
            ),
            (
                '[{"id": "test", "name": "Test", "description": "Test", '
                '"package_name": "test"}, {"id": "test", "name": "Again", '
                '"description": "Test", "package_name": "again"}]',
                "duplicate id",
            ),
        ):
            with self.subTest(contents=contents), tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8"
            ) as handle:
                handle.write(contents)
                handle.flush()
                with self.assertRaisesRegex(ValueError, expected):
                    load_catalogue(handle.name)


class BrandingTests(unittest.TestCase):
    def test_project_logo_is_svg(self):
        path = os.path.join(ROOT, "assets", "logo.svg")
        self.assertTrue(os.path.isfile(path), "falta assets/logo.svg")
        with open(path, "rb") as handle:
            self.assertIn(b"<svg", handle.read(200))


class ResolutionTests(unittest.TestCase):
    """Confirma que cada entrada tem um alvo utilizável nesta distro."""

    @classmethod
    def setUpClass(cls):
        cls.info = SystemInfo()
        cls.apps = load_catalogue()

    def test_native_packages_resolve(self):
        for app in self.apps:
            if app["package_type"] != "native":
                continue
            self.assertTrue(self.info.resolve_package(app), app["id"])

    def test_script_resolves_on_supported_family(self):
        if not self.info.family:
            self.skipTest("família desconhecida")
        checked = 0
        for app in self.apps:
            if app["package_type"] != "script":
                continue
            if (app.get("scripts") or {}).get(self.info.family):
                self.assertTrue(self.info.resolve_script(app), app["id"])
                checked += 1
        self.assertGreater(checked, 0, f"nenhum script para {self.info.family}")

    def test_install_commands_are_quoted_as_argv(self):
        """Comandos nativos nunca podem passar por um shell."""
        for app in self.apps:
            for cmd in self.info.get_install_commands(app):
                self.assertIsInstance(cmd, list, app["id"])
                self.assertTrue(all(isinstance(part, str) for part in cmd), app["id"])

    def test_os_release_parses_openSUSE_and_id_like(self):
        parsed = SystemInfo._parse_os_release(
            'ID=opensuse-tumbleweed\n'
            'ID_LIKE="suse opensuse"\n'
            'PRETTY_NAME="openSUSE Tumbleweed"\n'
        )
        self.assertEqual(parsed["ID"], "opensuse-tumbleweed")
        self.assertEqual(parsed["PRETTY_NAME"], "openSUSE Tumbleweed")

        info = SystemInfo.__new__(SystemInfo)
        info.distro = parsed["ID"]
        info.distro_like = parsed["ID_LIKE"].split()
        self.assertEqual(info._get_package_manager(), "zypper")

    def test_distro_is_read_from_os_release(self):
        info = SystemInfo.__new__(SystemInfo)
        info.is_flatpak = False
        info.distro_like = []
        with mock.patch(
            "builtins.open",
            mock.mock_open(read_data='ID="opensuse-leap"\nID_LIKE="suse"\n'),
        ):
            self.assertEqual(info._get_distro(), "opensuse-leap")
        self.assertEqual(info.distro_like, ["suse"])

    def test_id_like_selects_compatible_package_manager(self):
        info = SystemInfo.__new__(SystemInfo)
        info.distro = "custom-linux"
        info.distro_like = ["debian"]
        self.assertEqual(info._get_package_manager(), "apt")

    def test_native_remove_commands_keep_package_manager_dependencies(self):
        expected = {
            "apt": ["sudo", "apt-get", "remove", "-y", "sample"],
            "dnf": ["sudo", "dnf", "remove", "--no-autoremove", "-y", "sample"],
            "pacman": ["sudo", "pacman", "-R", "--noconfirm", "sample"],
            "zypper": ["sudo", "zypper", "remove", "-y", "sample"],
        }
        app = {"package_type": "native", "package_name": "sample"}
        for manager, command in expected.items():
            with self.subTest(manager=manager):
                info = SystemInfo.__new__(SystemInfo)
                info.package_manager = manager
                info._privilege_tool = "sudo"
                self.assertEqual(info.get_remove_commands(app), [command])

    def test_arch_native_install_keeps_pkexec_even_with_aur_helper(self):
        # yay/paru call sudo internally; in a GUI session without a terminal
        # that fails. Official repository packages must stay on pacman + pkexec.
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "pacman"
        info.aur_helpers = ["yay", "paru"]
        info._privilege_tool = "pkexec"
        app = {"package_type": "native", "package_name": "sample"}
        self.assertEqual(
            info.get_install_commands(app),
            [["pkexec", "pacman", "-S", "--noconfirm", "sample"]],
        )

    def test_arch_aur_install_uses_detected_helper(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "pacman"
        info.is_flatpak = False
        info.has_flatpak = True
        info.aur_helpers = ["paru", "yay"]
        app = {
            "id": "brave",
            "name": "Brave",
            "package_type": "vendor",
            "aur_package": "brave-bin",
            "fallback_type": "flatpak",
            "package_name": "com.brave.Browser",
        }
        self.assertEqual(info.resolve_package_type(app), "aur")
        self.assertEqual(
            info.get_install_commands(app),
            [["paru", "-S", "--needed", "--noconfirm", "brave-bin"]],
        )

    def test_arch_install_without_aur_helper_uses_pacman(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "pacman"
        info.aur_helpers = []
        info._privilege_tool = "pkexec"
        app = {"package_type": "native", "package_name": "sample"}
        self.assertEqual(
            info.get_install_commands(app),
            [["pkexec", "pacman", "-S", "--noconfirm", "sample"]],
        )

    def test_immutable_detection_prefers_ostree_boot_marker(self):
        info = SystemInfo.__new__(SystemInfo)
        info.is_flatpak = False
        with mock.patch.object(
            SystemInfo,
            "_host_has",
            side_effect=lambda binary: binary in {"rpm-ostree", "transactional-update"},
        ), mock.patch.object(SystemInfo, "_host_path_exists", return_value=True):
            self.assertEqual(info._detect_immutable(), "rpm-ostree")

    def test_immutable_detection_ignores_rpm_ostree_without_boot_marker(self):
        info = SystemInfo.__new__(SystemInfo)
        info.is_flatpak = False
        with mock.patch.object(
            SystemInfo, "_host_has", side_effect=lambda binary: binary == "rpm-ostree"
        ), mock.patch.object(SystemInfo, "_host_path_exists", return_value=False):
            self.assertIsNone(info._detect_immutable())

    def test_native_install_layers_with_rpm_ostree(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "dnf"
        info.immutable = "rpm-ostree"
        info._privilege_tool = "pkexec"
        app = {"package_type": "native", "package_name": "htop"}
        self.assertEqual(
            info.get_install_commands(app),
            [["pkexec", "rpm-ostree", "install", "--idempotent", "htop"]],
        )
        self.assertEqual(
            info.get_remove_commands(app),
            [["pkexec", "rpm-ostree", "uninstall", "--idempotent", "htop"]],
        )

    def test_native_install_uses_transactional_update(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "zypper"
        info.immutable = "transactional-update"
        info._privilege_tool = "pkexec"
        app = {"package_type": "native", "package_name": "htop"}
        self.assertEqual(
            info.get_install_commands(app),
            [[
                "pkexec", "transactional-update", "--non-interactive",
                "pkg", "install", "-y", "htop",
            ]],
        )
        self.assertEqual(
            info.get_remove_commands(app),
            [[
                "pkexec", "transactional-update", "--non-interactive",
                "pkg", "remove", "-y", "htop",
            ]],
        )

    def test_vendor_apps_fall_back_to_flatpak_on_immutable(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "dnf"
        info.is_flatpak = False
        info.has_flatpak = True
        info.aur_helpers = []
        info.immutable = "rpm-ostree"
        app = next(item for item in load_catalogue() if item["id"] == "vscode")
        self.assertEqual(info.resolve_package_type(app), "flatpak")

    def test_gaming_packs_are_unavailable_on_immutable(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "dnf"
        info.immutable = "rpm-ostree"
        app = next(item for item in load_catalogue() if item["id"] == "gaming-pack")
        self.assertIsNone(info.resolve_package_type(app))

    def test_vendor_apps_use_aur_when_helper_is_available(self):
        apps = load_catalogue()
        expected = {
            "brave": ("brave-bin", "yay"),
            "vscode": ("visual-studio-code-bin", "yay"),
        }
        for app_id, (package, helper) in expected.items():
            with self.subTest(app=app_id):
                info = SystemInfo.__new__(SystemInfo)
                info.package_manager = "pacman"
                info.is_flatpak = False
                info.has_flatpak = True
                info.aur_helpers = [helper]
                app = next(item for item in apps if item["id"] == app_id)
                self.assertEqual(info.resolve_package_type(app), "aur")
                self.assertEqual(info.resolve_package_name(app), package)
                self.assertEqual(
                    info.get_install_commands(app),
                    [[helper, "-S", "--needed", "--noconfirm", package]],
                )
                self.assertEqual(info.get_check_command(app), ["pacman", "-Q", package])

    def test_vendor_apps_keep_flatpak_fallback_without_aur_helper(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "pacman"
        info.is_flatpak = False
        info.has_flatpak = True
        info.aur_helpers = []
        app = next(item for item in load_catalogue() if item["id"] == "vscode")
        self.assertEqual(info.resolve_package_type(app), "flatpak")
        self.assertEqual(
            info.get_install_commands(app),
            [["flatpak", "install", "-y", "flathub", "com.visualstudio.code"]],
        )

    def test_available_updates_parses_zypper_table_rows(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "zypper"
        info.is_flatpak = False
        output = (
            "S | Repository | Name | Current Version | Available Version | Arch\n"
            "--+------------+------+-----------------+-------------------+-----\n"
            "v | repo-oss | mesa | 1 | 2 | x86_64\n"
            "i | repo-oss | lutris | 1 | 2 | x86_64\n"
        )
        with mock.patch(
            "core.system_info.subprocess.run",
            return_value=mock.Mock(returncode=0, stdout=output, stderr=""),
        ):
            self.assertEqual(info.available_updates(), ["mesa", "lutris"])

    def test_available_updates_accepts_dnf_update_exit_code(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "dnf"
        info.is_flatpak = False
        with mock.patch(
            "core.system_info.subprocess.run",
            return_value=mock.Mock(
                returncode=100,
                stdout="mesa.x86_64 1 2 updates\n",
                stderr="",
            ),
        ):
            self.assertEqual(info.available_updates(), ["mesa"])

    def test_available_updates_reports_command_errors(self):
        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "zypper"
        info.is_flatpak = False
        with mock.patch(
            "core.system_info.subprocess.run",
            return_value=mock.Mock(returncode=4, stdout="", stderr="repository unavailable"),
        ):
            with self.assertRaisesRegex(RuntimeError, "repository unavailable"):
                info.available_updates()

    def test_gaming_pack_installed_check_uses_only_required_tools(self):
        installer = Installer()
        app = next(app for app in load_catalogue() if app["id"] == "gaming-pack")
        self.assertEqual(app["check"], ["lutris", "mangohud"])
        with mock.patch.object(
            installer.sys_info,
            "get_check_command",
            side_effect=lambda item: ["check", item["package_name"]],
        ), mock.patch.object(installer.sys_info, "host_wrap", side_effect=lambda cmd: cmd), \
                mock.patch.object(installer, "_command_ok", return_value=True):
            self.assertTrue(installer.is_installed(app))

    def test_flatpak_remove_preserves_app_data_by_default(self):
        info = SystemInfo.__new__(SystemInfo)
        info.has_flatpak = True
        info.is_flatpak = False
        command = info.get_remove_commands({
            "package_type": "flatpak",
            "package_name": "org.example.App",
        })
        self.assertEqual(
            command,
            [["flatpak", "uninstall", "--noninteractive", "-y", "org.example.App"]],
        )
        self.assertNotIn("--delete-data", command[0])

    def test_scripts_have_no_automatic_remove_command(self):
        info = SystemInfo.__new__(SystemInfo)
        self.assertEqual(
            info.get_remove_commands({"package_type": "script"}), []
        )

    def test_vendor_apps_use_native_repositories_with_flatpak_fallback(self):
        app = next(item for item in load_catalogue() if item["id"] == "vscode")
        for manager in ("apt", "dnf", "zypper"):
            with self.subTest(manager=manager):
                info = SystemInfo.__new__(SystemInfo)
                info.package_manager = manager
                info.is_flatpak = False
                info.has_flatpak = True
                info._privilege_tool = "pkexec"
                self.assertEqual(info.resolve_package_type(app), "vendor")
                command = info.get_install_commands(app)
                self.assertEqual(command[0][0], "pkexec")
                self.assertEqual(command[0][-2:], ["vscode", "install"])
                self.assertEqual(info.get_check_command(app)[-1], "code")
                self.assertEqual(info.get_remove_commands(app)[0][-2:], ["vscode", "remove"])

        info = SystemInfo.__new__(SystemInfo)
        info.package_manager = "pacman"
        info.is_flatpak = False
        info.has_flatpak = True
        self.assertEqual(info.resolve_package_type(app), "flatpak")
        self.assertEqual(
            info.get_install_commands(app),
            [["flatpak", "install", "-y", "flathub", "com.visualstudio.code"]],
        )


class DryRunTests(unittest.TestCase):
    """``--dry-run`` nunca pode executar comandos nativos."""

    def test_native_dry_run_does_not_execute(self):
        installer = Installer()
        app = {
            "id": "__test__",
            "name": "Test",
            "package_type": "native",
            "package_name": "true",
        }
        with mock.patch.object(
            installer.sys_info, "get_install_commands", return_value=[["true"]]
        ), mock.patch("core.installer.subprocess.Popen") as popen:
            result = installer.run_install(app, dry_run=True)

        popen.assert_not_called()
        self.assertEqual(result["status"], "success")
        self.assertTrue(result.get("dry_run"))
        self.assertIn("$ true", result["output"])

    def test_install_command_failure_is_reported(self):
        installer = Installer()
        app = {"id": "test", "name": "Test", "package_type": "native"}
        with mock.patch.object(
            installer.sys_info,
            "get_install_commands",
            return_value=[[sys.executable, "-c", "raise SystemExit(4)"]],
        ):
            result = installer.run_install(app)

        self.assertEqual(result["status"], "error")
        self.assertIn("exit 4", result["message"])

    def test_running_install_can_be_cancelled(self):
        installer = Installer()
        app = {"id": "test", "name": "Test", "package_type": "native"}
        cancel_event = threading.Event()
        timer = threading.Timer(0.2, cancel_event.set)
        timer.daemon = True
        with mock.patch.object(
            installer.sys_info,
            "get_install_commands",
            return_value=[[sys.executable, "-c", "import time; time.sleep(30)"]],
        ):
            timer.start()
            result = installer.run_install(app, cancel_event=cancel_event)
            timer.join()

        self.assertEqual(result["status"], "cancelled")
        self.assertIn("not rolled back", result["message"])

    def test_remove_runs_command_and_reports_success(self):
        installer = Installer()
        app = {"id": "test", "name": "Test", "package_type": "native"}
        with mock.patch.object(
            installer.sys_info,
            "get_remove_commands",
            return_value=[[sys.executable, "-c", "print('removed')"]],
        ):
            result = installer.run_remove(app)

        self.assertEqual(result["status"], "success")
        self.assertIn("removed", result["output"])

    def test_remove_refuses_setup_scripts(self):
        result = Installer().run_remove(
            {"id": "gaming-pack", "name": "Gaming Pack", "package_type": "script"}
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("cannot be removed automatically", result["message"])


class ImmutableTests(unittest.TestCase):
    def _installer(self, immutable="rpm-ostree"):
        installer = Installer.__new__(Installer)
        installer.sys_info = mock.Mock()
        installer.sys_info.immutable = immutable
        return installer

    def test_native_install_reports_reboot_required(self):
        installer = self._installer()
        installer.sys_info.get_install_commands.return_value = [
            ["rpm-ostree", "install", "--idempotent", "htop"]
        ]
        installer.sys_info.resolve_package_type.return_value = "native"
        app = {"id": "htop", "name": "htop", "package_type": "native"}
        with mock.patch.object(
            installer,
            "_execute_commands",
            return_value={"status": "success", "output": []},
        ):
            result = installer.run_install(app)
        self.assertEqual(result["status"], "success")
        self.assertIn("Reboot", result["message"])

    def test_gaming_pack_explains_immutable_limitation(self):
        installer = self._installer()
        installer.sys_info.get_install_commands.return_value = []
        installer.sys_info.resolve_package_type.return_value = None
        app = {"id": "gaming-pack", "name": "Gaming Pack", "package_type": "script"}
        result = installer.run_install(app)
        self.assertEqual(result["status"], "error")
        self.assertIn("writable system package manager", result["message"])


class ScriptTests(unittest.TestCase):
    def test_host_script_dry_run_changes_nothing(self):
        info = SystemInfo()
        if not info.family:
            self.skipTest("família desconhecida")

        app = next(a for a in load_catalogue() if a["id"] == "gaming-pack")
        name = (app.get("scripts") or {}).get(info.family)
        if not name:
            self.skipTest(f"sem gaming pack para {info.family}")

        path = os.path.join(ROOT, "scripts", name)
        result = subprocess.run(
            ["bash", path, "--dry-run"],
            capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nothing was changed", result.stdout)
        self.assertIn("[dry-run]", result.stdout)

    def test_vendor_repository_scripts_support_dry_run(self):
        script = os.path.join(ROOT, "scripts", "vendor_apps.sh")
        for app_id in ("vscode", "brave"):
            with self.subTest(app=app_id):
                result = subprocess.run(
                    ["bash", script, app_id, "install", "--dry-run"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("[dry-run]", result.stdout)
                self.assertIn("nothing", result.stdout.lower())

        if SystemInfo().family == "fedora":
            result = subprocess.run(
                ["bash", script, "vscode", "remove", "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("dnf remove --no-autoremove", result.stdout)

    def test_suse_pack_recognizes_installed_packages_and_skips_optional_missing(self):
        script = os.path.join(ROOT, "scripts", "gaming_suse.sh")
        with tempfile.TemporaryDirectory() as temp_dir:
            zypper = os.path.join(temp_dir, "zypper")
            with open(zypper, "w", encoding="utf-8") as handle:
                handle.write(
                    "#!/bin/sh\n"
                    "if [ \"$1\" = search ]; then\n"
                    "  if [ \"$3\" != gamescope ]; then\n"
                    "    printf '%s\\n' 'S | Name | Summary | Type'\n"
                    "    printf '%s\\n' '--+------+---------+-------'\n"
                    "    printf 'i | %s | test | package\\n' \"$3\"\n"
                    "  fi\n"
                    "fi\n"
                    "exit 0\n"
                )
            for command in ("flatpak", "lutris", "mangohud"):
                command_path = os.path.join(temp_dir, command)
                with open(command_path, "w", encoding="utf-8") as handle:
                    handle.write("#!/bin/sh\nexit 0\n")
                os.chmod(command_path, 0o755)
            os.chmod(zypper, 0o755)

            result = subprocess.run(
                ["bash", script],
                capture_output=True,
                text=True,
                timeout=30,
                env={"PATH": temp_dir + os.pathsep + os.environ["PATH"]},
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not-available:gamescope", result.stdout)
        self.assertNotIn("not-available:lutris", result.stdout)
        self.assertIn("Gaming pack ready", result.stdout)


if __name__ == "__main__":
    unittest.main()
