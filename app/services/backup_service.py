import json
from datetime import datetime
from pathlib import Path
from .json_service import FILES, atomic_write, validate_bundle, upgrade_bundle


def create_backup(store, destination):
    if store.failed:
        raise ValueError('Reabra o aplicativo para recuperar a gravação antes de fazer backup.')
    folder = Path(destination) / ('STMU_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        atomic_write(folder / name, store.bundle[name])
    return folder


def restore_backup(store, source):
    folder = Path(source)
    bundle = {name: json.loads((folder / name).read_text(encoding='utf-8')) for name in FILES[:3]}
    if (folder / 'feriados.json').exists():
        bundle['feriados.json'] = json.loads((folder / 'feriados.json').read_text(encoding='utf-8'))
    elif 'feriados_versao' not in bundle['configuracoes.json']:
        # Backup da versão anterior: não apaga ajustes que ele nunca continha.
        import copy
        bundle['feriados.json'] = copy.deepcopy(store.bundle['feriados.json'])
        for key in ('nome_setor', 'sigla_setor'):
            bundle['configuracoes.json'].setdefault(key, store.config[key])
    bundle = upgrade_bundle(bundle)
    validate_bundle(bundle)
    safety = create_backup(store, store.directory.parent / 'backups')
    store.commit(bundle)
    return safety
