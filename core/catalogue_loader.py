import json
import os

CATALOGUE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue.json")

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

    with open(path, "r") as f:
        data = json.load(f)

    # Normaliza campos opcionais
    for app in data:
        app.setdefault("package_type", "native")
        app.setdefault("category", "Other")
    return data
