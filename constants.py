import os
import sys
from pathlib import Path

APP_ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
CONFIG_DIR = APP_ROOT / "config"
LOG_DIR = APP_ROOT / "logs"
TEMPLATE_DIR = APP_ROOT / "templates"
DOSSIER_TICKETS = APP_ROOT / "tickets_generes"
CONFIG_FILE = CONFIG_DIR / "config_email.json"
LOG_FILE = LOG_DIR / "app.log"
SUPPORTED_IMAGE_FORMATS = [("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Tous fichiers", "*.*")]

# Créer les dossiers nécessaires automatiquement
for dir_path in [CONFIG_DIR, LOG_DIR, TEMPLATE_DIR, DOSSIER_TICKETS]:
    dir_path.mkdir(parents=True, exist_ok=True)
