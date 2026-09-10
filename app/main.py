import logging
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from .services.json_service import Store, data_directory
from .ui.widgets import BG, INK, MUTED, BLUE, label
from .ui.calendario import CalendarView
from .ui.funcionarios import EmployeesView
from .ui.ferias import VacationsView
from .ui.dashboard import DataView
from .ui.feriados import HolidaysView


def prepare_tk_paths():
    """Use caminhos Windows estendidos para a biblioteca Tcl/Tk empacotada."""
    if os.name == 'nt' and getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
        for variable, folder in [('TCL_LIBRARY', '_tcl_data'), ('TK_LIBRARY', '_tk_data')]:
            target = str(base / folder)
            if not target.startswith('\\\\?\\'):
                target = '\\\\?\\' + target
            os.environ[variable] = target


class Application(tk.Tk):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.year = store.config['ano']
        self.title('STMU | Calendário de Férias')
        icon = Path(__file__).parent / 'assets' / 'stmu.ico'
        if icon.exists():
            self.iconbitmap(default=str(icon))
        self.geometry('1380x890')
        self.minsize(1060, 650)
        self.configure(bg=BG)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.option_add('*Font', ('Segoe UI', 10))
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background=BG, foreground=INK)
        style.configure('TButton', padding=(12, 8), background='white', borderwidth=1, bordercolor='#D7E1EB', relief='flat')
        style.map('TButton', background=[('active', '#E6EFFA')])
        style.configure('Primary.TButton', background=BLUE, foreground='white', borderwidth=0)
        style.map('Primary.TButton', background=[('active', '#1255A3')], foreground=[('active', 'white')])
        style.configure('TEntry', padding=7, fieldbackground='white')
        style.configure('TCombobox', padding=6, fieldbackground='white')
        style.configure('Treeview', rowheight=38, fieldbackground='white', background='white', borderwidth=0)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), padding=10, background='#E8EFF6', relief='flat')
        style.map('Treeview', background=[('selected', '#D9E9FD')], foreground=[('selected', INK)])
        sidebar = tk.Frame(self, bg=INK, width=218)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        label(sidebar, 'STMU', 30, True, 'white').pack(anchor='w', padx=26, pady=(30, 0))
        label(sidebar, 'GESTÃO DE FÉRIAS', 9, color='#AFC5DB').pack(anchor='w', padx=26, pady=(0, 35))
        self.nav = {}
        for key, title in [('calendar', '▦  Calendário'), ('employees', '▤  Funcionários'), ('vacations', '◷  Férias'), ('holidays', '◇  Feriados'), ('data', '▣  Dados e backup')]:
            item = tk.Button(sidebar, text=title, anchor='w', bg=INK, fg='#D5E1EC', activebackground='#284763', activeforeground='white', relief='flat', bd=0, padx=21, pady=14, font=('Segoe UI', 11), cursor='hand2', command=lambda k=key: self.show(k))
            item.pack(fill='x', padx=12, pady=4)
            self.nav[key] = item
        label(sidebar, '●  Armazenamento local\nJSON · Sem conexão externa\n\nVersão 1.1.0', 9, color='#B2C8DC', justify='left').pack(side='bottom', anchor='w', padx=23, pady=25)
        main = tk.Frame(self, bg=BG)
        main.pack(side='left', fill='both', expand=True)
        header = tk.Frame(main, bg='white', height=53, padx=25)
        header.pack(fill='x')
        header.pack_propagate(False)
        label(header, 'PLANEJAMENTO DE PESSOAS', 9, True, MUTED).pack(side='left')
        self.organization = label(header, '', 9, color=MUTED)
        self.organization.pack(side='right')
        self.update_identity()
        self.status = label(main, 'Pronto · Alterações salvas automaticamente', 9, color=MUTED, anchor='w', padx=26, pady=10)
        self.status.pack(side='bottom', fill='x')
        self.content = tk.Frame(main, bg=BG, padx=26, pady=23)
        self.content.pack(fill='both', expand=True)
        self.show('calendar')

    def show(self, key):
        for widget in self.content.winfo_children():
            widget.destroy()
        for name, item in self.nav.items():
            item.configure(bg='#294B6A' if name == key else INK, fg='white' if name == key else '#D5E1EC')
        views = {'calendar': CalendarView, 'employees': EmployeesView, 'vacations': VacationsView, 'holidays': HolidaysView, 'data': DataView}
        self.view = views[key](self.content, self)
        self.view.pack(fill='both', expand=True)

    def notify(self, text):
        self.status.configure(text='✓  ' + text)

    def update_identity(self):
        acronym = self.store.config['sigla_setor'] or 'STMU'
        self.organization.configure(text=f'{acronym}  /  Administração')
        self.title(f'{acronym} | Calendário de Férias')

    def safe(self, operation):
        try:
            return operation()
        except Exception as exc:
            logging.exception('Falha de operação')
            messagebox.showerror('Não foi possível concluir', str(exc), parent=self)

    def report_callback_exception(self, exc, value, tb):
        logging.error('Falha de interface', exc_info=(exc, value, tb))
        messagebox.showerror('Não foi possível concluir', str(value), parent=self)

    def preview(self):
        def open_preview():
            from .ui.impressao import PrintPreview
            PrintPreview(self)
        self.safe(open_preview)

    def close(self):
        self.store.close()
        self.destroy()


def main():
    prepare_tk_paths()
    if len(sys.argv) == 3 and sys.argv[1] == '--autoteste':
        from .diagnostics import run
        return run(Path(sys.argv[2]))
    store = None
    try:
        folder = data_directory()
        folder.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=folder / 'aplicativo.log', level=logging.ERROR, encoding='utf-8', format='%(asctime)s %(levelname)s %(message)s')
        store = Store(folder)
        app = Application(store)
        app.mainloop()
    except Exception as exc:
        logging.exception('Falha ao iniciar')
        if store:
            store.close()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror('Calendário STMU · Falha ao iniciar', f'{exc}\n\nOs arquivos existentes não foram apagados.\nPasta de dados: {data_directory()}')
            root.destroy()
        except Exception:
            print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
