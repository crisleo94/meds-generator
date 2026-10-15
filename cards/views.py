import os
import uuid
import base64
from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .generator import extract_excel_info, generate_pdf_buffer, clean_value
import pymupdf

import time

UPLOAD_DIR = settings.MEDIA_ROOT / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def purge_old_uploads(max_age_seconds=1800):
    """Elimina archivos temporales subidos hace más de 30 minutos."""
    now = time.time()
    try:
        for f in UPLOAD_DIR.glob('*.xlsx'):
            if f.is_file() and (now - f.stat().st_mtime > max_age_seconds):
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception:
        pass

def index(request):
    """Página principal con diseño oscuro y soporte para HTMX."""
    purge_old_uploads()
    return render(request, 'cards/index.html')

def upload_excel(request):
    """Recibe el archivo Excel vía HTMX, extrae sus columnas y muestra el formulario de configuración."""
    purge_old_uploads()
    if request.method != 'POST' or 'excel_file' not in request.FILES:
        return HttpResponse('<div class="p-4 text-red-400 bg-red-950/40 border border-red-800 rounded-lg">Por favor selecciona un archivo .xlsx válido.</div>')

    file = request.FILES['excel_file']
    if not file.name.lower().endswith(('.xlsx', '.xlsm')):
        return HttpResponse('<div class="p-4 text-red-400 bg-red-950/40 border border-red-800 rounded-lg">El archivo debe ser de formato Excel (.xlsx).</div>')

    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}.xlsx"
    saved_path = UPLOAD_DIR / saved_filename

    with open(saved_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    try:
        info = extract_excel_info(saved_path)
    except Exception as e:
        if saved_path.exists():
            os.remove(saved_path)
        return HttpResponse(f'<div class="p-4 text-red-400 bg-red-950/40 border border-red-800 rounded-lg">Error al leer el archivo Excel: {str(e)}</div>')

    headers = info['headers']
    # Sugerir columnas por defecto inteligentemente
    default_title = headers[0]
    default_code = headers[0]

    for h in headers:
        h_upper = h.upper()
        if any(term in h_upper for term in ['DESC', 'NOM', 'PRODUCTO', 'ARTICULO', 'MEDICAMENTO']):
            default_title = h
        if any(term in h_upper for term in ['CVE', 'COD', 'BARR', 'EAN', 'UPC', 'ID', 'SKU']):
            default_code = h

    context = {
        'file_id': file_id,
        'filename': file.name,
        'headers': headers,
        'row_count': info['row_count'],
        'default_title': default_title,
        'default_code': default_code,
        'sheets': info['sheets']
    }
    return render(request, 'cards/partials/config_form.html', context)

def preview_cards(request):
    """Genera una vista previa en tiempo real de las primeras tarjetas según la configuración seleccionada."""
    if request.method != 'POST':
        return HttpResponse('')

    file_id = request.POST.get('file_id')
    title_col = request.POST.get('title_col')
    code_col = request.POST.get('code_col')
    barcode_mode = request.POST.get('barcode_mode', 'barcode')  # 'barcode' o 'numbers'
    clean_symbols = request.POST.get('clean_symbols') == 'on'

    saved_path = UPLOAD_DIR / f"{file_id}.xlsx"
    if not saved_path.exists():
        return HttpResponse('<div class="text-red-400">Archivo no encontrado. Por favor sube el archivo nuevamente.</div>')

    with_barcode = (barcode_mode == 'barcode')

    try:
        # Generar un PDF temporal en memoria solo con los primeros 10 elementos para vista previa instantánea
        pdf_buffer, total_items, _ = generate_pdf_buffer(
            file_path=saved_path,
            title_col=title_col,
            code_col=code_col,
            with_barcode=with_barcode,
            clean_symbols=clean_symbols,
            max_items=15
        )

        # Renderizar la primera página a imagen base64 usando PyMuPDF
        doc = pymupdf.open(stream=pdf_buffer.getvalue(), filetype="pdf")
        page = doc[0]
        # Recortar solo el área de las primeras tarjetas (para vista nítida)
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        doc.close()

        context = {
            'img_base64': img_base64,
            'total_items': total_items,
            'with_barcode': with_barcode,
            'title_col': title_col,
            'code_col': code_col
        }
        return render(request, 'cards/partials/preview.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="text-red-400 p-4 bg-red-950/40 rounded-lg">Error generando vista previa: {str(e)}</div>')

def download_pdf(request):
    """Genera y descarga el archivo PDF final completo con tamaño A4."""
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)

    file_id = request.POST.get('file_id')
    title_col = request.POST.get('title_col')
    code_col = request.POST.get('code_col')
    barcode_mode = request.POST.get('barcode_mode', 'barcode')
    clean_symbols = request.POST.get('clean_symbols') == 'on'

    saved_path = UPLOAD_DIR / f"{file_id}.xlsx"
    if not saved_path.exists():
        return HttpResponse('Archivo de origen expirado o no encontrado.', status=404)

    with_barcode = (barcode_mode == 'barcode')

    try:
        pdf_buffer, total_items, total_pages = generate_pdf_buffer(
            file_path=saved_path,
            title_col=title_col,
            code_col=code_col,
            with_barcode=with_barcode,
            clean_symbols=clean_symbols
        )

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"tarjetas_{'con_codigo_barras' if with_barcode else 'numeros'}_A4.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Limpieza efímera del archivo de origen una vez completada la generación
        try:
            if saved_path.exists():
                saved_path.unlink()
        except Exception:
            pass

        return response
    except Exception as e:
        return HttpResponse(f'Error al generar el PDF: {str(e)}', status=500)
