"""Persistência local, gravação atômica e recuperação transacional de JSON."""
import copy
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from .feriados_service import default_holidays, validate_holidays


FILES = ('funcionarios.json', 'ferias.json', 'configuracoes.json', 'feriados.json')
DEFAULTS = ({'funcionarios': []}, {'ferias': []}, {'versao': 1, 'ano': date.today().year, 'orientacao': 'Paisagem', 'nome_setor': 'STMU', 'sigla_setor': 'STMU', 'feriados_versao': 1}, default_holidays())


def upgrade_bundle(bundle):
    """Adiciona campos sem alterar os cadastros existentes."""
    upgraded = copy.deepcopy(bundle)
    config = upgraded['configuracoes.json']
    if 'feriados.json' not in upgraded:
        if 'feriados_versao' in config:
            raise ValueError('Falta feriados.json. Restaure um backup completo para preservar seus ajustes.')
        upgraded['feriados.json'] = default_holidays()
    config.setdefault('nome_setor', 'STMU')
    config.setdefault('sigla_setor', 'STMU')
    config.setdefault('feriados_versao', 1)
    return upgraded


def data_directory():
    if os.environ.get('STMU_DATA_DIR'):
        return Path(os.environ['STMU_DATA_DIR'])
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    if not getattr(sys, 'frozen', False) or (base / 'portable.flag').exists():
        return base / 'data'
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'STMU' / 'CalendarioFerias' / 'data'


