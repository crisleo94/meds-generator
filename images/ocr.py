"""
Módulo de OCR in-memory para extracción de texto de imágenes usando Tesseract y Pillow.
Garantiza cero persistencia en disco: todo se procesa directamente en RAM.
"""

import io
import os
import shutil
from pathlib import Path
from django.conf import settings
from PIL import Image, ImageEnhance, ImageOps
import pytesseract


def configure_tesseract_path() -> bool:
    """Detecta y configura la ruta del ejecutable de Tesseract."""
    if shutil.which("tesseract"):
        return True

    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]

    for path in common_paths:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True

    return False


def configure_tessdata():
    """Configura la variable de entorno TESSDATA_PREFIX apuntando al tessdata del proyecto si existe."""
    base_dir = getattr(settings, 'BASE_DIR', Path(__file__).resolve().parent.parent)
    project_tessdata = Path(base_dir) / "tessdata"

    if project_tessdata.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(project_tessdata)


def preprocess_image(image: Image.Image, mode: str = "contrast") -> Image.Image:
    """
    Aplica técnicas de preprocesamiento para mejorar la tasa de acierto del OCR:
    - none: Imagen original
    - grayscale: Escala de grises simple
    - contrast: Escala de grises y aumento de contraste (2.0x)
    - threshold: Auto-contraste y binarización blanco y negro puro
    """
    if mode == "none":
        return image

    processed = image.convert("L")

    if mode == "grayscale":
        return processed

    if mode in ("contrast", "auto"):
        enhancer = ImageEnhance.Contrast(processed)
        return enhancer.enhance(2.0)

    if mode == "threshold":
        processed = ImageOps.autocontrast(processed)
        threshold = 140
        return processed.point(lambda p: 255 if p > threshold else 0)

    return processed


def extract_text_from_bytes(
    image_bytes: bytes,
    lang: str = "spa+eng",
    preprocess_mode: str = "contrast",
    psm: int = 3,
) -> dict:
    """
    Extrae texto de una imagen en memoria (bytes).
    Retorna un diccionario con el texto y metadatos estadísticos.
    """
    if not image_bytes:
        raise ValueError("El archivo de imagen está vacío.")

    if not configure_tesseract_path():
        raise RuntimeError(
            "No se encontró Tesseract OCR instalado en el sistema o en el PATH.\n"
            "Verifica la instalación en el servidor o contenedor."
        )

    configure_tessdata()

    # Validar idiomas solicitados
    try:
        available = pytesseract.get_languages()
    except Exception:
        available = []

    chosen_lang = lang
    if available:
        requested = lang.split("+")
        valid = [l for l in requested if l in available]
        if valid:
            chosen_lang = "+".join(valid)

    config_params = f"--psm {psm}"

    with Image.open(io.BytesIO(image_bytes)) as img:
        processed_img = preprocess_image(img, mode=preprocess_mode)
        raw_text = pytesseract.image_to_string(processed_img, lang=chosen_lang, config=config_params)

    text = raw_text.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    return {
        "text": text,
        "char_count": len(text),
        "word_count": len(text.split()),
        "line_count": len(lines),
        "lang": chosen_lang,
        "preprocess_mode": preprocess_mode,
        "psm": psm,
    }
