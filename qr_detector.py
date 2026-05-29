from typing import Optional, Tuple
import cv2
import numpy as np

class QRZoneDetector:
    """Détecte strictement et efficacement une zone blanche rectangulaire/carrée."""

    @classmethod
    def detect_white_square(cls, image_path: str) -> Optional[Tuple[int, int, int, int]]:
        try:
            # Lecture forcée en 3 canaux (évite les surprises alpha)
            img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Impossible de lire l'image: {image_path}")

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # 1. Seuil strict pour isoler le blanc pur
            _, mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

            # 2. Nettoyage minimal des artefacts
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # 3. Extraction des contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            min_area = w * h * 0.01  # 1% minimum
            max_area = w * h * 0.6   # 60% maximum (évite de matcher le fond entier)
            best = None
            max_right = -1

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if not (min_area <= area <= max_area):
                    continue

                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect = bw / bh if bh > 0 else 0

                # ✅ Contraintes strictes : proche d'un carré
                if not (0.8 <= aspect <= 1.25):
                    continue

                # ✅ Remplissage strict (>75% de la bounding box)
                if area / (bw * bh) < 0.75:
                    continue

                # ✅ Luminosité moyenne stricte
                roi = gray[y:y+bh, x:x+bw]
                if np.mean(roi) < 200:
                    continue

                # ✅ Ratio de pixels blancs dans la bbox (>80%)
                if cv2.countNonZero(mask[y:y+bh, x:x+bw]) / (bw * bh) < 0.8:
                    continue

                right_edge = x + bw
                if right_edge > max_right:
                    max_right = right_edge
                    best = (x, y, bw, bh)

            return best

        except Exception as e:
            print(f"❌ Erreur détection QR zone: {e}")
            return None