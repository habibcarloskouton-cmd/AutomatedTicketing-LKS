import io
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import qrcode
from PIL import Image, ImageDraw, ImageFont
from constants import TEMPLATE_DIR
from qr_detector import QRZoneDetector

class TicketGenerator:
    """Génération des tickets avec QR Code et personnalisation"""

    DEFAULT_SIZE = (600, 300)
    QR_PADDING_RATIO = 0.1
    DEFAULT_QR_POS = (420, 75)
    DEFAULT_QR_SIZE = (150, 150)

    def __init__(self):
        self.templates: Dict[str, str] = {}
        self.custom_template: Optional[str] = None
        self.qr_zone: Optional[Tuple[int, int, int, int]] = None
        self._initialize_templates()

    def _initialize_templates(self) -> None:
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        colors = {"Standard": "#fbce05", "VIP": "#0040ff", "VVIP": "#04ff00"}

        for ticket_type, color in colors.items():
            filename = TEMPLATE_DIR / f"template_{ticket_type.lower()}.jpg"
            if not filename.exists():
                self._create_template_image(filename, color, ticket_type)
            self.templates[ticket_type] = str(filename)

    def _create_template_image(self, filename: Path, color: str, ticket_type: str) -> None:
        img = Image.new('RGB', self.DEFAULT_SIZE, color=color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, 590, 290], outline="black", width=2)
        text_color = "white" if ticket_type == "VVIP" else "black"
        draw.text((50, 50), f"Billet {ticket_type}", fill=text_color)
        draw.text((50, 100), "Event Name Placeholder", fill=text_color)
        draw.rectangle([420, 75, 570, 225], fill="white", outline="gray")
        img.save(filename)

    def load_custom_template(self, file_path: str) -> Tuple[bool, str]:
        try:
            if not Path(file_path).exists():
                return False, "Fichier non trouvé"

            img = Image.open(file_path)
            img.verify()
            Image.open(file_path)

            qr_zone = QRZoneDetector.detect_white_square(file_path)
            if qr_zone is None:
                return False, "Aucun carré blanc détecté. Ajoutez une zone blanche pour le QR Code."

            self.custom_template = str(Path(file_path).resolve())
            self.qr_zone = qr_zone
            x, y, w, h = qr_zone
            return True, f"Zone détectée: ({x}, {y}), taille {w}x{h}px"

        except Exception as e:
            return False, f"Erreur: {type(e).__name__}: {str(e)}"

    def _get_template_path(self, ticket_type: str) -> str:
        if self.custom_template and Path(self.custom_template).exists():
            return self.custom_template
        return self.templates.get(ticket_type, self.templates["Standard"])

    def _create_qr_code(self, participant: Dict[str, Any], event_info: Dict[str, str]) -> Image.Image:
        qr_data = (
            f"ID:{participant.get('Code', '000')}|"
            f"Nom:{participant.get('Nom', 'Inconnu')}|"
            f"Event:{event_info['nom']}:LCS2026_PROTOTYPE"
        )
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(qr_data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    def _position_qr(self, qr_img: Image.Image, qr_zone: Optional[Tuple]) -> Tuple[Image.Image, int, int]:
        if qr_zone:
            x, y, w, h = qr_zone
            square_side = min(w, h)
            padding = int(square_side * self.QR_PADDING_RATIO)
            qr_size = max(64, square_side - (2 * padding))
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
            return qr_img, x + padding, y + padding
        qr_img = qr_img.resize(self.DEFAULT_QR_SIZE, Image.Resampling.LANCZOS)
        return qr_img, self.DEFAULT_QR_POS[0], self.DEFAULT_QR_POS[1]

    def _add_participant_text(self, ticket_img: Image.Image, participant: Dict[str, Any]) -> None:
        draw = ImageDraw.Draw(ticket_img)
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except IOError:
            font = ImageFont.load_default()
            font_small = font

        draw.text((50, 150), f"Participant: {participant.get('Nom', 'N/A')}", fill="black", font=font)
        draw.text((50, 180), f"Email: {participant.get('Email', 'N/A')}", fill="gray", font=font_small)

    def generate_ticket_image(self, participant: Dict[str, Any], event_info: Dict[str, str], ticket_type: str = "Standard") -> Tuple[Optional[io.BytesIO], Optional[str]]:
        try:
            template_path = self._get_template_path(ticket_type)
            ticket_img = Image.open(template_path).convert("RGBA")

            if self.custom_template and self.qr_zone is None:
                self.qr_zone = QRZoneDetector.detect_white_square(template_path)

            qr_img = self._create_qr_code(participant, event_info)
            current_qr_zone = self.qr_zone if self.custom_template else None
            qr_img, paste_x, paste_y = self._position_qr(qr_img, current_qr_zone)
            ticket_img.paste(qr_img, (paste_x, paste_y), qr_img)

            if not self.custom_template:
                self._add_participant_text(ticket_img, participant)

            buffer = io.BytesIO()
            ticket_img.convert("RGB").save(buffer, format='PNG')
            buffer.seek(0)
            filename = f"Ticket_{participant.get('Nom', 'User')}.png"
            return buffer, filename

        except Exception as e:
            print(f"❌ Erreur génération ticket: {e}")
            return None, None
