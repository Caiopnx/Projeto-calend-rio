import tkinter as tk
from tkinter import ttk, messagebox
from .widgets import BG, MUTED, Dialog, label, button, table
from .ferias import parse_date, display_date
from ..services.feriados_service import TYPES, holidays_for_year


class HolidayDialog(Dialog):
    def __init__(self, app, year, selected=None):
        super().__init__(app, 'Editar feriado' if selected else 'Adicionar feriado', height=445)
        self.year, self.selected = year, selected
        item = selected or {}
        label(self.body, f'Ajuste válido somente para {year:04d}. O padrão dos outros anos será mantido.', 9, color=MUTED, wraplength=450, justify='left').pack(anchor='w')
        self.name = self.field('Nome do feriado', item.get('nome', ''))
        self.day = self.field('Data (DD/MM/AAAA)', display_date(item['data']) if item else f'01/01/{year:04d}')
        label(self.body, 'Tipo', color=MUTED).pack(anchor='w', pady=(12, 5))
        self.kind = tk.StringVar(value=item.get('tipo', 'Municipal'))
        ttk.Combobox(self.body, textvariable=self.kind, values=TYPES, state='readonly').pack(fill='x')
        actions = tk.Frame(self.body, bg='white')
        actions.pack(side='bottom', fill='x')
        button(actions, 'Salvar feriado', self.save, True).pack(side='right')
        button(actions, 'Cancelar', self.destroy).pack(side='right', padx=8)

    def save(self):
        try:
            self.app.store.save_holiday(dict(nome=self.name.get().strip(), data=parse_date(self.day.get()).isoformat(), tipo=self.kind.get()), self.year, self.selected)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Confira o feriado', str(exc), parent=self)
            return
        self.destroy()
        self.app.show('holidays')
        self.app.notify('Feriado salvo. Calendário e impressão atualizados.')


class HolidaysView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        label(self, 'FERIADOS', 23, True).pack(anchor='w')
        label(self, 'Calendário civil de Volta Redonda / RJ · sem pontos facultativos.', color=MUTED).pack(anchor='w', pady=(4, 16))
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill='x')
        label(toolbar, 'Ano').pack(side='left', padx=(0, 8))
        self.year = tk.StringVar(value=str(app.year))
        spin = ttk.Spinbox(toolbar, from_=1, to=9999, textvariable=self.year, width=7, command=self.refresh)
        spin.pack(side='left')
        spin.bind('<Return>', lambda e: self.refresh())
        button(toolbar, 'Aplicar', self.refresh).pack(side='left', padx=8)
        self.kind = tk.StringVar(value='Todos')
        combo = ttk.Combobox(toolbar, values=('Todos',) + TYPES, textvariable=self.kind, state='readonly', width=13)
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        button(toolbar, '+ Adicionar feriado', self.new, True).pack(side='right')
        actions = tk.Frame(self, bg=BG)
        actions.pack(fill='x', pady=(12, 0))
        button(actions, 'Editar neste ano', self.edit).pack(side='left')
        button(actions, 'Remover neste ano', self.delete).pack(side='left', padx=8)
        button(actions, 'Restaurar padrões do ano', self.reset).pack(side='left')
        self.info = label(self, '', 9, color=MUTED, wraplength=750, justify='left')
        self.info.pack(anchor='w', pady=(10, 0))
        self.tree = table(self, [('data', 'Data', 110), ('nome', 'Nome do feriado', 410), ('tipo', 'Tipo', 110), ('origem', 'Origem', 160)])
        self.tree.bind('<Double-1>', lambda e: self.edit())
        self.rows = {}
        self.refresh()

    def refresh(self):
        try:
            year = int(self.year.get())
            entries = holidays_for_year(self.app.store, year)
            if year != self.app.year:
                self.app.store.configure(ano=year)
                self.app.year = year
        except (ValueError, OSError) as exc:
            messagebox.showerror('Confira o ano', str(exc), parent=self)
            return False
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for item in entries:
            if self.kind.get() not in ('Todos', item['tipo']):
                continue
            iid = item['origem'] + ':' + item['id']
            self.rows[iid] = item
            origin = 'Personalizado' if item['origem'] == 'personalizado' else ('Ajustado neste ano' if item['ajustado'] else 'Padrão')
            self.tree.insert('', 'end', iid=iid, values=(display_date(item['data']), item['nome'], item['tipo'], origin))
        self.info.configure(text=f'{len(self.rows)} feriados exibidos · Edições e remoções valem só para {year:04d}. Restaurar padrões desfaz ajustes, mantendo os feriados personalizados.')
        return True

    def selected(self):
        if not self.tree.selection():
            messagebox.showinfo('Selecione um feriado', 'Clique em uma linha da lista.', parent=self)
            return None
        return self.rows[self.tree.selection()[0]]

    def new(self):
        if self.refresh():
            HolidayDialog(self.app, self.app.year)

    def edit(self):
        if (item := self.selected()):
            HolidayDialog(self.app, self.app.year, item)

    def delete(self):
        if (item := self.selected()) and messagebox.askyesno('Remover feriado', f"Remover {item['nome']} do calendário de {self.app.year:04d}?\nO padrão dos outros anos não será alterado.", parent=self):
            def remove():
                self.app.store.delete_holiday(item, self.app.year)
                self.refresh()
            self.app.safe(remove)

    def reset(self):
        if messagebox.askyesno('Restaurar padrões', f'Desfazer as edições e remoções dos feriados padrão de {self.app.year:04d}?\nOs feriados personalizados serão mantidos.', parent=self):
            def reset():
                self.app.store.reset_holidays(self.app.year)
                self.refresh()
            self.app.safe(reset)
