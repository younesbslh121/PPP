import json
import os

project_path = "/home/younes/Projects/PPP"

with open(os.path.join(project_path, "class_names.json"), "r", encoding="utf-8") as f:
    class_names = json.load(f)

with open(os.path.join(project_path, "allergens_db.json"), "r", encoding="utf-8") as f:
    allergens_db = json.load(f)

with open(os.path.join(project_path, "translations.json"), "r", encoding="utf-8") as f:
    translations = json.load(f)

fallback_config = {
    "class_names": class_names,
    "allergens_db": allergens_db,
    "translations": translations
}

out_path = os.path.join(project_path, "static", "config_fallback.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(fallback_config, f, ensure_ascii=False, indent=2)

print("Created static/config_fallback.json successfully!")
