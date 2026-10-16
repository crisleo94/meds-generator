import os
import time
import uuid
import base64
from pathlib import Path
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from .generator import extract_excel_info, generate_pdf_buffer, clean_value
from .sorter import clean_and_sort_lines
from .normalizer import normalize_excel_columns
import pymupdf

UPLOAD_DIR = settings.MEDIA_ROOT / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def purge_old_uploads(max_age_seconds=1800):
    """Elimina archivos temporales subidos hace más de 30 minutos."""
    now = time.time()
    try:
        for f in UPLOAD_DIR.glob('*.*'):
            if f.is_file() and (now - f.stat().st_mtime > max_age_seconds):
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception:
        pass

def index(request):
    """Página principal con diseño oscuro y soporte para HTMX y 3 pestañas."""
    purge_old_uploads()
    active_tab = request.GET.get('tab', 'cards')
    return render(request, 'cards/index.html', {'active_tab': active_tab})

# ==============================================================================
# HERRAMIENTA 1: IMPRESIÓN DE TARJETAS
# ==============================================================================

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
    default_col1 = headers[0]
    default_col2 = headers[1] if len(headers) > 1 else headers[0]

    for h in headers:
        h_upper = h.upper()
        if any(term in h_upper for term in ['DESC', 'NOM', 'PRODUCTO', 'ARTICULO', 'MEDICAMENTO']):
            default_col1 = h
        if any(term in h_upper for term in ['CVE', 'COD', 'BARR', 'EAN', 'UPC', 'ID', 'SKU']):
            default_col2 = h

    context = {
        'file_id': file_id,
        'filename': file.name,
        'headers': headers,
        'row_count': info['row_count'],
        'default_col1': default_col1,
        'default_col2': default_col2,
        'sheets': info['sheets']
    }
    return render(request, 'cards/partials/config_form.html', context)

def preview_cards(request):
    """Genera una vista previa en tiempo real de las primeras tarjetas (1 o 2 columnas)."""
    if request.method != 'POST':
        return HttpResponse('')

    file_id = request.POST.get('file_id')
    num_cols = int(request.POST.get('num_cols', 2))
    col1 = request.POST.get('col1')
    col2 = request.POST.get('col2')
    card_style = request.POST.get('card_style', 'barcode')
    clean_symbols = request.POST.get('clean_symbols') == 'on'
    font_family = request.POST.get('font_family', 'Helvetica')
    font_size = request.POST.get('font_size', 'auto')
    font_color = request.POST.get('font_color', '#000000')

    saved_path = UPLOAD_DIR / f"{file_id}.xlsx"
    if not saved_path.exists():
        return HttpResponse('<div class="text-red-400 p-4 bg-red-950/40 rounded-lg">Archivo no encontrado. Por favor sube el archivo nuevamente.</div>')

    try:
        pdf_buffer, total_items, _ = generate_pdf_buffer(
            file_path=saved_path,
            col1=col1,
            col2=col2,
            num_cols=num_cols,
            card_style=card_style,
            clean_symbols=clean_symbols,
            max_items=15,
            font_family=font_family,
            font_size=font_size,
            font_color=font_color
        )

        doc = pymupdf.open(stream=pdf_buffer.getvalue(), filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        doc.close()

        context = {
            'img_base64': img_base64,
            'total_items': total_items,
            'num_cols': num_cols,
            'col1': col1,
            'col2': col2,
            'card_style': card_style,
            'font_family': font_family,
            'font_size': font_size,
            'font_color': font_color
        }
        return render(request, 'cards/partials/preview.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="text-red-400 p-4 bg-red-950/40 rounded-lg">Error generando vista previa: {str(e)}</div>')

def download_pdf(request):
    """Genera y descarga el archivo PDF final completo con tamaño A4."""
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)

    file_id = request.POST.get('file_id')
    num_cols = int(request.POST.get('num_cols', 2))
    col1 = request.POST.get('col1')
    col2 = request.POST.get('col2')
    card_style = request.POST.get('card_style', 'barcode')
    clean_symbols = request.POST.get('clean_symbols') == 'on'
    font_family = request.POST.get('font_family', 'Helvetica')
    font_size = request.POST.get('font_size', 'auto')
    font_color = request.POST.get('font_color', '#000000')

    saved_path = UPLOAD_DIR / f"{file_id}.xlsx"
    if not saved_path.exists():
        return HttpResponse('Archivo de origen expirado o no encontrado.', status=404)

    try:
        pdf_buffer, total_items, total_pages = generate_pdf_buffer(
            file_path=saved_path,
            col1=col1,
            col2=col2,
            num_cols=num_cols,
            card_style=card_style,
            clean_symbols=clean_symbols,
            font_family=font_family,
            font_size=font_size,
            font_color=font_color
        )

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        filename = f"tarjetas_{num_cols}cols_{card_style}_A4.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Limpieza efímera del archivo
        try:
            if saved_path.exists():
                saved_path.unlink()
        except Exception:
            pass

        return response
    except Exception as e:
        return HttpResponse(f'Error al generar el PDF: {str(e)}', status=500)

