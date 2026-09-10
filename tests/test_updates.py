import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from app.services.json_service import Store, FILES, atomic_write
from app.services.backup_service import create_backup, restore_backup
from app.services.feriados_service import holidays_for_year, holiday_map, easter
from app.services.calendario_service import year_data
from app.services.pdf_service import generate_pdf
import pypdfium2 as pdfium


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'data')
        self.person = self.store.save_employee(dict(nome='Teste', matricula='01', setor='STMU', cargo='Agente', cor='#118855', ativo=True))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def legacy_bundle(self):
        bundle = copy.deepcopy({name: self.store.bundle[name] for name in FILES[:3]})
        for key in ('nome_setor', 'sigla_setor', 'feriados_versao'):
            bundle['configuracoes.json'].pop(key, None)
        return bundle

    def test_ten_twenty_edit_reopen_and_overlap(self):
        self.store.save_vacation(self.person, [(date(2027, 7, 8), date(2027, 7, 17)), (date(2027, 12, 20), date(2028, 1, 8))])
        self.assertEqual(len(year_data(self.store, 2027)[0]), 22)
        self.assertEqual(len(year_data(self.store, 2028)[0]), 8)
        self.assertIn(date(2027, 7, 17), holiday_map(self.store, 2027))
        request = self.store.vacations[0]['solicitacao']
        self.store.save_vacation(self.person, [(date(2027, 6, 1), date(2027, 6, 10)), (date(2027, 7, 1), date(2027, 7, 20))], request)
        with self.assertRaises(ValueError):
            self.store.save_vacation(self.person, [(date(2027, 7, 10), date(2027, 8, 8))])
        self.store.close()
        self.store = Store(self.root / 'data')
        self.assertEqual(len(self.store.vacations), 2)

    def test_reject_invalid_split(self):
        for periods in [
            [(date(2027, 1, 1), date(2027, 1, 10))],
            [(date(2027, 1, 1), date(2027, 1, 20)), (date(2027, 3, 1), date(2027, 3, 10))],
            [(date(2027, 1, 1), date(2027, 1, 10)), (date(2027, 1, 10), date(2027, 1, 29))],
            [(date(2027, 1, 1), date(2027, 1, 11)), (date(2027, 3, 1), date(2027, 3, 19))],
        ]:
            with self.assertRaises(ValueError):
                self.store.save_vacation(self.person, periods)

    def test_mobile_dates_and_scope(self):
        self.assertEqual(easter(2026), date(2026, 4, 5))
        self.assertEqual(easter(2027), date(2027, 3, 28))
        self.assertEqual(easter(2028), date(2028, 4, 16))
        dates = {x['id']: x for x in holidays_for_year(self.store, 2027)}
        self.assertEqual(dates['paixao']['data'], '2027-03-26')
        self.assertEqual(dates['carnaval']['data'], '2027-02-09')
        self.assertEqual(dates['carnaval']['tipo'], 'Estadual')
        self.assertEqual(dates['corpus-christi']['data'], '2027-05-27')
        self.assertEqual(dates['corpus-christi']['tipo'], 'Municipal')
        self.assertEqual(len(dates), 15)
        forbidden = [date(2027, 1, 20), date(2027, 2, 8), date(2027, 2, 10), date(2027, 3, 8), date(2027, 10, 28)]
        self.assertTrue(all(day not in holiday_map(self.store, 2027) for day in forbidden))
        for year in [1, 2026, 2028, 2100, 9999]:
            annual = {x['id']: x for x in holidays_for_year(self.store, year)}
            self.assertEqual(annual['aniversario-vr']['data'], date(year, 7, 17).isoformat())
            self.assertEqual(annual['santo-antonio']['data'], date(year, 6, 13).isoformat())

    def test_annual_override_and_reset_preserve_rules(self):
        original = copy.deepcopy(self.store.bundle['feriados.json']['feriados'])
        selected = next(x for x in holidays_for_year(self.store, 2027) if x['id'] == 'sao-jorge')
        self.store.save_holiday(dict(nome='São Jorge ajustado', data='2027-04-20', tipo='Estadual'), 2027, selected)
        self.assertIn(date(2027, 4, 20), holiday_map(self.store, 2027))
        self.assertNotIn(date(2027, 4, 23), holiday_map(self.store, 2027))
        self.assertIn(date(2028, 4, 23), holiday_map(self.store, 2028))
        self.store.delete_holiday(selected, 2027)
        self.assertNotIn(date(2027, 4, 20), holiday_map(self.store, 2027))
        self.store.save_holiday(dict(nome='Feriado local de teste', data='2027-08-10', tipo='Municipal'), 2027)
        self.store.reset_holidays(2027)
        self.assertIn(date(2027, 4, 23), holiday_map(self.store, 2027))
        self.assertIn(date(2027, 8, 10), holiday_map(self.store, 2027))
        self.assertEqual(original, self.store.bundle['feriados.json']['feriados'])

    def test_custom_edit_delete_and_invalid(self):
        self.store.save_holiday(dict(nome='Teste', data='2027-08-10', tipo='Municipal'), 2027)
        item = next(x for x in holidays_for_year(self.store, 2027) if x['origem'] == 'personalizado')
        self.store.save_holiday(dict(nome='Teste editado', data='2027-08-11', tipo='Estadual'), 2027, item)
        self.assertNotIn(date(2027, 8, 10), holiday_map(self.store, 2027))
        self.store.delete_holiday(item, 2027)
        self.assertNotIn(date(2027, 8, 11), holiday_map(self.store, 2027))
        for fields in [dict(nome='', data='2027-08-10', tipo='Municipal'), dict(nome='Teste', data='2028-08-10', tipo='Municipal'), dict(nome='Teste', data='2027-08-10', tipo='Facultativo')]:
            with self.assertRaises(ValueError):
                self.store.save_holiday(fields, 2027)

    def test_legacy_migration_and_byte_backup(self):
        folder = self.root / 'legacy'
        folder.mkdir()
        legacy = self.legacy_bundle()
        for name, data in legacy.items():
            atomic_write(folder / name, data)
        before = {name: (folder / name).read_bytes() for name in legacy}
        migrated = Store(folder)
        try:
            self.assertEqual(migrated.employees, self.store.employees)
            self.assertEqual(migrated.config['nome_setor'], 'STMU')
            self.assertEqual(len(holidays_for_year(migrated, 2027)), 15)
            backups = list((folder.parent / 'backups').glob('antes_atualizacao_*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(before, {name: (backups[0] / name).read_bytes() for name in legacy})
        finally:
            migrated.close()

    def test_legacy_transaction_recovery(self):
        folder = self.root / 'legacy-journal'
        folder.mkdir()
        atomic_write(folder / 'transacao.json', self.legacy_bundle())
        recovered = Store(folder)
        try:
            self.assertEqual(recovered.employees, self.store.employees)
            self.assertTrue((folder / 'feriados.json').exists())
        finally:
            recovered.close()

    def test_backup_new_and_legacy(self):
        self.store.configure(nome_setor='SETOR DE TRANSPORTE', sigla_setor='ST')
        self.store.save_holiday(dict(nome='Teste', data='2027-08-10', tipo='Municipal'), 2027)
        backup = create_backup(self.store, self.root / 'backup')
        self.assertTrue((backup / 'feriados.json').exists())
        self.store.configure(nome_setor='Outro')
        restore_backup(self.store, backup)
        self.assertEqual(self.store.config['nome_setor'], 'SETOR DE TRANSPORTE')
        legacy = self.root / 'old-backup'
        legacy.mkdir()
        for name, data in self.legacy_bundle().items():
            atomic_write(legacy / name, data)
        restore_backup(self.store, legacy)
        self.assertIn(date(2027, 8, 10), holiday_map(self.store, 2027))
        self.assertEqual(self.store.config['nome_setor'], 'SETOR DE TRANSPORTE')

    def test_missing_or_corrupted_holidays_not_silently_reset(self):
        self.store.close()
        file = self.root / 'data' / 'feriados.json'
        file.unlink()
        with self.assertRaises(ValueError):
            Store(file.parent)
        file.write_text('{invalid', encoding='utf-8')
        with self.assertRaises(ValueError):
            Store(file.parent)
        self.assertEqual(file.read_text(encoding='utf-8'), '{invalid')

    def test_sector_validation(self):
        for fields in [dict(nome_setor=''), dict(nome_setor='A' * 161), dict(sigla_setor='A' * 25)]:
            with self.assertRaises(ValueError):
                self.store.configure(**fields)
        self.store.configure(nome_setor='Secretaria Municipal', sigla_setor='')

    def test_pdf_long_sector_red_bold_and_vacation_colors(self):
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.colors import HexColor
        self.store.configure(nome_setor=('SECRETARIA MUNICIPAL DE TRANSPORTE E MOBILIDADE URBANA ' * 3)[:160])
        self.store.save_vacation(self.person, [(date(2027, 7, 8), date(2027, 7, 17)), (date(2027, 8, 1), date(2027, 8, 20))])
        seen = []
        original = Canvas.drawString
        def observe(canvas, x, y, text, *args, **kw):
            seen.append((text, canvas._fontname, canvas._fillColorObj))
            return original(canvas, x, y, text, *args, **kw)
        for orientation in ('Retrato', 'Paisagem'):
            path = self.root / (orientation + '.pdf')
            with patch.object(Canvas, 'drawString', observe):
                generate_pdf(self.store, 2027, path, orientation)
            with pdfium.PdfDocument(str(path)) as document:
                page = document[0]
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                self.assertIn('SECRETARIA MUNICIPAL', text)
                self.assertIn('ANO: 2027', text)
                self.assertIn('DEZEMBRO', text)
                textpage.close()
                page.close()
        self.assertTrue(any(text == '17' and font == 'Helvetica-Bold' and color == HexColor('#BE2836') for text, font, color in seen))


if __name__ == '__main__':
    unittest.main()
