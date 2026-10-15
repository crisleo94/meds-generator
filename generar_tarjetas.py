import os
import re
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth

# --- Dimensiones exactas solicitadas ---
# Tarjeta: 3.5 cm de ancho x 1.5 cm de alto
CARD_W = 3.5 * 72 / 2.54   # ~99.2126 pt
CARD_H = 1.5 * 72 / 2.54   # ~42.5197 pt

# Página A4: 21.0 cm x 29.7 cm
PAGE_W, PAGE_H = A4        # 595.28 pt x 841.89 pt

# Cuadrícula A4:
# 5 columnas * 3.5 cm = 17.5 cm (márgenes laterales de 1.75 cm cada uno)
# 18 filas * 1.5 cm = 27.0 cm (márgenes superior e inferior de 1.35 cm cada uno)
COLS = 5
ROWS = 18
CARDS_PER_PAGE = COLS * ROWS  # 90 tarjetas por página

MARGIN_X = (PAGE_W - COLS * CARD_W) / 2.0
MARGIN_Y = (PAGE_H - ROWS * CARD_H) / 2.0

MAX_TEXT_W = CARD_W - 8.0  # 4 pt de margen interno a cada lado (~91.21 pt)
MAX_TEXT_H = CARD_H - 5.0  # Margen vertical interno de seguridad

def balance_wrap_2(words, font_name, font_size, max_w):
    """Divide las palabras en 2 líneas equilibradas evitando palabras huérfanas."""
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
            # Penalización para evitar números o palabras cortas solas en la línea 2
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
    """Divide las palabras en 3 líneas en caso de textos inusualmente largos."""
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

def layout_card(desc, cve):
    """
    Calcula dinámicamente la tipografía y saltos de línea para que
    el título sea lo más legible posible sin desbordar, y el CVEART
    quede en negrita, más pequeño y centrado debajo.
    """
    title_font = 'Helvetica'
    cve_font = 'Helvetica-Bold'
    words = desc.split()

    # 1. Probar si entra en 1 sola línea (fuentes de 8.0 a 7.0)
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

    # 2. Probar en 2 líneas equilibradas (fuentes de 8.0 bajando hasta 6.0)
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

    # 3. Probar en 3 líneas para textos extremos
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

    # Respaldo de seguridad
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

def clean_description(raw_desc):
    """Elimina prefijos como */ o * y espacios al inicio/final."""
    if raw_desc is None:
        return ""
    return re.sub(r'^[*/\s]+', '', str(raw_desc)).strip()

def generar_pdf(excel_path='PATENTE.xlsx', output_pdf='tarjetas_medicamentos.pdf'):
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

                # Guía de corte: borde sutil gris claro
                c.setStrokeColorRGB(0.78, 0.78, 0.78)
                c.setLineWidth(0.4)
                c.rect(x0, y0, CARD_W, CARD_H)

                layout = layout_card(desc, cve)
                h_total = layout['h_total']
                t_fs = layout['title_fs']
                t_leading = layout['title_leading']
                t_lines = layout['title_lines']
                cve_fs = layout['cve_fs']
                gap = layout['gap']

                # Centrado vertical
                y_top = y0 + (CARD_H + h_total) / 2.0
                y_first_baseline = y_top - 0.75 * t_fs

                # Título
                c.setFillColorRGB(0.08, 0.08, 0.08)
                c.setFont(layout['title_font'], t_fs)
                for l_idx, line in enumerate(t_lines):
                    line_y = y_first_baseline - l_idx * t_leading
                    line_w = stringWidth(line, layout['title_font'], t_fs)
                    line_x = x0 + (CARD_W - line_w) / 2.0
                    c.drawString(line_x, line_y, line)

                # CVEART en negrita debajo
                y_last_baseline = y_first_baseline - (len(t_lines) - 1) * t_leading
                y_cve_baseline = y_last_baseline - 0.25 * t_fs - 0.75 * cve_fs - gap

                c.setFont(layout['cve_font'], cve_fs)
                cve_w = stringWidth(cve, layout['cve_font'], cve_fs)
                cve_x = x0 + (CARD_W - cve_w) / 2.0
                c.drawString(cve_x, y_cve_baseline, cve)

            if item_idx >= total_items:
                break

        c.showPage()
        print(f"Página {page_num}/{total_pages} generada.")

    c.save()
    print(f"\n¡PDF generado exitosamente en: {output_pdf}!")

if __name__ == '__main__':
    generar_pdf()
