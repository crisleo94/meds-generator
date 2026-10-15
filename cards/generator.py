import io
import re
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.barcode import createBarcodeDrawing

# --- Dimensiones exactas ---
CARD_W = 3.5 * 72 / 2.54   # ~99.2126 pt (3.5 cm)
CARD_H = 1.5 * 72 / 2.54   # ~42.5197 pt (1.5 cm)

PAGE_W, PAGE_H = A4        # 595.28 pt x 841.89 pt

COLS = 5
ROWS = 18
CARDS_PER_PAGE = COLS * ROWS  # 90 tarjetas por página

MARGIN_X = (PAGE_W - COLS * CARD_W) / 2.0
MARGIN_Y = (PAGE_H - ROWS * CARD_H) / 2.0

MAX_TEXT_W = CARD_W - 8.0  # ~91.21 pt
MAX_TEXT_H = CARD_H - 5.0  # ~37.52 pt
MAX_BC_W = CARD_W - 10.0   # ~89.21 pt

def balance_wrap_2(words, font_name, font_size, max_w):
    """Divide las palabras en 2 líneas equilibradas evitando palabras o números huérfanos."""
    n = len(words)
    best_split = None
    min_cost = float('inf')
    for i in range(1, n):
        l1 = ' '.join(words[:i])
        l2 = ' '.join(words[i:])
        w1 = stringWidth(l1, font_name, font_size)
        w2 = stringWidth(l2, font_name, font_size)
        if w1 <= max_w and w2 <= max_w:
            diff = abs(w1 - w2)
            cost = diff
            if len(words[i:]) == 1:
                cost += 40.0
                if len(words[i:][0]) <= 3:
                    cost += 100.0
            if len(words[:i]) == 1 and len(words[0]) <= 3:
                cost += 80.0
            if cost < min_cost:
                min_cost = cost
                best_split = [l1, l2]
    return best_split

def balance_wrap_3(words, font_name, font_size, max_w):
    """Divide las palabras en 3 líneas en caso de textos extremos."""
    n = len(words)
    best_split = None
    min_cost = float('inf')
    for i in range(1, n - 1):
        for j in range(i + 1, n):
            l1 = ' '.join(words[:i])
            l2 = ' '.join(words[i:j])
            l3 = ' '.join(words[j:])
            w1 = stringWidth(l1, font_name, font_size)
            w2 = stringWidth(l2, font_name, font_size)
            w3 = stringWidth(l3, font_name, font_size)
            if w1 <= max_w and w2 <= max_w and w3 <= max_w:
                cost = max(w1, w2, w3) - min(w1, w2, w3)
                if len(words[j:]) == 1 and len(words[j:][0]) <= 3:
                    cost += 100.0
                if cost < min_cost:
                    min_cost = cost
                    best_split = [l1, l2, l3]
    return best_split

