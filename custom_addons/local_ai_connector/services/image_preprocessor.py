# -*- coding: utf-8 -*-
"""
Pipeline de procesamiento de imagen, detección de tachones y corrección NLP
para la digitalización de documentos/recetas médicas.
"""
import io
import logging
import re

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    from PIL import Image, ImageEnhance, UnidentifiedImageError
except ImportError:
    Image = None

_logger = logging.getLogger(__name__)

# Diccionario estricto de mapeo directo para homologación de ingredientes/marcas
STRICT_DICTIONARY_MAP = {
    "westergiron": "WESTEPIRON",
    "amikazina": "AMIKACINA",
    "sefuroxima": "CEFUROXIMA",
    "parasetamol": "PARACETAMOL",
    "ibuprofeno": "IBUPROFENO",
    "ketorolako": "KETOROLACO",
}


def enhance_document_quality(binary_data):
    """Mejora la calidad de imagen aplicando binarización y reducción de ruido.
    
    Retorna bytes JPEG optimizados para OCR / LLM Vision.
    """
    if not binary_data:
        return binary_data

    if cv2 is not None and np is not None:
        try:
            nparr = np.frombuffer(binary_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                denoised = cv2.fastNlMeansDenoising(gray, h=10)
                _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                is_success, buffer = cv2.imencode(".jpg", thresh)
                if is_success:
                    return buffer.tobytes()
        except Exception as exc:
            _logger.warning("Fallo en procesamiento OpenCV: %s", exc)

    # Fallback con PIL si OpenCV no estuviera disponible o fallara
    if Image is not None:
        try:
            img = Image.open(io.BytesIO(binary_data)).convert("L")
            enhancer = ImageEnhance.Contrast(img)
            img_contrast = enhancer.enhance(1.8)
            buf = io.BytesIO()
            img_contrast.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception as exc:
            _logger.warning("Fallo en procesamiento PIL: %s", exc)

    return binary_data


def is_line_crossed_out(line_crop_bytes):
    """Evalúa si una región/renglón de imagen contiene tachones o rayones excesivos.
    
    Retorna True si la densidad de masa oscura o trazos horizontales indican tachón.
    """
    if cv2 is None or np is None or not line_crop_bytes:
        return False

    try:
        nparr = np.frombuffer(line_crop_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False

        total_pixels = img.size
        black_pixels = np.count_nonzero(img < 50)
        density = black_pixels / float(total_pixels) if total_pixels > 0 else 0

        # Análisis de contornos de trazado continuo
        contours, _ = cv2.findContours(255 - img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        long_strokes = 0
        for c in contours:
            _, _, w, h = cv2.boundingRect(c)
            if w > (img.shape[1] * 0.35) and h < (img.shape[0] * 0.25):
                long_strokes += 1

        return density > 0.60 or long_strokes >= 2
    except Exception as exc:
        _logger.warning("Error evaluando tachón: %s", exc)
        return False


def clean_and_normalize_substance(raw_text, known_substances=None):
    """Corrige errores ortográficos y aplica el diccionario estricto de homologación.
    
    Entrada: "westergiron" -> Salida: "WESTEPIRON".
    """
    if not raw_text:
        return ""

    text_clean = raw_text.strip()
    key_lower = text_clean.lower()

    # 1. Aplicación de reglas del diccionario estricto
    if key_lower in STRICT_DICTIONARY_MAP:
        return STRICT_DICTIONARY_MAP[key_lower]

    # Limpieza de caracteres raros / ruido de OCR
    cleaned = re.sub(r"[^\w\s\.-]", "", text_clean)

    # 2. Fuzzy matching heurístico simple si existe lista conocida
    if known_substances:
        for known in known_substances:
            if known and known.lower() == key_lower:
                return known.upper()

    return cleaned.upper()
