import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta
from .widgets import BG, MUTED, Dialog, label, button, table, ScrollFrame

MODES = {'30 dias consecutivos': (30,), '15 + 15 dias': (15, 15), '10 + 20 dias': (10, 20)}


def display_date(iso):
    value = date.fromisoformat(iso)
    return f'{value.day:02d}/{value.month:02d}/{value.year:04d}'


def parse_date(value):
    try:
        day, month, year = [int(x) for x in value.strip().split('/')]
        return date(year, month, day)
    except (ValueError, TypeError):
        raise ValueError('Use datas válidas no formato DD/MM/AAAA.') from None


class VacationDialog(Dialog):
    def __init__(self, app, request_id=None):
        super().__init__(app, 'Editar férias' if request_id else 'Cadastrar férias', width=570, height=620)
        container = self.body
        actions = tk.Frame(container, bg='white')
        actions.pack(side='bottom', fill='x', pady=(12, 0))
        scroll = ScrollFrame(container)
        scroll.pack(fill='both', expand=True)
        scroll.canvas.configure(bg='white')
        self.body = scroll.inner
        self.body.configure(bg='white')
        self.request_id = request_id
        entries = sorted([v for v in app.store.vacations if v['solicitacao'] == request_id], key=lambda v: v['periodo'])
        self.people = {f"{e['nome']} · {e['matricula']}" + ('' if e['ativo'] else ' (inativo)'): e['id'] for e in sorted(app.store.employees, key=lambda e: e['nome'].casefold()) if e['ativo'] or (entries and e['id'] == entries[0]['funcionario_id'])}
        label(self.body, 'Funcionário', color=MUTED).pack(anchor='w')
        self.person = tk.StringVar(value=next((name for name, eid in self.people.items() if entries and eid == entries[0]['funcionario_id']), ''))
        ttk.Combobox(self.body, textvariable=self.person, values=list(self.people), state='readonly').pack(fill='x', pady=(5, 15))
        durations = tuple((date.fromisoformat(v['fim']) - date.fromisoformat(v['inicio'])).days + 1 for v in entries)
        self.mode = tk.StringVar(value=next((name for name, values in MODES.items() if values == durations), '30 dias consecutivos'))
        choice = ttk.Combobox(self.body, textvariable=self.mode, values=list(MODES), state='readonly')
        choice.pack(fill='x')
        choice.bind('<<ComboboxSelected>>', lambda e: self.mode_changed())
        self.periods, self.frames = [], []
        for i in range(2):
            frame = tk.Frame(self.body, bg='white', pady=12)
            self.frames.append(frame)
            label(frame, f'PERÍODO {i + 1}', 10, True).pack(anchor='w')
            row = tk.Frame(frame, bg='white')
            row.pack(fill='x', pady=8)
            initial = tk.StringVar(value=display_date(entries[i]['inicio']) if len(entries) > i else '')
            final = tk.StringVar(value=display_date(entries[i]['fim']) if len(entries) > i else '')
            for caption, variable in [('Início (DD/MM/AAAA)', initial), ('Fim (DD/MM/AAAA)', final)]:
                col = tk.Frame(row, bg='white')
                col.pack(side='left', fill='x', expand=True, padx=(0, 10))
                label(col, caption, 9, color=MUTED).pack(anchor='w')
                ttk.Entry(col, textvariable=variable, width=18).pack(fill='x', pady=4)
            info = label(frame, 'Informe as datas.', 9, color=MUTED)
            info.pack(anchor='w')
            button(frame, 'Calcular data final', lambda n=i: self.auto_end(n)).pack(anchor='w', pady=(6, 0))
            self.periods.append((initial, final, info))
            initial.trace_add('write', lambda *_, n=i: self.count(n))
            final.trace_add('write', lambda *_, n=i: self.count(n))
        self.hint = label(self.body, 'Contagem inclusiva: o primeiro e o último dia contam.\nPeríodos podem atravessar meses e anos.', 9, color=MUTED, justify='left')
        self.hint.pack(side='bottom', anchor='w', pady=12)
        button(actions, 'Salvar férias', self.save, True).pack(side='right')
        button(actions, 'Cancelar', self.destroy).pack(side='right', padx=8)
        self.mode_changed()

    def mode_changed(self):
        for frame in self.frames:
            frame.pack_forget()
        self.frames[0].pack(fill='x')
        if len(MODES[self.mode.get()]) == 2:
            self.frames[1].pack(fill='x')
        for i in range(2):
            self.count(i)

    def count(self, index):
        initial, final, info = self.periods[index]
        try:
            days = (parse_date(final.get()) - parse_date(initial.get())).days + 1
            expected = MODES[self.mode.get()][min(index, len(MODES[self.mode.get()]) - 1)]
            info.configure(text=f'{days} dias corridos · esperado: {expected} dias', fg='#138168' if days == expected else '#B44242')
        except ValueError:
            info.configure(text='Informe duas datas válidas.', fg=MUTED)

    def auto_end(self, index):
        try:
            days = MODES[self.mode.get()][index]
            final = parse_date(self.periods[index][0].get()) + timedelta(days=days - 1)
            self.periods[index][1].set(display_date(final.isoformat()))
        except (ValueError, OverflowError) as exc:
            messagebox.showerror('Confira a data inicial', str(exc), parent=self)

    def save(self):
        try:
            count = len(MODES[self.mode.get()])
            periods = [(parse_date(a.get()), parse_date(b.get())) for a, b, _ in self.periods[:count]]
            self.app.store.save_vacation(self.people.get(self.person.get()), periods, self.request_id)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Não foi possível salvar férias', str(exc), parent=self)
            return
        self.destroy()
        self.app.show('vacations')
        self.app.notify('Férias salvas e calendário atualizado.')


