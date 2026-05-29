import io
import time
from pathlib import Path
from constants import LOG_FILE

class Utils:
    """Fonctions utilitaires réutilisables"""

    @staticmethod
    def sanitize_folder_name(name: str) -> str:
        return name.replace(" ", "_").replace("/", "-").replace("\\", "-").strip("_-" )

    @staticmethod
    def ensure_directory(path) -> bool:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Erreur création dossier {path}: {e}")
            return False

    @staticmethod
    def write_log(message: str) -> None:
        try:
            log_path = Path(LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    @staticmethod
    def copy_buffer(buffer: io.BytesIO) -> io.BytesIO:
        buffer.seek(0)
        return io.BytesIO(buffer.read())
