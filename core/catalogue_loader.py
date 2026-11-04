import json
import os

CATALOGUE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue.json")
PACKAGE_TYPES = {"native", "flatpak", "snap", "script"}

DEFAULT_CATALOGUE = [
    {"id": "git", "name": "Git", "description": "Distributed version control.",
     "category": "Development", "package_name": "git", "package_type": "native"},
    {"id": "htop", "name": "htop", "description": "Interactive process viewer.",
     "category": "System", "package_name": "htop", "package_type": "native"},
    {"id": "curl", "name": "cURL", "description": "Transfer data with URLs.",
     "category": "Utilities", "package_name": "curl", "package_type": "native"},
]


def load_catalogue(path=None):
    """Carrega o catálogo. Se o arquivo não existir, cria um exemplo padrão."""
    path = path or CATALOGUE_PATH

    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(DEFAULT_CATALOGUE, f, indent=4)
        return list(DEFAULT_CATALOGUE)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Catalogue must be a JSON array: {path}")

    # Normaliza campos opcionais
    app_ids = set()
    for index, app in enumerate(data, start=1):
        if not isinstance(app, dict):
            raise ValueError(f"Catalogue entry {index} must be a JSON object: {path}")
        app.setdefault("package_type", "native")
        app.setdefault("category", "Other")
        for field in ("id", "name", "description", "package_name"):
            value = app.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Catalogue entry {index} has a missing or invalid "
                    f"{field!r}: {path}"
                )
        if app["id"] in app_ids:
            raise ValueError(f"Catalogue entry {index} has duplicate id {app['id']!r}: {path}")
        app_ids.add(app["id"])
        if not isinstance(app["category"], str) or not app["category"].strip():
            raise ValueError(f"Catalogue entry {index} has an invalid 'category': {path}")
        if (
            not isinstance(app["package_type"], str)
            or app["package_type"] not in PACKAGE_TYPES
        ):
            raise ValueError(
                f"Catalogue entry {index} has an unsupported 'package_type': {path}"
            )
    return data
