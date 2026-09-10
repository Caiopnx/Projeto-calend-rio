import os
import shutil
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import pypdfium2 as pdfium
from ..services.pdf_service import generate_pdf
from .widgets import BG, INK, label, button


class PrintPreview(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title('PRÉ-VISUALIZAÇÃO DE IMPRESSÃO · ' + app.store.config['nome_setor'])
        self.geometry('1050x820')
        self.minsize(840, 600)
        self.configure(bg=BG)
        self.transient(app)
        self.grab_set()
        self.temp = tempfile.TemporaryDirectory(prefix='stmu_preview_')
        self.path = Path(self.temp.name) / 'calendario.pdf'
        self.document = None
        self.zoom, self.page = .95, 0
        top = tk.Frame(self, bg='white', padx=14, pady=12)
        top.pack(fill='x')
        label(top, f'A4 · {app.year:04d}', 12, True).pack(side='left', padx=(0, 12))
        self.orientation = tk.StringVar(value=app.store.config.get('orientacao', 'Paisagem'))
        combo = ttk.Combobox(top, values=['Retrato', 'Paisagem'], textvariable=self.orientation, state='readonly', width=11)
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>', lambda e: app.safe(self.generate))
        button(top, 'Zoom −', lambda: self.change_zoom(-.15)).pack(side='left', padx=(10, 3))
        button(top, 'Zoom +', lambda: self.change_zoom(.15)).pack(side='left')
        button(top, 'Gerar PDF', self.export, True).pack(side='right')
        button(top, 'Imprimir', self.print_file).pack(side='right', padx=8)
        nav = tk.Frame(self, bg=BG, padx=14, pady=8)
        nav.pack(fill='x')
        button(nav, '‹ Página', lambda: self.move_page(-1)).pack(side='left')
        self.info = label(nav, '')
        self.info.pack(side='left', padx=12)
        button(nav, 'Página ›', lambda: self.move_page(1)).pack(side='left')
        label(nav, 'Prévia do PDF final • margens incluídas', 9).pack(side='right')
        area = tk.Frame(self, bg='#CBD5E1')
        area.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(area, bg='#CBD5E1', highlightthickness=0)
        vs = ttk.Scrollbar(area, orient='vertical', command=self.canvas.yview)
        hs = ttk.Scrollbar(area, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        hs.pack(side='bottom', fill='x')
        vs.pack(side='right', fill='y')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-int(e.delta / 120), 'units'))
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda e: self.close())
        try:
            self.generate()
        except Exception:
            self.close()
            raise

    def generate(self):
        if self.document:
            self.document.close()
            self.document = None
        generate_pdf(self.app.store, self.app.year, self.path, self.orientation.get())
        self.document = pdfium.PdfDocument(str(self.path))
        self.page = 0
        if self.app.store.config['orientacao'] != self.orientation.get():
            self.app.store.configure(orientacao=self.orientation.get())
        self.update()
        first = self.document[0]
        width, height = first.get_size()
        first.close()
        area_width = self.canvas.winfo_width() if self.canvas.winfo_width() > 100 else 1000
        area_height = self.canvas.winfo_height() if self.canvas.winfo_height() > 100 else 650
        self.zoom = max(.3, min(1.4, (area_width - 45) / (width * 1.4), (area_height - 45) / (height * 1.4)))
        self.render()

    def render(self):
        if not self.document:
            return
        page = self.document[self.page]
        bitmap = page.render(scale=self.zoom * 1.4)
        picture = bitmap.to_pil().copy()
        bitmap.close()
        page.close()
        self.photo = ImageTk.PhotoImage(picture)
        self.canvas.delete('all')
        self.canvas.create_rectangle(25, 25, picture.width + 25, picture.height + 25, fill='#9AABBE', outline='')
        self.canvas.create_image(20, 20, image=self.photo, anchor='nw')
        self.canvas.configure(scrollregion=(0, 0, picture.width + 45, picture.height + 45))
        self.info.configure(text=f'{self.page + 1} / {len(self.document)} · Zoom {self.zoom:.0%}')

    def change_zoom(self, delta):
        self.zoom = min(2.5, max(.3, self.zoom + delta))
        self.render()

    def move_page(self, delta):
        self.page = max(0, min(len(self.document) - 1, self.page + delta))
        self.render()
        self.canvas.yview_moveto(0)

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, title='Gerar PDF', defaultextension='.pdf', filetypes=[('Documento PDF', '*.pdf')], initialfile=f'Calendario_Ferias_STMU_{self.app.year:04d}.pdf')
        if path:
            def save():
                shutil.copyfile(self.path, path)
                messagebox.showinfo('PDF gerado', f'Documento salvo em:\n{path}', parent=self)
            self.app.safe(save)

    def print_file(self):
        if os.name != 'nt':
            messagebox.showinfo('Impressão', 'Gere o PDF e abra-o no leitor de PDF para imprimir.', parent=self)
            return
        if not messagebox.askokcancel('Imprimir calendário', 'O PDF será enviado ao comando de impressão do leitor padrão do Windows.\n\nConfira a impressora padrão e configure A4, orientação ' + self.orientation.get().lower() + ' e ajuste à página no leitor.\n\nDeseja continuar?', parent=self):
            return
        try:
            # Keep a separate copy alive after the preview closes for the external reader.
            print_dir = self.app.store.directory.parent / 'impressao'
            print_dir.mkdir(exist_ok=True)
            from datetime import datetime
            target = print_dir / ('Calendario_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.pdf')
            shutil.copyfile(self.path, target)
            os.startfile(str(target), 'print')
            messagebox.showinfo('Comando enviado', 'O comando foi entregue ao leitor de PDF. Verifique a fila da impressora.\nA confirmação de impressão depende do leitor e da impressora.', parent=self)
        except OSError:
            messagebox.showinfo('Impressão pelo leitor de PDF', 'O leitor padrão não disponibiliza impressão automática.\nUse “Gerar PDF”, abra o documento no leitor e pressione Ctrl+P.', parent=self)

    def close(self):
        if self.document:
            self.document.close()
            self.document = None
        self.temp.cleanup()
        self.destroy()
