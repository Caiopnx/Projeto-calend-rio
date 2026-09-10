import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from .widgets import BG, MUTED, Dialog, label, button, table


class EmployeeDialog(Dialog):
    def __init__(self, app, employee=None):
        super().__init__(app, 'Editar funcionário' if employee else 'Novo funcionário', height=605)
        self.employee = employee or {}
        self.fields = {key: self.field(title, self.employee.get(key, '')) for key, title in [('nome', 'Nome completo'), ('matricula', 'Matrícula'), ('setor', 'Setor'), ('cargo', 'Cargo')]}
        self.color = self.employee.get('cor', '#176BCE')
        row = tk.Frame(self.body, bg='white')
        row.pack(fill='x', pady=17)
        self.swatch = tk.Label(row, text='     ', bg=self.color, relief='solid', bd=1)
        self.swatch.pack(side='left', padx=(0, 10))
        button(row, 'Escolher cor', self.pick).pack(side='left')
        self.active = tk.BooleanVar(value=self.employee.get('ativo', True))
        ttk.Checkbutton(self.body, text='Funcionário ativo', variable=self.active).pack(anchor='w')
        label(self.body, 'A cor será aplicada a todas as férias deste funcionário.', 9, color=MUTED).pack(anchor='w', pady=14)
        actions = tk.Frame(self.body, bg='white')
        actions.pack(fill='x', side='bottom')
        button(actions, 'Salvar funcionário', self.save, True).pack(side='right')
        button(actions, 'Cancelar', self.destroy).pack(side='right', padx=8)

    def pick(self):
        color = colorchooser.askcolor(self.color, parent=self, title='Cor do funcionário')[1]
        if color:
            self.color = color
            self.swatch.configure(bg=color)

    def save(self):
        try:
            self.app.store.save_employee({**{k: v.get().strip() for k, v in self.fields.items()}, 'cor': self.color, 'ativo': self.active.get()}, self.employee.get('id'))
        except (ValueError, OSError) as exc:
            messagebox.showerror('Não foi possível salvar', str(exc), parent=self)
            return
        self.destroy()
        self.app.show('employees')
        self.app.notify('Funcionário salvo. Calendário e legenda atualizados.')


class EmployeesView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        label(self, 'FUNCIONÁRIOS', 23, True).pack(anchor='w')
        label(self, 'Pessoas, setores e cores que identificam as férias no calendário.', color=MUTED).pack(anchor='w', pady=(4, 20))
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill='x')
        self.search = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.search, width=28).pack(side='left')
        label(toolbar, 'Pesquisar nome, matrícula, setor ou cargo', 9, color=MUTED).pack(side='left', padx=8)
        button(toolbar, '+ Novo funcionário', lambda: EmployeeDialog(app), True).pack(side='right')
        actions = tk.Frame(self, bg=BG)
        actions.pack(fill='x', pady=(12, 0))
        for text, fn in [('Editar', self.edit), ('Alterar cor', self.color), ('Excluir', self.delete)]:
            button(actions, text, fn).pack(side='left', padx=(0, 8))
        self.tree = table(self, [('nome', 'Nome completo', 240), ('matricula', 'Matrícula', 110), ('setor', 'Setor', 150), ('cargo', 'Cargo', 150), ('cor', 'Cor', 100), ('ativo', 'Situação', 85)])
        self.tree.bind('<Double-1>', lambda e: self.edit())
        self.search.trace_add('write', lambda *_: self.refresh())
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        query = self.search.get().casefold()
        for e in sorted(self.app.store.employees, key=lambda e: e['nome'].casefold()):
            if query not in ' '.join(str(e[k]) for k in ('nome', 'matricula', 'setor', 'cargo')).casefold():
                continue
            self.tree.insert('', 'end', iid=str(e['id']), values=(e['nome'], e['matricula'], e['setor'], e['cargo'], e['cor'], 'Ativo' if e['ativo'] else 'Inativo'))

    def selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo('Selecione um funcionário', 'Clique em uma linha da lista.', parent=self)
            return None
        return next(e for e in self.app.store.employees if e['id'] == int(selection[0]))

    def edit(self):
        if (employee := self.selected()):
            EmployeeDialog(self.app, employee)

    def color(self):
        if not (employee := self.selected()):
            return
        color = colorchooser.askcolor(employee['cor'], parent=self, title='Alterar cor')[1]
        if color:
            def save():
                self.app.store.save_employee(dict(employee, cor=color), employee['id'])
                self.refresh()
                self.app.notify('Cor atualizada em todos os períodos de férias.')
            self.app.safe(save)

    def delete(self):
        if not (employee := self.selected()):
            return
        count = sum(v['funcionario_id'] == employee['id'] for v in self.app.store.vacations)
        if messagebox.askyesno('Excluir funcionário', f"Excluir {employee['nome']}?\n\nOs {count} períodos de férias vinculados também serão excluídos.\nEsta ação não pode ser desfeita sem um backup.", parent=self):
            def remove():
                self.app.store.delete_employee(employee['id'])
                self.refresh()
                self.app.notify('Funcionário e períodos vinculados excluídos.')
            self.app.safe(remove)
