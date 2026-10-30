import json
import os

def load_catalogue():
    catalogue_path = "catalogue.json"
    
    if not os.path.exists(catalogue_path):
        example_data = [
            {"id": "git", "name": "Git", "description": "Distributed version control.", "category": "Dev", "package_name": "git", "package_type": "apt"},
            {"id": "neovim", "name": "Neovim", "description": "Extensible Vim-based editor.", "category": "Dev", "package_name": "neovim", "package_type": "apt"},
            {"id": "curl", "name": "Curl", "description": "Network tool.", "category": "Utils", "package_name": "curl", "package_type": "apt"},
            {"id": "htop", "name": "Htop", "description": "Process viewer.", "category": "System", "package_name": "htop", "package_type": "apt"},
            {"id": "spotify", "name": "Spotify", "description": "Music streaming.", "category": "Media", "package_name": "com.spotify.Client", "package_type": "flatpak"},
            {"id": "discord", "name": "Discord", "description": "Voice and text chat.", "category": "Social", "package_name": "discord", "package_type": "snap"}
        ]
        with open(catalogue_path, "w") as f:
            json.dump(example_data, f, indent=4)
            
    with open(catalogue_path, "r") as f:
        return json.load(f)
