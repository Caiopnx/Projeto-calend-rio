import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from .widgets import BG, INK, MUTED, label, button, ScrollFrame
from ..services.calendario_service import MONTHS, WEEKDAYS, month_weeks, year_data
from ..services.feriados_service import holiday_map, HOLIDAY_COLOR


class CalendarView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        heading = tk.Frame(self, bg=BG)
        heading.pack(fill='x')
        label(heading, 'CALENDÁRIO ANUAL DE FÉRIAS', 19, True).pack(side='left')
        button(heading, 'Pré-visualizar impressão', app.preview, True).pack(side='right')
        self.subtitle = label(self, '', color=MUTED, wraplength=750, justify='left')
        self.subtitle.pack(anchor='w', pady=(3, 18))
        self.bind('<Configure>', lambda e: self.subtitle.configure(wraplength=max(250, e.width - 15)))
        toolbar = tk.Frame(self, bg='white', padx=15, pady=12)
        toolbar.pack(fill='x')
        label(toolbar, 'Ano', 10, True).pack(side='left', padx=(0, 8))
        self.year = tk.StringVar(value=str(app.year))
        spin = ttk.Spinbox(toolbar, from_=1, to=9999, textvariable=self.year, width=7, command=self.refresh)
        spin.pack(side='left')
        spin.bind('<Return>', lambda e: self.refresh())
        button(toolbar, 'Aplicar', self.refresh).pack(side='left', padx=8)
        self.month = tk.StringVar(value='Visão anual')
        combo = ttk.Combobox(toolbar, values=['Visão anual'] + list(MONTHS), textvariable=self.month, state='readonly', width=18)
        combo.pack(side='left', padx=12)
        combo.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        self.summary = label(self, '', 9, color=MUTED)
        self.summary.pack(anchor='w', pady=(10, 0))
        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill='both', expand=True, pady=(16, 0))
        self.refresh()

    def refresh(self):
        try:
            year = int(self.year.get())
            days, legend = year_data(self.app.store, year)
            self.holidays = holiday_map(self.app.store, year)
            if year != self.app.year:
                self.app.store.configure(ano=year)
                self.app.year = year
        except (ValueError, OSError) as exc:
            messagebox.showerror('Confira o ano', 'Informe um ano de 1 a 9999.\n' + str(exc), parent=self)
            return
        for widget in self.scroll.inner.winfo_children():
            widget.destroy()
        self.subtitle.configure(text=f"{self.app.store.config['nome_setor']}\nANO: {year:04d}")
        self.summary.configure(text=f'{len(legend)} funcionários com férias · {len(days)} dias com ausências')
        grid = tk.Frame(self.scroll.inner, bg=BG)
        grid.pack(fill='x')
        individual = self.month.get() != 'Visão anual'
        months = [MONTHS.index(self.month.get()) + 1] if individual else range(1, 13)
        cols = 1 if individual else 4
        for col in range(cols):
            grid.columnconfigure(col, weight=1, uniform='month')
        for index, month in enumerate(months):
            card = tk.Frame(grid, bg='white', padx=10, pady=10, highlightbackground='#E0E7EF', highlightthickness=1)
            card.grid(row=index // cols, column=index % cols, sticky='nsew', padx=(0, 9), pady=(0, 12))
            title = label(card, MONTHS[month - 1], 11, True)
            title.pack(anchor='w', pady=(0, 8))
            title.bind('<Button-1>', lambda e, m=month: self.open_month(m))
            canvas = tk.Canvas(card, bg='white', highlightthickness=0, height=390 if individual else 179)
            canvas.pack(fill='both', expand=True)
            canvas.bind('<Configure>', lambda e, c=canvas, m=month: self.draw_month(c, year, m, days, individual))
            canvas.bind('<Button-1>', lambda e, c=canvas: self.day_details(c, e, days))
        legend_frame = tk.Frame(self.scroll.inner, bg='white', padx=18, pady=16)
        legend_frame.pack(fill='x', padx=(0, 9), pady=(4, 10))
        label(legend_frame, 'LEGENDA', 10, True).pack(anchor='w')
        label(legend_frame, 'Número vermelho e em negrito: feriado em Volta Redonda / RJ.', 9, True, HOLIDAY_COLOR, wraplength=700, justify='left').pack(anchor='w', pady=(6, 0))
        label(legend_frame, 'Clique em um dia para consultar as pessoas de férias. Faixas mostram ausências simultâneas.', 9, color=MUTED).pack(anchor='w', pady=(4, 12))
        if not legend:
            label(legend_frame, 'Nenhum período neste ano. Cadastre funcionários e férias para iniciar o planejamento.', color=MUTED, wraplength=680, justify='left').pack(anchor='w')
        for employee in legend:
            row = tk.Frame(legend_frame, bg='white')
            row.pack(fill='x', pady=3)
            tk.Label(row, bg=employee['cor'], width=2, relief='solid', bd=1).pack(side='left', padx=(0, 9))
            label(row, f"{employee['nome']}  ·  {employee['matricula']}  ·  {employee['setor']}" + ('' if employee['ativo'] else '  ·  Inativo'), 10, wraplength=780, justify='left').pack(side='left')

    def open_month(self, month):
        self.month.set(MONTHS[month - 1])
        self.refresh()

    def draw_month(self, canvas, year, month, days, individual):
        canvas.delete('all')
        width, height = canvas.winfo_width(), canvas.winfo_height()
        cw, ch = width / 7, (height - 23) / 6
        canvas.cells = []
        for col, title in enumerate(WEEKDAYS):
            canvas.create_text((col + .5) * cw, 9, text=title, font=('Segoe UI', 7 if cw < 28 else 8), fill='#B65A62' if col in (0, 6) else MUTED)
        today = date.today()
        for row, week in enumerate(month_weeks(year, month)):
            for col, number in enumerate(week):
                if not number:
                    continue
                day = date(year, month, number)
                x, y = col * cw, 23 + row * ch
                staff = days.get(day, [])
                canvas.create_rectangle(x + 1, y + 1, x + cw - 1, y + ch - 1, fill='#F1F5F9' if staff else 'white', outline='#D4E0EC' if day == today else '#EFF3F7')
                for i, employee in enumerate(staff):
                    sw = (cw - 4) / len(staff)
                    canvas.create_rectangle(x + 2 + i * sw, y + ch - (10 if individual else 6), x + 2 + (i + 1) * sw, y + ch - 2, fill=employee['cor'], outline='')
                holiday = day in self.holidays
                canvas.create_text(x + cw / 2, y + (15 if individual else 9), text=number, fill=HOLIDAY_COLOR if holiday else INK, font=('Segoe UI', 12 if individual else 9, 'bold' if holiday or staff or day == today else 'normal'))
                if individual and staff:
                    canvas.create_text(x + cw / 2, y + 35, text=f'{len(staff)} de férias', fill=MUTED, font=('Segoe UI', 9))
                canvas.cells.append((x, y, x + cw, y + ch, day))

    def day_details(self, canvas, event, days):
        for x1, y1, x2, y2, day in getattr(canvas, 'cells', []):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                from .widgets import Dialog, ScrollFrame
                dialog = Dialog(self.app, f'{day.day:02d}/{day.month:02d}/{day.year:04d}', height=430)
                scroll = ScrollFrame(dialog.body)
                scroll.pack(fill='both', expand=True)
                staff = days.get(day, [])
                for holiday in self.holidays.get(day, []):
                    label(scroll.inner, f"{holiday['nome']}\nFeriado {holiday['tipo'].lower()}", bold=True, color=HOLIDAY_COLOR, wraplength=430, justify='left').pack(anchor='w', pady=8)
                if not staff:
                    label(scroll.inner, 'Nenhum funcionário de férias neste dia.').pack(anchor='w', pady=12)
                for employee in staff:
                    label(scroll.inner, f"● {employee['nome']}\nMatrícula {employee['matricula']} · {employee['setor']}", color=INK, wraplength=430, justify='left').pack(anchor='w', pady=8)
                return
