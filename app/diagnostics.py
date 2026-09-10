"""Autoteste opcional do código e do EXE; usa cadastros temporários."""
import json
import tempfile
import traceback
from datetime import date
from pathlib import Path
from .services.json_service import Store
from .services.calendario_service import year_data
from .services.backup_service import create_backup, restore_backup


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    app = store = None
    report = {'ok': False, 'checks': []}
    try:
        with tempfile.TemporaryDirectory(prefix='stmu_test_') as temp:
            from .main import Application
            from .ui.funcionarios import EmployeeDialog
            from .ui.ferias import VacationDialog
            from .ui.impressao import PrintPreview
            from .ui.feriados import HolidayDialog
            from PIL import ImageGrab
            store = Store(Path(temp) / 'data')
            store.configure(ano=2028)
            app = Application(store)
            errors = []
            app.report_callback_exception = lambda *args: errors.append(str(args[1]))
            employee = EmployeeDialog(app)
            for key, value in dict(nome='Funcionário de Teste', matricula='QA-001', setor='STMU', cargo='Agente').items():
                employee.fields[key].set(value)
            employee.save()
            assert len(store.employees) == 1
            report['checks'].append('Cadastro pela interface')
            vacation = VacationDialog(app)
            vacation.person.set(next(iter(vacation.people)))
            vacation.mode.set('15 + 15 dias')
            vacation.mode_changed()
            vacation.periods[0][0].set('16/02/2028')
            vacation.auto_end(0)
            vacation.periods[1][0].set('20/12/2028')
            vacation.auto_end(1)
            vacation.save()
            assert len(store.vacations) == 2
            assert date(2028, 2, 29) in year_data(store, 2028)[0]
            assert len(year_data(store, 2029)[0]) == 3
            report['checks'].append('Férias 15 + 15 pela interface, bissexto e virada de ano')
            vacation = VacationDialog(app)
            vacation.person.set(next(iter(vacation.people)))
            vacation.mode.set('10 + 20 dias')
            vacation.mode_changed()
            vacation.periods[0][0].set('08/07/2028')
            vacation.auto_end(0)
            vacation.periods[1][0].set('01/08/2028')
            vacation.auto_end(1)
            assert vacation.periods[0][1].get() == '17/07/2028'
            assert vacation.periods[1][1].get() == '20/08/2028'
            vacation.save()
            assert len(store.vacations) == 4
            edit = VacationDialog(app, store.vacations[-1]['solicitacao'])
            assert edit.mode.get() == '10 + 20 dias'
            edit.destroy()
            report['checks'].append('Cadastro e edição de 10 + 20 pela interface')
            holiday = HolidayDialog(app, 2028)
            holiday.name.set('Feriado de teste')
            holiday.day.set('10/09/2028')
            holiday.save()
            app.view.kind.set('Estadual')
            app.view.refresh()
            assert len(app.view.rows) == 2
            report['checks'].append('Cadastro e filtro de feriados pela interface')
            app.show('data')
            app.view.sector.set('SECRETARIA MUNICIPAL DE TRANSPORTE E MOBILIDADE URBANA')
            app.view.acronym.set('STMU')
            app.view.save_settings()
            assert store.config['nome_setor'].startswith('SECRETARIA')
            for key in ['calendar', 'employees', 'vacations', 'holidays', 'data']:
                app.show(key)
                app.update()
            app.show('calendar')
            app.update()
            app.view.month.set('JULHO')
            app.view.refresh()
            app.update()
            import tkinter as tk
            grid = app.view.scroll.inner.winfo_children()[0]
            card = grid.winfo_children()[0]
            calendar_canvas = next(x for x in card.winfo_children() if isinstance(x, tk.Canvas))
            seventeens = [x for x in calendar_canvas.find_all() if calendar_canvas.type(x) == 'text' and calendar_canvas.itemcget(x, 'text') == '17']
            assert len(seventeens) == 1
            assert calendar_canvas.itemcget(seventeens[0], 'fill') == '#BE2836'
            assert 'bold' in calendar_canvas.itemcget(seventeens[0], 'font')
            assert date(2028, 7, 17) in year_data(store, 2028)[0]
            app.view.month.set('Visão anual')
            app.view.refresh()
            app.update()
            report['checks'].append('Feriado vermelho/negrito junto com férias; nome do setor')
            try:
                ImageGrab.grab(window=app.winfo_id()).save(output / 'aplicativo.png')
            except OSError:
                pass
            preview = PrintPreview(app)
            for orientation in ['Retrato', 'Paisagem']:
                preview.orientation.set(orientation)
                preview.generate()
                preview.change_zoom(.15)
                assert preview.document is not None
            preview.close()
            report['checks'].append('Telas, geração de PDF, prévia A4 e zoom')
            backup = create_backup(store, Path(temp) / 'backups')
            store.delete_employee(store.employees[0]['id'])
            assert len(store.vacations) == 0
            restore_backup(store, backup)
            assert len(store.vacations) == 4
            report['checks'].append('Exclusão e restauração do backup')
            app.close()
            app = None
            store = Store(Path(temp) / 'data')
            assert len(store.vacations) == 4
            store.close()
            store = None
            assert not errors, str(errors)
            report['checks'].append('Persistência após reabertura')
            report['ok'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if app:
            app.close()
        elif store:
            store.close()
        (output / 'autoteste.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
