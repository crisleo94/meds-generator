"""
Módulo de conversión de imágenes in-memory utilizando FFmpeg y Pillow.
Garantiza cero persistencia en disco: procesamiento por tuberías (pipes) en RAM
o buffers temporales con eliminación inmediata.
"""

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image


FORMAT_CONFIG = {
    'webp': {
        'ext': 'webp',
        'mime': 'image/webp',
        'desc': 'WebP (Ultra ligero, ideal para web)',
        'pipe': True
    },
    'jpg': {
        'ext': 'jpg',
        'mime': 'image/jpeg',
        'desc': 'JPEG / JPG (Compatibilidad universal)',
        'pipe': True
    },
    'jpeg': {
        'ext': 'jpg',
        'mime': 'image/jpeg',
        'desc': 'JPEG / JPG (Compatibilidad universal)',
        'pipe': True
    },
    'png': {
        'ext': 'png',
        'mime': 'image/png',
        'desc': 'PNG (Sin pérdida, soporte transparencia)',
        'pipe': True
    },
    'avif': {
        'ext': 'avif',
        'mime': 'image/avif',
        'desc': 'AVIF (Compresión avanzada de última generación)',
        'pipe': False
    },
    'ico': {
        'ext': 'ico',
        'mime': 'image/x-icon',
        'desc': 'ICO (Ícono / Favicon para sitios web)',
        'pipe': False
    },
    'gif': {
        'ext': 'gif',
        'mime': 'image/gif',
        'desc': 'GIF (Imagen o animación)',
        'pipe': True
    },
    'bmp': {
        'ext': 'bmp',
        'mime': 'image/bmp',
        'desc': 'BMP (Formato bitmap sin compresión)',
        'pipe': True
    }
}


def get_ffmpeg_cmd() -> str:
    """Obtiene la ruta o comando para invocar FFmpeg."""
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    common_win_paths = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    ]

    for p in common_win_paths:
        if os.path.isfile(p):
            return p

    return "ffmpeg"


def convert_image_in_memory(
    image_bytes: bytes,
    target_format: str,
    quality: int = 85,
    max_dim: int | None = None,
    strip_metadata: bool = True
) -> dict:
    """
    Convierte una imagen de cualquier formato a otro en memoria.
    Retorna un diccionario con los bytes convertidos, MIME type, extensión y estadísticas.
    """
    fmt_key = target_format.lower().strip()
    if fmt_key not in FORMAT_CONFIG:
        raise ValueError(f"Formato no soportado: '{target_format}'. Formatos válidos: {list(FORMAT_CONFIG.keys())}")

    config = FORMAT_CONFIG[fmt_key]
    ffmpeg_bin = get_ffmpeg_cmd()

    # Caso especial: ICO (Se genera con Pillow para soportar múltiples resoluciones limpias)
    if fmt_key == 'ico':
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            # Si tiene transparencia o paleta, convertir a RGBA
            if pil_img.mode not in ('RGB', 'RGBA'):
                pil_img = pil_img.convert('RGBA')

            size = max_dim if (max_dim and max_dim in (16, 32, 48, 64, 128, 256)) else 256
            resized = pil_img.resize((size, size), Image.Resampling.LANCZOS)

            bio = io.BytesIO()
            resized.save(bio, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            output_bytes = bio.getvalue()

        orig_sz = len(image_bytes)
        conv_sz = len(output_bytes)
        reduction = round((1 - conv_sz / orig_sz) * 100, 1) if orig_sz > 0 else 0

        return {
            'bytes': output_bytes,
            'mime_type': config['mime'],
            'ext': config['ext'],
            'original_size': orig_sz,
            'converted_size': conv_sz,
            'reduction_percent': reduction,
            'format_name': config['desc'],
        }

    # Caso especial: AVIF con FFmpeg (el muxer AVIF requiere archivo buscable)
    if fmt_key == 'avif':
        with tempfile.NamedTemporaryFile(suffix='.avif', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [ffmpeg_bin, '-y', '-i', 'pipe:0']
            if max_dim and max_dim > 0:
                cmd += ['-vf', f'scale=min({max_dim}\\,iw):-1']
            if strip_metadata:
                cmd += ['-map_metadata', '-1']

            # libaom-av1: crf de 0 (lossless) a 63 (baja calidad)
            crf = int(63 - (quality * 63 / 100))
            cmd += ['-c:v', 'libaom-av1', '-crf', str(crf), '-still-picture', '1', tmp_path]

            proc = subprocess.run(cmd, input=image_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                err_msg = proc.stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"Error en FFmpeg al convertir a AVIF: {err_msg[:400]}")

            with open(tmp_path, 'rb') as f_out:
                output_bytes = f_out.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        orig_sz = len(image_bytes)
        conv_sz = len(output_bytes)
        reduction = round((1 - conv_sz / orig_sz) * 100, 1) if orig_sz > 0 else 0

        return {
            'bytes': output_bytes,
            'mime_type': config['mime'],
            'ext': config['ext'],
            'original_size': orig_sz,
            'converted_size': conv_sz,
            'reduction_percent': reduction,
            'format_name': config['desc'],
        }

    # Resto de formatos soportados por tubería estándar directa (pipe:0 -> pipe:1)
    cmd = [ffmpeg_bin, '-y', '-i', 'pipe:0']

    # Filtro de escalado proporcional
    if max_dim and max_dim > 0:
        cmd += ['-vf', f'scale=min({max_dim}\\,iw):-1']

    # Descartar metadatos EXIF si se solicita
    if strip_metadata:
        cmd += ['-map_metadata', '-1']

    # Opciones por formato
    if fmt_key == 'webp':
        cmd += ['-quality', str(quality), '-f', 'webp']
    elif fmt_key in ('jpg', 'jpeg'):
        # En MJPEG/JPEG qscale va de 1 (mejor) a 31 (peor)
        qscale = max(1, min(31, int(31 - (quality * 30 / 100))))
        cmd += ['-q:v', str(qscale), '-f', 'image2', '-c:v', 'mjpeg']
    elif fmt_key == 'png':
        cmd += ['-f', 'image2', '-c:v', 'png']
    elif fmt_key == 'gif':
        cmd += ['-f', 'gif']
    elif fmt_key == 'bmp':
        cmd += ['-f', 'image2', '-c:v', 'bmp']

    cmd.append('pipe:1')

    proc = subprocess.run(cmd, input=image_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err_msg = proc.stderr.decode('utf-8', errors='ignore')
        raise RuntimeError(f"Error de conversión en FFmpeg ({fmt_key}): {err_msg[:400]}")

    output_bytes = proc.stdout
    orig_sz = len(image_bytes)
    conv_sz = len(output_bytes)
    reduction = round((1 - conv_sz / orig_sz) * 100, 1) if orig_sz > 0 else 0

    return {
        'bytes': output_bytes,
        'mime_type': config['mime'],
        'ext': config['ext'],
        'original_size': orig_sz,
        'converted_size': conv_sz,
        'reduction_percent': reduction,
        'format_name': config['desc'],
    }
