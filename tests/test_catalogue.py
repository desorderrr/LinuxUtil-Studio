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
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.catalogue_loader import load_catalogue  # noqa: E402
from core.system_info import SystemInfo  # noqa: E402

CATEGORIES = {
    "Internet", "Communication", "Development", "Gaming", "Media",
    "Graphics", "Productivity", "System", "Utilities",
}
PACKAGE_TYPES = {"native", "flatpak", "snap", "script"}
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


if __name__ == "__main__":
    unittest.main()
