"""PDF A4; a pré-visualização rasteriza este mesmo documento."""
import math
from datetime import date
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from .calendario_service import MONTHS, WEEKDAYS, month_weeks, year_data
from .feriados_service import holiday_map, HOLIDAY_COLOR

INK = '#142D45'
MUTED = '#597084'


def wrap(text, width, size):
    lines, current = [], ''
    for word in text.split():
        candidate = (current + ' ' + word).strip()
        if stringWidth(candidate, 'Helvetica', size) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = ''
            for char in word:
                if stringWidth(current + char, 'Helvetica', size) > width:
                    lines.append(current)
                    current = ''
                current += char
    if current:
        lines.append(current)
    return lines or ['']


def generate_pdf(store, year, path, orientation='Paisagem'):
    days, legend = year_data(store, year)
    holidays = holiday_map(store, year)
    sector = store.config['nome_setor']
    width, height = landscape(A4) if orientation == 'Paisagem' else A4
    c = canvas.Canvas(str(path), pagesize=(width, height))
    c.setTitle(f'Calendário anual de férias - {sector} - {year}')
    c.setAuthor(sector)
    margin, page = 30, 1
    sector_lines = wrap(sector, width - 2 * margin, 10)
    year_y = height - 72 - 12 * (len(sector_lines) - 1)

    def text(x, y, value, size=9, color=INK, bold=False):
        c.setFillColor(HexColor(color))
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        c.drawString(x, y, str(value))

    def header(continuation=False):
        c.setFillColor(HexColor(INK))
        c.rect(0, height - 8, width, 8, fill=1, stroke=0)
        text(margin, height - 38, 'CALENDÁRIO ANUAL DE FÉRIAS', 17, bold=True)
        for index, line in enumerate(sector_lines):
            text(margin, height - 56 - index * 12, line, 10, MUTED)
        text(margin, year_y, f'ANO: {year:04d}' + ('  |  Legenda (continuação)' if continuation else ''), 10, MUTED)

    def footer():
        c.setStrokeColor(HexColor('#D7E1E9'))
        c.line(margin, 28, width - margin, 28)
        text(margin, 16, 'Vermelho/negrito: feriado. Faixas: férias. Contagem em dias corridos.', 7, MUTED)
        text(width - margin - 45, 16, f'Página {page}', 7, MUTED)

    header()
    cols = 4 if orientation == 'Paisagem' else 3
    rows = 12 // cols
    gap = 10
    top = year_y - 20
    bottom = 125 if orientation == 'Paisagem' else 162
    box_w = (width - 2 * margin - gap * (cols - 1)) / cols
    box_h = (top - bottom - gap * (rows - 1)) / rows
    for month in range(1, 13):
        col, row = (month - 1) % cols, (month - 1) // cols
        x, y = margin + col * (box_w + gap), top - row * (box_h + gap)
        c.setFillColor(HexColor('#EDF3F7'))
        c.roundRect(x, y - 18, box_w, 18, 3, fill=1, stroke=0)
        text(x + 7, y - 12, MONTHS[month - 1], 8, bold=True)
        cw, ch = box_w / 7, (box_h - 33) / 6
        for d, label in enumerate(WEEKDAYS):
            text(x + d * cw + 2, y - 28, label, 6, '#AC4950' if d in (0, 6) else MUTED)
        for r, week in enumerate(month_weeks(year, month)):
            for d, number in enumerate(week):
                if not number:
                    continue
                left, cell_top = x + d * cw, y - 33 - r * ch
                staff = days.get(date(year, month, number), [])
                c.setFillColor(HexColor('#F7F9FB'))
                c.rect(left + .6, cell_top - ch + .5, cw - 1.2, ch - 1, fill=1, stroke=0)
                if staff:
                    # Keep the numeral on white and all colors visible underneath.
                    stripe_h = max(2.5, ch * .28)
                    for idx, employee in enumerate(staff):
                        c.setFillColor(HexColor(employee['cor']))
                        c.rect(left + .8 + idx * (cw - 1.6) / len(staff), cell_top - ch + .8, (cw - 1.6) / len(staff), stripe_h, fill=1, stroke=0)
                holiday = date(year, month, number) in holidays
                text(left + 3, cell_top - min(8, ch * .6), number, min(7, ch * .46), HOLIDAY_COLOR if holiday else INK, bold=holiday)

    y = bottom - 17
    text(margin, y, 'LEGENDA DE FUNCIONÁRIOS', 9, bold=True)
    y -= 17
    if not legend:
        text(margin, y, 'Nenhum período de férias cadastrado para este ano.', 9, MUTED)
    legend_cols = 3 if orientation == 'Paisagem' else 2
    legend_w = (width - 2 * margin) / legend_cols
    for start in range(0, len(legend), legend_cols):
        group = legend[start:start + legend_cols]
        labels = [wrap(f"{e['nome']} | {e['matricula']}", legend_w - 24, 8) for e in group]
        row_h = max(len(lines) for lines in labels) * 11 + 9
        if y - row_h < 40:
            footer()
            c.showPage()
            page += 1
            header(True)
            y = year_y - 24
        for col, (employee, lines) in enumerate(zip(group, labels)):
            x = margin + col * legend_w
            c.setFillColor(HexColor(employee['cor']))
            c.setStrokeColor(HexColor('#B9C8D4'))
            c.rect(x, y - 2, 9, 9, fill=1, stroke=1)
            for index, line in enumerate(lines):
                text(x + 15, y - index * 11, line, 8)
        y -= row_h
    footer()
    c.save()
    return Path(path)