# ==============================================================================
# HERRAMIENTA 2: ORDENADOR DE LISTAS DE TEXTO (FLUJO n8n)
# ==============================================================================

def sort_list(request):
    """Limpia y ordena alfabéticamente una lista de texto en español."""
    if request.method != 'POST':
        return HttpResponse('')

    raw_text = request.POST.get('raw_text', '')
    remove_duplicates = request.POST.get('remove_duplicates') == 'on'

    result = clean_and_sort_lines(raw_text, remove_duplicates=remove_duplicates)
    return render(request, 'cards/partials/sorter_result.html', result)

def download_sorted_txt(request):
    """Descarga el texto limpio y ordenado como archivo .txt."""
    if request.method != 'POST':
        return HttpResponse('Método no permitido', status=405)

    sorted_text = request.POST.get('sorted_text', '')
    response = HttpResponse(sorted_text, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="lista_medicamentos_ordenada.txt"'
    return response

# ==============================================================================
# HERRAMIENTA 3: NORMALIZADOR DE EXCEL
# ==============================================================================

def upload_normalizer_excel(request):
    """Sube un Excel para ser normalizado y muestra las columnas detectadas para mapeo."""
    purge_old_uploads()
    if request.method != 'POST' or 'excel_file' not in request.FILES:
        return HttpResponse('<div class="p-4 text-red-400 bg-red-950/40 border border-red-800 rounded-lg">Por favor selecciona un archivo .xlsx válido.</div>')

    file = request.FILES['excel_file']
    if not file.name.lower().endswith(('.xlsx', '.xlsm')):
        return HttpResponse('<div class="p-4 text-red-400 bg-red-950/40 border border-red-800 rounded-lg">El archivo debe ser de formato Excel (.xlsx).</div>')

    file_id = str(uuid.uuid4())
    saved_filename = f"norm_{file_id}.xlsx"
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

    context = {
        'file_id': file_id,
        'filename': file.name,
        'headers': info['headers'],
        'row_count': info['row_count'],
        'sample_rows': info['sample_rows']
    }
    return render(request, 'cards/partials/normalizer_form.html', context)

def process_normalizer_excel(request):
    """Procesa y normaliza el Excel según las columnas seleccionadas."""
    if request.method != 'POST':
        return HttpResponse('')

    file_id = request.POST.get('file_id')
    selected_cols = request.POST.getlist('selected_cols')
    code_col = request.POST.get('code_col')
    if code_col == '__none__':
        code_col = None
    remove_duplicates = request.POST.get('remove_duplicates') == 'on'

    saved_path = UPLOAD_DIR / f"norm_{file_id}.xlsx"
    if not saved_path.exists():
        return HttpResponse('<div class="text-red-400 p-4 bg-red-950/40 rounded-lg">Archivo no encontrado. Sube el archivo nuevamente.</div>')

    if not selected_cols:
        return HttpResponse('<div class="text-amber-400 p-4 bg-amber-950/40 border border-amber-800 rounded-lg">Debes seleccionar al menos una columna para consolidar.</div>')

    try:
        res = normalize_excel_columns(
            file_path=saved_path,
            selected_cols=selected_cols,
            code_col=code_col,
            remove_duplicates=remove_duplicates
        )

        # Guardar el Excel normalizado generado temporalmente para permitir descarga
        out_filename = f"normalized_{file_id}.xlsx"
        out_path = UPLOAD_DIR / out_filename
        with open(out_path, 'wb') as f:
            f.write(res['buffer'].getvalue())

        context = {
            'file_id': file_id,
            'total_items': res['total_items'],
            'sample_items': res['sample_items'],
            'has_code': bool(code_col),
            'selected_cols': selected_cols
        }
        return render(request, 'cards/partials/normalizer_result.html', context)
    except Exception as e:
        return HttpResponse(f'<div class="text-red-400 p-4 bg-red-950/40 rounded-lg">Error normalizando Excel: {str(e)}</div>')

def download_normalized_excel(request, file_id):
    """Descarga el Excel normalizado resultante."""
    out_path = UPLOAD_DIR / f"normalized_{file_id}.xlsx"
    if not out_path.exists():
        return HttpResponse('Archivo expirado o no encontrado.', status=404)

    with open(out_path, 'rb') as f:
        data = f.read()

    # Limpieza efímera tras la descarga
    try:
        out_path.unlink()
        orig_path = UPLOAD_DIR / f"norm_{file_id}.xlsx"
        if orig_path.exists():
            orig_path.unlink()
    except Exception:
        pass

    response = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="medicamentos_normalizado.xlsx"'
    return response
