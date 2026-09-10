import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from app.services.json_service import Store, FILES, atomic_write
from app.services.backup_service import create_backup, restore_backup
from app.services.calendario_service import month_weeks, year_data
from app.services.pdf_service import generate_pdf
import pypdfium2 as pdfium


class ServicesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'data')
        self.person = self.store.save_employee(dict(nome='João da Silva', matricula='001', setor='STMU', cargo='Agente', cor='#176BCE', ativo=True))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_persistence_edit_and_color(self):
        self.store.save_vacation(self.person, [(date(2027, 1, 1), date(2027, 1, 30))])
        employee = dict(self.store.employees[0], nome='João Santos', cor='#118855')
        self.store.save_employee(employee, self.person)
        self.store.close()
        self.store = Store(Path(self.temp.name) / 'data')
        days, legend = year_data(self.store, 2027)
        self.assertEqual(len(days), 30)
        self.assertEqual(days[date(2027, 1, 1)][0]['cor'], '#118855')
        self.assertEqual(legend[0]['nome'], 'João Santos')

    def test_duplicate_registration_and_validation(self):
        before = copy.deepcopy(self.store.bundle)
        with self.assertRaises(ValueError):
            self.store.save_employee(dict(self.store.employees[0], nome='Outro'), None)
        self.assertEqual(before, self.store.bundle)
        with self.assertRaises(ValueError):
            self.store.save_employee(dict(self.store.employees[0], cor='red'), self.person)

    def test_split_and_cross_year(self):
        self.store.save_vacation(self.person, [(date(2027, 12, 25), date(2028, 1, 8)), (date(2028, 2, 16), date(2028, 3, 1))])
        self.assertEqual(len(year_data(self.store, 2027)[0]), 7)
        self.assertEqual(len(year_data(self.store, 2028)[0]), 23)
        self.assertIn(date(2028, 2, 29), year_data(self.store, 2028)[0])
        self.assertEqual(year_data(self.store, 2026), ({}, []))

    def test_invalid_duration_overlap_and_edit(self):
        for periods in [[(date(2027, 1, 1), date(2027, 1, 29))], [(date(2027, 1, 30), date(2027, 1, 1))], [(date(2027, 1, 1), date(2027, 1, 15))]]:
            with self.assertRaises(ValueError):
                self.store.save_vacation(self.person, periods)
        self.store.save_vacation(self.person, [(date(2027, 1, 1), date(2027, 1, 30))])
        with self.assertRaises(ValueError):
            self.store.save_vacation(self.person, [(date(2027, 1, 30), date(2027, 2, 28))])
        request_id = self.store.vacations[0]['solicitacao']
        self.store.save_vacation(self.person, [(date(2027, 3, 1), date(2027, 3, 30))], request_id)
        self.assertEqual(len(self.store.vacations), 1)
        self.store.delete_vacation(request_id)
        self.assertFalse(self.store.vacations)

    def test_simultaneous_employees(self):
        second = self.store.save_employee(dict(nome='Maria', matricula='002', setor='STMU', cargo='Agente', cor='#AA8844', ativo=False))
        for person in [self.person, second]:
            self.store.save_vacation(person, [(date(2027, 1, 1), date(2027, 1, 30))])
        days, legend = year_data(self.store, 2027)
        self.assertEqual(len(days[date(2027, 1, 1)]), 2)
        self.assertEqual(len(legend), 2)
        self.store.delete_employee(self.person)
        self.assertEqual(len(self.store.vacations), 1)

    def test_real_calendar_and_limits(self):
        self.assertEqual(month_weeks(2027, 1)[0], [0, 0, 0, 0, 0, 1, 2])
        self.assertIn(29, sum(month_weeks(2028, 2), []))
        self.assertNotIn(29, sum(month_weeks(2100, 2), []))
        for year in [1, 2000, 9999]:
            self.assertEqual(len(month_weeks(year, 12)), 6)
        with self.assertRaises(ValueError):
            month_weeks(0, 1)

    def test_backup_restore_and_reject_bad_backup(self):
        backup = create_backup(self.store, Path(self.temp.name) / 'backups')
        self.store.delete_employee(self.person)
        safety = restore_backup(self.store, backup)
        self.assertTrue((safety / FILES[0]).exists())
        self.assertEqual(len(self.store.employees), 1)
        original = copy.deepcopy(self.store.bundle)
        (backup / FILES[1]).write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            restore_backup(self.store, backup)
        self.assertEqual(original, self.store.bundle)

    def test_crash_recovery(self):
        recovered = copy.deepcopy(self.store.bundle)
        recovered[FILES[0]]['funcionarios'][0]['nome'] = 'Recuperado'
        atomic_write(self.store.directory / 'transacao.json', recovered)
        self.store.close()
        self.store = Store(Path(self.temp.name) / 'data')
        self.assertEqual(self.store.employees[0]['nome'], 'Recuperado')
        self.assertFalse((self.store.directory / 'transacao.json').exists())

    def test_lock_prevents_two_writers(self):
        with self.assertRaises(ValueError):
            Store(self.store.directory)

    def test_corrupted_data_preserved(self):
        self.store.close()
        path = Path(self.temp.name) / 'data' / FILES[0]
        path.write_text('{bad', encoding='utf-8')
        with self.assertRaises(ValueError):
            Store(path.parent)
        self.assertEqual(path.read_text(encoding='utf-8'), '{bad')

    def test_write_failure_blocks_further_writes(self):
        with patch('app.services.json_service.atomic_write', side_effect=OSError('disco cheio')):
            with self.assertRaises(OSError):
                self.store.configure(ano=2028)
        with self.assertRaises(ValueError):
            self.store.configure(ano=2029)

    def test_pdf_portrait_landscape_and_legend_pagination(self):
        bundle = copy.deepcopy(self.store.bundle)
        for i in range(2, 92):
            bundle[FILES[0]]['funcionarios'].append(dict(id=i, nome=f'Funcionário {i:03d} ' + 'Sobrenome ' * 8, matricula=str(i), setor='STMU', cargo='Agente', cor='#558899', ativo=True))
            bundle[FILES[1]]['ferias'].append(dict(id=i, funcionario_id=i, solicitacao=str(i), ano=2028, periodo=1, inicio='2028-01-01', fim='2028-01-30'))
        self.store.commit(bundle)
        for orientation in ('Retrato', 'Paisagem'):
            path = Path(self.temp.name) / (orientation + '.pdf')
            generate_pdf(self.store, 2028, path, orientation)
            with pdfium.PdfDocument(str(path)) as doc:
                self.assertGreater(len(doc), 1)
                page = doc[0]
                width, height = page.get_size()
                self.assertEqual(width > height, orientation == 'Paisagem')
                page.close()
                text = ''
                for page in doc:
                    txt = page.get_textpage()
                    text += txt.get_text_range()
                    txt.close()
                    page.close()
                for month in ['JANEIRO', 'FEVEREIRO', 'DEZEMBRO']:
                    self.assertIn(month, text)
                self.assertIn('Funcionário 091', text)


if __name__ == '__main__':
    unittest.main()
