import re
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.barcode import createBarcodeDrawing

# --- Dimensiones exactas solicitadas ---
# Tarjeta: 3.5 cm de ancho x 1.5 cm de alto
CARD_W = 3.5 * 72 / 2.54   # ~99.2126 pt
CARD_H = 1.5 * 72 / 2.54   # ~42.5197 pt

# Página A4: 21.0 cm x 29.7 cm
PAGE_W, PAGE_H = A4        # 595.28 pt x 841.89 pt

# Cuadrícula A4:
# 5 columnas * 3.5 cm = 17.5 cm (márgenes laterales: 1.75 cm cada uno)
# 18 filas * 1.5 cm = 27.0 cm (márgenes superior e inferior: 1.35 cm cada uno)
COLS = 5
ROWS = 18
CARDS_PER_PAGE = COLS * ROWS  # 90 tarjetas por página

MARGIN_X = (PAGE_W - COLS * CARD_W) / 2.0
MARGIN_Y = (PAGE_H - ROWS * CARD_H) / 2.0

MAX_TEXT_W = CARD_W - 8.0  # ~91.21 pt (margen de seguridad horizontal para texto)
MAX_BC_W = CARD_W - 10.0   # ~89.21 pt (zona de silencio y margen lateral para código de barras)

def balance_wrap_2(words, font_name, font_size, max_w):
    """Divide las palabras en 2 líneas equilibradas evitando números o palabras huérfanas."""
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
            # Penalización para evitar números o palabras muy cortas solas en la línea 2
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

def layout_barcode_card(desc, cve):
    """
    Calcula dinámicamente el tamaño de fuente, saltos de línea y dimensiones
    del código de barras y texto para que todo encaje vertical y horizontalmente
    dentro de la tarjeta de 3.5cm x 1.5cm sin desbordar.
    """
    title_font = 'Helvetica'
    words = desc.split()

    # 1. Probar si el título cabe en 1 sola línea (7.5 pt o 7.0 pt)
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

    # 2. Probar si el título se divide en 2 líneas equilibradas (7.0 pt bajando hasta 5.5 pt)
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

    # Respaldo para textos inusualmente largos
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

def clean_description(raw_desc):
    """Elimina prefijos como */ o * y espacios al inicio/final."""
    if raw_desc is None:
        return ""
    return re.sub(r'^[*/\s]+', '', str(raw_desc)).strip()

def generar_pdf_con_codigo_barras(excel_path='PATENTE.xlsx', output_pdf='tarjetas_medicamentos_con_codigo_barras.pdf'):
    print(f"Leyendo archivo {excel_path}...")
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    # Omitir cabecera
    items = []
    for r in rows[1:]:
        cve = str(r[0]).strip() if r[0] is not None else ""
        desc = clean_description(r[1])
        if cve or desc:
            items.append((cve, desc))

    total_items = len(items)
    total_pages = (total_items + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE
    print(f"Total de medicamentos a procesar: {total_items}")
    print(f"Total de páginas A4 estimadas: {total_pages} ({CARDS_PER_PAGE} tarjetas por página)")

    c = canvas.Canvas(output_pdf, pagesize=A4)
    item_idx = 0

    for page_num in range(1, total_pages + 1):
        for r_idx in range(ROWS):
            for c_idx in range(COLS):
                if item_idx >= total_items:
                    break
                cve, desc = items[item_idx]
                item_idx += 1

                x0 = MARGIN_X + c_idx * CARD_W
                y0 = MARGIN_Y + (ROWS - 1 - r_idx) * CARD_H

                # Guía de corte: borde sutil gris claro (0.4 pt)
                c.setStrokeColorRGB(0.78, 0.78, 0.78)
                c.setLineWidth(0.4)
                c.rect(x0, y0, CARD_W, CARD_H)

                layout = layout_barcode_card(desc, cve)
                t_lines = layout['t_lines']
                t_fs = layout['t_fs']
                t_leading = layout['t_leading']
                bc_h = layout['bc_h']
                cve_fs = layout['cve_fs']
                gap1 = layout['gap1']
                gap2 = layout['gap2']
                total_h = layout['total_h']

                # Centrado vertical del bloque completo
                y_top = y0 + (CARD_H + total_h) / 2.0

                # 1. Título del medicamento
                c.setFillColorRGB(0.08, 0.08, 0.08)
                c.setFont('Helvetica', t_fs)
                y_first_baseline = y_top - 0.75 * t_fs
                for l_idx, line in enumerate(t_lines):
                    line_y = y_first_baseline - l_idx * t_leading
                    line_w = stringWidth(line, 'Helvetica', t_fs)
                    c.drawString(x0 + (CARD_W - line_w) / 2.0, line_y, line)

                y_last_baseline = y_first_baseline - (len(t_lines) - 1) * t_leading

                # 2. Código de barras (Code 128 vectorial)
                bc_y = y_last_baseline - 0.25 * t_fs - gap1 - bc_h
                bw = 0.40
                bc = createBarcodeDrawing('Code128', value=cve, barWidth=bw, barHeight=bc_h, humanReadable=False)
                # Ajuste de ancho de barras en caso de códigos extraordinariamente largos
                if bc.width > MAX_BC_W:
                    bw = bw * (MAX_BC_W / bc.width)
                    bc = createBarcodeDrawing('Code128', value=cve, barWidth=bw, barHeight=bc_h, humanReadable=False)

                bc_x = x0 + (CARD_W - bc.width) / 2.0
                bc.drawOn(c, bc_x, bc_y)

                # 3. Número CVEART en negrita debajo del código de barras
                y_cve_baseline = bc_y - gap2 - 0.75 * cve_fs
                c.setFont('Helvetica-Bold', cve_fs)
                cve_w = stringWidth(cve, 'Helvetica-Bold', cve_fs)
                c.drawString(x0 + (CARD_W - cve_w) / 2.0, y_cve_baseline, cve)

            if item_idx >= total_items:
                break

        c.showPage()
        print(f"Página {page_num}/{total_pages} generada.")

    c.save()
    print(f"\n¡PDF con códigos de barra generado exitosamente en: {output_pdf}!")

if __name__ == '__main__':
    generar_pdf_con_codigo_barras()