class VacationsView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        label(self, 'FÉRIAS', 23, True).pack(anchor='w')
        label(self, 'Organize solicitações de 30 dias, 15 + 15 dias ou 10 + 20 dias.', color=MUTED).pack(anchor='w', pady=(4, 20))
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill='x')
        self.search = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.search, width=30).pack(side='left')
        label(toolbar, 'Pesquisar funcionário ou matrícula', 9, color=MUTED).pack(side='left', padx=8)
        button(toolbar, '+ Cadastrar férias', self.new, True).pack(side='right')
        actions = tk.Frame(self, bg=BG)
        actions.pack(fill='x', pady=(12, 0))
        button(actions, 'Editar solicitação', self.edit).pack(side='left')
        button(actions, 'Excluir solicitação', self.delete).pack(side='left', padx=8)
        self.tree = table(self, [('nome', 'Funcionário', 230), ('matricula', 'Matrícula', 90), ('periodo', 'Período', 80), ('inicio', 'Início', 105), ('fim', 'Fim', 105), ('dias', 'Dias corridos', 90)])
        self.tree.bind('<Double-1>', lambda e: self.edit())
        self.search.trace_add('write', lambda *_: self.refresh())
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        employees = {e['id']: e for e in self.app.store.employees}
        for v in sorted(self.app.store.vacations, key=lambda v: v['inicio']):
            e = employees[v['funcionario_id']]
            if self.search.get().casefold() not in (e['nome'] + ' ' + e['matricula']).casefold():
                continue
            days = (date.fromisoformat(v['fim']) - date.fromisoformat(v['inicio'])).days + 1
            self.tree.insert('', 'end', iid=str(v['id']), values=(e['nome'], e['matricula'], v['periodo'], display_date(v['inicio']), display_date(v['fim']), days))

    def selected(self):
        rows = self.tree.selection()
        if not rows:
            messagebox.showinfo('Selecione férias', 'Clique em um período na lista.', parent=self)
            return None
        return next(v['solicitacao'] for v in self.app.store.vacations if v['id'] == int(rows[0]))

    def new(self):
        if not any(e['ativo'] for e in self.app.store.employees):
            messagebox.showinfo('Cadastre um funcionário', 'É necessário ter um funcionário ativo para cadastrar férias.', parent=self)
            return
        VacationDialog(self.app)

    def edit(self):
        if (request_id := self.selected()):
            VacationDialog(self.app, request_id)

    def delete(self):
        if not (request_id := self.selected()):
            return
        if messagebox.askyesno('Excluir férias', 'Excluir esta solicitação completa?\nNas opções fracionadas, os dois períodos serão excluídos.', parent=self):
            def remove():
                self.app.store.delete_vacation(request_id)
                self.refresh()
                self.app.notify('Solicitação de férias excluída.')
            self.app.safe(remove)