def atomic_write(path, data):
    path = Path(path)
    temp = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def validate_bundle(bundle):
    try:
        employees = bundle[FILES[0]]['funcionarios']
        vacations = bundle[FILES[1]]['ferias']
        config = bundle[FILES[2]]
        if not isinstance(employees, list) or not isinstance(vacations, list) or not isinstance(config, dict):
            raise ValueError('Estrutura JSON inválida.')
        if config.get('versao') != 1 or type(config.get('ano')) is not int or not 1 <= config['ano'] <= 9999 or config.get('orientacao') not in ('Retrato', 'Paisagem'):
            raise ValueError('Configurações inválidas ou versão incompatível.')
        if not isinstance(config.get('nome_setor'), str) or not config['nome_setor'].strip() or len(config['nome_setor']) > 160:
            raise ValueError('Informe o nome do setor (até 160 caracteres).')
        if not isinstance(config.get('sigla_setor'), str) or len(config['sigla_setor']) > 24 or config.get('feriados_versao') != 1:
            raise ValueError('Sigla do setor inválida (até 24 caracteres) ou versão de feriados incompatível.')
        validate_holidays(bundle['feriados.json'])
        ids, registrations = set(), set()
        for e in employees:
            if type(e['id']) is not int or e['id'] < 1 or e['id'] in ids:
                raise ValueError('ID de funcionário inválido ou duplicado.')
            ids.add(e['id'])
            for key in ('nome', 'matricula', 'setor', 'cargo'):
                if not isinstance(e[key], str) or not e[key].strip() or len(e[key]) > 160:
                    raise ValueError('Preencha os campos do funcionário (máximo de 160 caracteres).')
            reg = e['matricula'].strip().casefold()
            if reg in registrations:
                raise ValueError('Já existe um funcionário com essa matrícula.')
            registrations.add(reg)
            if not isinstance(e['cor'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', e['cor']) or type(e['ativo']) is not bool:
                raise ValueError('Cor ou situação inválida.')
        vacation_ids, groups = set(), {}
        for v in vacations:
            if type(v['id']) is not int or v['id'] < 1 or v['id'] in vacation_ids:
                raise ValueError('ID de férias inválido ou duplicado.')
            vacation_ids.add(v['id'])
            if type(v['funcionario_id']) is not int or v['funcionario_id'] not in ids:
                raise ValueError('Férias vinculadas a funcionário inexistente.')
            start, end = date.fromisoformat(v['inicio']), date.fromisoformat(v['fim'])
            if v['inicio'] != start.isoformat() or v['fim'] != end.isoformat():
                raise ValueError('As datas no JSON devem usar o formato AAAA-MM-DD.')
            days = (end - start).days + 1
            if days not in (10, 15, 20, 30) or v['ano'] != start.year:
                raise ValueError('Cada período deve ter 10, 15, 20 ou 30 dias corridos, incluindo início e fim.')
            if not isinstance(v['solicitacao'], str) or not v['solicitacao'] or type(v['periodo']) is not int or v['periodo'] not in (1, 2):
                raise ValueError('Solicitação de férias inválida.')
            groups.setdefault(v['solicitacao'], []).append(v)
        for group in groups.values():
            ordered = sorted(group, key=lambda x: x['periodo'])
            durations = [(date.fromisoformat(x['fim']) - date.fromisoformat(x['inicio'])).days + 1 for x in ordered]
            if durations not in ([30], [15, 15], [10, 20]) or [x['periodo'] for x in ordered] != list(range(1, len(ordered) + 1)) or len({x['funcionario_id'] for x in ordered}) != 1:
                raise ValueError('A solicitação deve conter 30 dias, 15 + 15 dias ou 10 + 20 dias, nessa ordem.')
        for employee_id in ids:
            periods = sorted((v for v in vacations if v['funcionario_id'] == employee_id), key=lambda v: v['inicio'])
            for previous, current in zip(periods, periods[1:]):
                if current['inicio'] <= previous['fim']:
                    raise ValueError('Há períodos de férias sobrepostos para o mesmo funcionário.')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Arquivo de dados incompleto ou incompatível.') from exc


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = (self.directory / '.stmu.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.lock.seek(0)
                if self.lock.read(1) == b'':
                    self.lock.write(b'0')
                    self.lock.flush()
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.lock.close()
            raise ValueError('O aplicativo já está aberto com esta pasta de dados. Feche a outra janela.') from exc
        try:
            journal = self.directory / 'transacao.json'
            if journal.exists():
                recovered = upgrade_bundle(json.loads(journal.read_text(encoding='utf-8')))
                validate_bundle(recovered)
                for name in FILES:
                    atomic_write(self.directory / name, recovered[name])
                journal.unlink()
            existing = [name for name in FILES if (self.directory / name).exists()]
            if existing and not all(name in existing for name in FILES[:3]):
                raise ValueError('A pasta de dados está incompleta. Restaure um backup completo; nenhum dado foi sobrescrito.')
            if not existing:
                atomic_write(journal, {name: initial for name, initial in zip(FILES, DEFAULTS)})
                for name, initial in zip(FILES, DEFAULTS):
                    atomic_write(self.directory / name, initial)
                journal.unlink()
            original = {name: json.loads((self.directory / name).read_text(encoding='utf-8')) for name in FILES if (self.directory / name).exists()}
            self.bundle = upgrade_bundle(original)
            validate_bundle(self.bundle)
            self.failed = False
            if self.bundle != original:
                # Backup byte a byte antes da primeira migração; arquivos antigos
                # continuam disponíveis mesmo se houver interrupção na gravação.
                import shutil
                backup = self.directory.parent / 'backups' / ('antes_atualizacao_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                backup.mkdir(parents=True, exist_ok=False)
                for name in original:
                    shutil.copyfile(self.directory / name, backup / name)
                self.commit(self.bundle)
        except Exception:
            self.close()
            raise

    @property
    def employees(self):
        return self.bundle[FILES[0]]['funcionarios']

    @property
    def vacations(self):
        return self.bundle[FILES[1]]['ferias']

    @property
    def config(self):
        return self.bundle[FILES[2]]

    def commit(self, bundle):
        if self.failed:
            raise ValueError('Uma gravação falhou. Feche e reabra o aplicativo para recuperar a transação antes de continuar.')
        validate_bundle(bundle)
        journal = self.directory / 'transacao.json'
        try:
            atomic_write(journal, bundle)
            for name in FILES:
                atomic_write(self.directory / name, bundle[name])
            journal.unlink()
        except OSError:
            self.failed = True
            raise
        self.bundle = copy.deepcopy(bundle)

    def save_employee(self, fields, employee_id=None):
        bundle = copy.deepcopy(self.bundle)
        entries = bundle[FILES[0]]['funcionarios']
        employee = dict(fields, id=employee_id or max((x['id'] for x in entries), default=0) + 1)
        entries[:] = [x for x in entries if x['id'] != employee_id] + [employee]
        self.commit(bundle)
        return employee['id']

    def delete_employee(self, employee_id):
        bundle = copy.deepcopy(self.bundle)
        bundle[FILES[0]]['funcionarios'] = [x for x in self.employees if x['id'] != employee_id]
        bundle[FILES[1]]['ferias'] = [x for x in self.vacations if x['funcionario_id'] != employee_id]
        self.commit(bundle)

    def save_vacation(self, employee_id, periods, request_id=None):
        if employee_id not in {e['id'] for e in self.employees}:
            raise ValueError('Selecione um funcionário.')
        durations = [(end - start).days + 1 for start, end in periods]
        if durations not in ([30], [15, 15], [10, 20]):
            raise ValueError('Informe 30 dias, 15 + 15 dias ou 10 + 20 dias, nessa ordem. As datas inicial e final contam.')
        bundle = copy.deepcopy(self.bundle)
        next_id = max((v['id'] for v in self.vacations), default=0) + 1
        entries = [v for v in self.vacations if v['solicitacao'] != request_id]
        request_id = request_id or uuid4().hex
        for i, (start, end) in enumerate(periods):
            entries.append(dict(id=next_id + i, funcionario_id=employee_id, solicitacao=request_id, periodo=i + 1, ano=start.year, inicio=start.isoformat(), fim=end.isoformat()))
        bundle[FILES[1]]['ferias'] = entries
        self.commit(bundle)

    def delete_vacation(self, request_id):
        bundle = copy.deepcopy(self.bundle)
        bundle[FILES[1]]['ferias'] = [v for v in self.vacations if v['solicitacao'] != request_id]
        self.commit(bundle)

    def configure(self, **values):
        bundle = copy.deepcopy(self.bundle)
        bundle[FILES[2]].update(values)
        self.commit(bundle)

    def save_holiday(self, fields, year, selected=None):
        bundle = copy.deepcopy(self.bundle)
        data = bundle['feriados.json']
        if date.fromisoformat(fields['data']).year != year:
            raise ValueError('Informe uma data dentro do ano selecionado.')
        if selected and selected['origem'] == 'padrao':
            data['excecoes'] = [x for x in data['excecoes'] if (x['origem_id'], x['ano']) != (selected['id'], year)]
            data['excecoes'].append(dict(fields, origem_id=selected['id'], ano=year, removido=False))
        else:
            identifier = selected['id'] if selected else uuid4().hex
            data['personalizados'] = [x for x in data['personalizados'] if x['id'] != identifier]
            data['personalizados'].append(dict(fields, id=identifier))
        self.commit(bundle)

    def delete_holiday(self, selected, year):
        bundle = copy.deepcopy(self.bundle)
        data = bundle['feriados.json']
        if selected['origem'] == 'padrao':
            data['excecoes'] = [x for x in data['excecoes'] if (x['origem_id'], x['ano']) != (selected['id'], year)]
            data['excecoes'].append(dict(origem_id=selected['id'], ano=year, removido=True))
        else:
            data['personalizados'] = [x for x in data['personalizados'] if x['id'] != selected['id']]
        self.commit(bundle)

    def reset_holidays(self, year):
        bundle = copy.deepcopy(self.bundle)
        bundle['feriados.json']['excecoes'] = [x for x in bundle['feriados.json']['excecoes'] if x['ano'] != year]
        self.commit(bundle)

    def close(self):
        if getattr(self, 'lock', None) and not self.lock.closed:
            self.lock.close()
