import os
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from .widgets import BG, MUTED, label, button, ScrollFrame
from ..services.backup_service import create_backup, restore_backup


class DataView(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        label(self, 'Dados e backup', 24, True).pack(anchor='w')
        label(self, 'Seus dados ficam neste computador, em arquivos JSON.', color=MUTED).pack(anchor='w', pady=(4, 20))
        scroll = ScrollFrame(self)
        scroll.pack(fill='both', expand=True)
        settings = tk.Frame(scroll.inner, bg='white', padx=22, pady=20)
        settings.pack(fill='x', pady=(0, 15))
        label(settings, 'DADOS DO CALENDÁRIO', 15, True).pack(anchor='w')
        label(settings, 'Nome do setor', color=MUTED).pack(anchor='w', pady=(12, 4))
        self.sector = tk.StringVar(value=app.store.config['nome_setor'])
        ttk.Entry(settings, textvariable=self.sector).pack(fill='x')
        label(settings, 'Sigla do setor (opcional)', color=MUTED).pack(anchor='w', pady=(12, 4))
        self.acronym = tk.StringVar(value=app.store.config['sigla_setor'])
        ttk.Entry(settings, textvariable=self.acronym, width=26).pack(anchor='w')
        button(settings, 'Salvar dados do calendário', self.save_settings).pack(anchor='w', pady=(14, 0))
        for title, description, action, caption in [
            ('Armazenamento local', f'Pasta atual:\n{app.store.directory}\n\nfuncionarios.json · ferias.json · configuracoes.json · feriados.json\nAs alterações são salvas automaticamente.', self.open_folder, 'Abrir pasta de dados'),
            ('Fazer backup', 'Cria uma pasta datada com os quatro arquivos JSON.\nEscolha um pendrive ou outra pasta para transportar os dados.', self.backup, 'Fazer backup'),
            ('Restaurar backup', 'Substitui os dados atuais por um backup validado.\nUma cópia de segurança dos dados atuais é criada antes da restauração.', self.restore, 'Restaurar backup'),
        ]:
            card = tk.Frame(scroll.inner, bg='white', padx=22, pady=20)
            card.pack(fill='x', pady=(0, 15))
            label(card, title, 15, True).pack(anchor='w')
            label(card, description, color=MUTED, justify='left', wraplength=750).pack(anchor='w', pady=12)
            button(card, caption, action).pack(anchor='w')

    def open_folder(self):
        self.app.safe(lambda: os.startfile(str(self.app.store.directory)))

    def save_settings(self):
        def save():
            self.app.store.configure(nome_setor=self.sector.get().strip(), sigla_setor=self.acronym.get().strip())
            self.app.update_identity()
            self.app.notify('Dados do calendário salvos. O nome aparecerá no calendário, na prévia e no PDF.')
        self.app.safe(save)

    def backup(self):
        destination = filedialog.askdirectory(parent=self, title='Escolha onde guardar o backup')
        if destination:
            def run():
                path = create_backup(self.app.store, destination)
                messagebox.showinfo('Backup concluído', f'Arquivos copiados para:\n{path}', parent=self)
            self.app.safe(run)

    def restore(self):
        source = filedialog.askdirectory(parent=self, title='Selecione a pasta do backup JSON (atual ou antigo)')
        if source and messagebox.askyesno('Restaurar backup', f'Substituir os dados atuais pelo backup desta pasta?\n\n{source}\n\nUma cópia dos dados atuais será preservada.', parent=self):
            def run():
                safety = restore_backup(self.app.store, source)
                self.app.year = self.app.store.config['ano']
                self.app.update_identity()
                messagebox.showinfo('Restauração concluída', f'Dados restaurados.\nBackup dos dados anteriores:\n{safety}', parent=self)
                self.app.show('calendar')
                self.app.notify('Backup restaurado com sucesso.')
            self.app.safe(run)
