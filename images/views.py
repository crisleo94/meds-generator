import base64
import os
from pathlib import Path
from django.http import HttpResponse
from django.shortcuts import render
from .ocr import extract_text_from_bytes
from .converter import convert_image_in_memory, FORMAT_CONFIG


def ocr_extract(request):
    """Extrae texto de una imagen en memoria y devuelve el resultado vía HTMX."""
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)

    image_file = request.FILES.get('image')
    if not image_file:
        return HttpResponse(
            '<div class="p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-sm">'
            'Por favor selecciona o arrastra un archivo de imagen válido.'
            '</div>'
        )

    lang = request.POST.get('lang', 'spa+eng')
    preprocess_mode = request.POST.get('preprocess', 'contrast')
    psm_val = request.POST.get('psm', '3')
    try:
        psm = int(psm_val)
    except ValueError:
        psm = 3

    try:
        image_bytes = image_file.read()
        ocr_data = extract_text_from_bytes(
            image_bytes=image_bytes,
            lang=lang,
            preprocess_mode=preprocess_mode,
            psm=psm
        )

        context = {
            'filename': image_file.name,
            'filesize_kb': round(len(image_bytes) / 1024, 1),
            'text': ocr_data['text'],
            'char_count': ocr_data['char_count'],
            'word_count': ocr_data['word_count'],
            'line_count': ocr_data['line_count'],
            'lang': ocr_data['lang'],
            'preprocess_mode': ocr_data['preprocess_mode'],
        }
        return render(request, 'images/partials/ocr_result.html', context)
    except Exception as exc:
        return HttpResponse(
            f'<div class="p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-sm">'
            f'<strong>Error en el proceso OCR:</strong> {str(exc)}'
            f'</div>'
        )


def convert_image(request):
    """
    Convierte una imagen a otro formato usando FFmpeg/Pillow en memoria.
    Soporta descarga directa o previsualización interactiva con HTMX.
    """
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)

    image_file = request.FILES.get('image')
    if not image_file:
        return HttpResponse(
            '<div class="p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-sm">'
            'Por favor selecciona o arrastra una imagen para convertir.'
            '</div>'
        )

    target_format = request.POST.get('target_format', 'webp').lower().strip()
    quality_raw = request.POST.get('quality', '85')
    try:
        quality = max(10, min(100, int(quality_raw)))
    except ValueError:
        quality = 85

    max_dim_raw = request.POST.get('max_dim', 'original').strip()
    max_dim = None
    if max_dim_raw and max_dim_raw.lower() != 'original':
        try:
            max_dim = int(max_dim_raw)
        except ValueError:
            max_dim = None

    strip_metadata = request.POST.get('strip_metadata') == 'on'
    is_direct_download = request.POST.get('direct_download') == '1' or request.GET.get('download') == '1'

    try:
        image_bytes = image_file.read()
        res = convert_image_in_memory(
            image_bytes=image_bytes,
            target_format=target_format,
            quality=quality,
            max_dim=max_dim,
            strip_metadata=strip_metadata
        )

        stem = Path(image_file.name).stem or "imagen"
        out_filename = f"{stem}.{res['ext']}"

        # Descarga directa de archivo
        if is_direct_download:
            response = HttpResponse(res['bytes'], content_type=res['mime_type'])
            response['Content-Disposition'] = f'attachment; filename="{out_filename}"'
            return response

        # Respuesta HTMX con previsualización y botón de descarga directa
        b64_content = base64.b64encode(res['bytes']).decode('utf-8')
        data_uri = f"data:{res['mime_type']};base64,{b64_content}"

        context = {
            'orig_filename': image_file.name,
            'out_filename': out_filename,
            'orig_size_kb': round(res['original_size'] / 1024, 1),
            'conv_size_kb': round(res['converted_size'] / 1024, 1),
            'reduction_percent': res['reduction_percent'],
            'format_name': res['format_name'],
            'ext': res['ext'],
            'mime_type': res['mime_type'],
            'data_uri': data_uri,
            'b64_content': b64_content,
        }
        return render(request, 'images/partials/converter_result.html', context)

    except Exception as exc:
        return HttpResponse(
            f'<div class="p-4 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-sm">'
            f'<strong>Error al convertir la imagen:</strong> {str(exc)}'
            f'</div>'
        )