def layout_card_numbers_only(desc, cve):
    """Layout para tarjetas sin código de barras (solo número en negrita)."""
    title_font = 'Helvetica'
    cve_font = 'Helvetica-Bold'
    words = desc.split()

    # 1. Una sola línea
    for fs in [8.0, 7.5, 7.0]:
        w = stringWidth(desc, title_font, fs)
        if w <= MAX_TEXT_W:
            cve_fs = min(fs - 1.8, 6.0)
            cve_w = stringWidth(cve, cve_font, cve_fs)
            if cve_w > MAX_TEXT_W:
                cve_fs *= (MAX_TEXT_W / cve_w)
            gap = 3.5
            h_total = fs + gap + cve_fs
            return {
                'title_font': title_font,
                'title_fs': fs,
                'title_leading': fs * 1.15,
                'title_lines': [desc],
                'cve_font': cve_font,
                'cve_fs': cve_fs,
                'gap': gap,
                'h_total': h_total
            }

    # 2. Dos líneas
    for fs in [8.0, 7.5, 7.0, 6.5, 6.0]:
        lines = balance_wrap_2(words, title_font, fs, MAX_TEXT_W)
        if lines:
            leading = fs * 1.15
            cve_fs = min(fs - 1.8, 5.8)
            cve_w = stringWidth(cve, cve_font, cve_fs)
            if cve_w > MAX_TEXT_W:
                cve_fs *= (MAX_TEXT_W / cve_w)
            gap = 2.8
            h_total = leading + fs + gap + cve_fs
            if h_total <= MAX_TEXT_H:
                return {
                    'title_font': title_font,
                    'title_fs': fs,
                    'title_leading': leading,
                    'title_lines': lines,
                    'cve_font': cve_font,
                    'cve_fs': cve_fs,
                    'gap': gap,
                    'h_total': h_total
                }

    # 3. Tres líneas
    for fs in [6.0, 5.5, 5.0]:
        lines = balance_wrap_3(words, title_font, fs, MAX_TEXT_W)
        if lines:
            leading = fs * 1.12
            cve_fs = min(fs - 1.2, 5.0)
            gap = 2.0
            h_total = 2 * leading + fs + gap + cve_fs
            return {
                'title_font': title_font,
                'title_fs': fs,
                'title_leading': leading,
                'title_lines': lines,
                'cve_font': cve_font,
                'cve_fs': cve_fs,
                'gap': gap,
                'h_total': h_total
            }

    return {
        'title_font': title_font,
        'title_fs': 5.0,
        'title_leading': 5.5,
        'title_lines': [desc[:len(desc)//2], desc[len(desc)//2:]],
        'cve_font': cve_font,
        'cve_fs': 4.5,
        'gap': 2.0,
        'h_total': 15.0
    }

def layout_barcode_card(desc, cve):
    """Layout para tarjetas con código de barras y número debajo."""
    title_font = 'Helvetica'
    words = desc.split()

    for fs in [7.5, 7.0]:
        w = stringWidth(desc, title_font, fs)
        if w <= MAX_TEXT_W:
            t_lines = [desc]
            t_fs = fs
            t_leading = fs * 1.15
            t_h = fs
            bc_h = 11.0
            cve_fs = 5.4
            gap1 = 2.8
            gap2 = 1.8
            total_h = t_h + gap1 + bc_h + gap2 + cve_fs
            return {
                't_lines': t_lines,
                't_fs': t_fs,
                't_leading': t_leading,
                'bc_h': bc_h,
                'cve_fs': cve_fs,
                'gap1': gap1,
                'gap2': gap2,
                'total_h': total_h
            }

    for fs in [7.0, 6.5, 6.0, 5.5]:
        lines = balance_wrap_2(words, title_font, fs, MAX_TEXT_W)
        if lines:
            t_lines = lines
            t_fs = fs
            t_leading = fs * 1.12
            t_h = t_leading + fs
            bc_h = 9.2
            cve_fs = 5.0
            gap1 = 2.0
            gap2 = 1.5
            total_h = t_h + gap1 + bc_h + gap2 + cve_fs
            return {
                't_lines': t_lines,
                't_fs': t_fs,
                't_leading': t_leading,
                'bc_h': bc_h,
                'cve_fs': cve_fs,
                'gap1': gap1,
                'gap2': gap2,
                'total_h': total_h
            }

    return {
        't_lines': [desc[:len(desc)//2], desc[len(desc)//2:]],
        't_fs': 5.0,
        't_leading': 5.5,
        'bc_h': 8.0,
        'cve_fs': 4.5,
        'gap1': 1.5,
        'gap2': 1.5,
        'total_h': 24.0
    }

def clean_value(raw_val, remove_symbols=True):
    if raw_val is None:
        return ""
    val_str = str(raw_val).strip()
    if remove_symbols:
        val_str = re.sub(r'^[*/\s]+', '', val_str).strip()
    return val_str

def extract_excel_info(file_path):
    """Lee el archivo Excel y devuelve las hojas y las columnas de la primera hoja."""
    wb = openpyxl.load_workbook(file_path, read_only=True)
    sheet_names = wb.sheetnames
    first_sheet = wb[sheet_names[0]]
    rows_iter = first_sheet.iter_rows(values_only=True)
    header_row = next(rows_iter, None)

    headers = []
    if header_row:
        for idx, h in enumerate(header_row):
            h_clean = str(h).strip() if h is not None else f"Columna_{idx+1}"
            headers.append(h_clean)

    # Contar filas aproximadas
    row_count = 0
    sample_rows = []
    for r in rows_iter:
        if any(cell is not None and str(cell).strip() != '' for cell in r):
            row_count += 1
            if len(sample_rows) < 5:
                sample_rows.append([str(c).strip() if c is not None else '' for c in r])

    wb.close()
    return {
        'sheets': sheet_names,
        'headers': headers,
        'row_count': row_count,
        'sample_rows': sample_rows
    }

def generate_pdf_buffer(file_path, title_col, code_col, with_barcode=True, clean_symbols=True, max_items=None):
    """
    Genera el PDF en memoria y devuelve (BytesIO_buffer, total_items, total_pages).
    """
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header_row = next(rows_iter, None)

    if not header_row:
        wb.close()
        raise ValueError("El archivo Excel está vacío o no contiene encabezados.")

    headers = [str(h).strip() if h is not None else '' for h in header_row]

    try:
        title_idx = headers.index(title_col)
    except ValueError:
        title_idx = 1 if len(headers) > 1 else 0

    try:
        code_idx = headers.index(code_col)
    except ValueError:
        code_idx = 0

    items = []
    for r in rows_iter:
        if r is None:
            continue
        raw_title = r[title_idx] if title_idx < len(r) else ''
        raw_code = r[code_idx] if code_idx < len(r) else ''

        title = clean_value(raw_title, remove_symbols=clean_symbols)
        code = str(raw_code).strip() if raw_code is not None else ''

        if title or code:
            items.append((title, code))
            if max_items and len(items) >= max_items:
                break

    wb.close()

    total_items = len(items)
    total_pages = (total_items + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
    if total_pages == 0:
        total_pages = 1

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    item_idx = 0
    for page_num in range(1, total_pages + 1):
        for r_idx in range(ROWS):
            for c_idx in range(COLS):
                if item_idx >= total_items:
                    break
                title, code = items[item_idx]
                item_idx += 1

                x0 = MARGIN_X + c_idx * CARD_W
                y0 = MARGIN_Y + (ROWS - 1 - r_idx) * CARD_H

                # Borde sutil gris claro para corte
                c.setStrokeColorRGB(0.78, 0.78, 0.78)
                c.setLineWidth(0.4)
                c.rect(x0, y0, CARD_W, CARD_H)

                if with_barcode and code:
                    # Modo Código de Barras
                    layout = layout_barcode_card(title, code)
                    t_lines = layout['t_lines']
                    t_fs = layout['t_fs']
                    t_leading = layout['t_leading']
                    bc_h = layout['bc_h']
                    cve_fs = layout['cve_fs']
                    gap1 = layout['gap1']
                    gap2 = layout['gap2']
                    total_h = layout['total_h']

                    y_top = y0 + (CARD_H + total_h) / 2.0

                    # Título
                    c.setFillColorRGB(0.08, 0.08, 0.08)
                    c.setFont('Helvetica', t_fs)
                    y_first_baseline = y_top - 0.75 * t_fs
                    for l_idx, line in enumerate(t_lines):
                        line_y = y_first_baseline - l_idx * t_leading
                        line_w = stringWidth(line, 'Helvetica', t_fs)
                        c.drawString(x0 + (CARD_W - line_w) / 2.0, line_y, line)

                    y_last_baseline = y_first_baseline - (len(t_lines) - 1) * t_leading

                    # Código de barras
                    bc_y = y_last_baseline - 0.25 * t_fs - gap1 - bc_h
                    bw = 0.40
                    bc = createBarcodeDrawing('Code128', value=code, barWidth=bw, barHeight=bc_h, humanReadable=False)
                    if bc.width > MAX_BC_W:
                        bw = bw * (MAX_BC_W / bc.width)
                        bc = createBarcodeDrawing('Code128', value=code, barWidth=bw, barHeight=bc_h, humanReadable=False)

                    bc_x = x0 + (CARD_W - bc.width) / 2.0
                    bc.drawOn(c, bc_x, bc_y)

                    # Número en negrita debajo
                    y_cve_baseline = bc_y - gap2 - 0.75 * cve_fs
                    c.setFont('Helvetica-Bold', cve_fs)
                    cve_w = stringWidth(code, 'Helvetica-Bold', cve_fs)
                    c.drawString(x0 + (CARD_W - cve_w) / 2.0, y_cve_baseline, code)

                else:
                    # Modo Solo Números
                    layout = layout_card_numbers_only(title, code)
                    h_total = layout['h_total']
                    t_fs = layout['title_fs']
                    t_leading = layout['title_leading']
                    t_lines = layout['title_lines']
                    cve_fs = layout['cve_fs']
                    gap = layout['gap']

                    y_top = y0 + (CARD_H + h_total) / 2.0
                    y_first_baseline = y_top - 0.75 * t_fs

                    c.setFillColorRGB(0.08, 0.08, 0.08)
                    c.setFont(layout['title_font'], t_fs)
                    for l_idx, line in enumerate(t_lines):
                        line_y = y_first_baseline - l_idx * t_leading
                        line_w = stringWidth(line, layout['title_font'], t_fs)
                        c.drawString(x0 + (CARD_W - line_w) / 2.0, line_y, line)

                    y_last_baseline = y_first_baseline - (len(t_lines) - 1) * t_leading
                    y_cve_baseline = y_last_baseline - 0.25 * t_fs - 0.75 * cve_fs - gap

                    c.setFont(layout['cve_font'], cve_fs)
                    cve_w = stringWidth(code, layout['cve_font'], cve_fs)
                    c.drawString(x0 + (CARD_W - cve_w) / 2.0, y_cve_baseline, code)

            if item_idx >= total_items:
                break

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer, total_items, total_pages
