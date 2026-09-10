"""Calendário civil de Volta Redonda/RJ, calculado localmente, sem rede.

Regras recorrentes e ajustes anuais ficam separados no feriados.json.
As regras representam o calendário atual, não uma reconstrução histórica.
"""
import copy
from datetime import date, timedelta

HOLIDAY_COLOR = '#BE2836'
TYPES = ('Nacional', 'Estadual', 'Municipal')


def default_holidays():
    fixed = [
        ('ano-novo', 'Confraternização Universal', 'Nacional', 1, 1),
        ('tiradentes', 'Tiradentes', 'Nacional', 21, 4),
        ('trabalho', 'Dia do Trabalho', 'Nacional', 1, 5),
        ('independencia', 'Independência do Brasil', 'Nacional', 7, 9),
        ('aparecida', 'Nossa Senhora Aparecida', 'Nacional', 12, 10),
        ('finados', 'Finados', 'Nacional', 2, 11),
        ('republica', 'Proclamação da República', 'Nacional', 15, 11),
        ('consciencia-negra', 'Dia Nacional de Zumbi e da Consciência Negra', 'Nacional', 20, 11),
        ('natal', 'Natal', 'Nacional', 25, 12),
        ('sao-jorge', 'São Jorge', 'Estadual', 23, 4),
        ('santo-antonio', 'Santo Antônio', 'Municipal', 13, 6),
        ('aniversario-vr', 'Aniversário de Volta Redonda', 'Municipal', 17, 7),
    ]
    rules = [dict(id=i, nome=n, tipo=t, dia=d, mes=m, movel=False) for i, n, t, d, m in fixed]
    # Paixão de Cristo usa a categoria Nacional solicitada para a apresentação
    # administrativa; a base municipal também é documentada em FERIADOS.md.
    for i, n, t, offset in [
        ('paixao', 'Paixão de Cristo / Sexta-feira Santa', 'Nacional', -2),
        ('carnaval', 'Terça-feira de Carnaval', 'Estadual', -47),
        ('corpus-christi', 'Corpus Christi', 'Municipal', 60),
    ]:
        rules.append(dict(id=i, nome=n, tipo=t, movel=True, referencia='pascoa', deslocamento=offset))
    return {'versao': 1, 'feriados': rules, 'personalizados': [], 'excecoes': []}


def easter(year):
    """Computus gregoriano de Meeus/Jones/Butcher, anos 1 a 9999."""
    if type(year) is not int or not 1 <= year <= 9999:
        raise ValueError('Informe um ano de 1 a 9999.')
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def validate_holidays(data):
    try:
        if data['versao'] != 1:
            raise ValueError('Versão de feriados incompatível.')
        if any(not isinstance(data[k], list) for k in ('feriados', 'personalizados', 'excecoes')):
            raise ValueError('Estrutura de feriados inválida.')
        def fields(item):
            if not isinstance(item['nome'], str) or not item['nome'].strip() or len(item['nome']) > 160 or item['tipo'] not in TYPES:
                raise ValueError('Informe nome do feriado (até 160 caracteres) e tipo válido.')
        def exact_date(value):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() != value:
                raise ValueError('Use AAAA-MM-DD no JSON dos feriados.')
            return parsed
        ids = set()
        for rule in data['feriados']:
            fields(rule)
            if not isinstance(rule['id'], str) or not rule['id'] or rule['id'] in ids:
                raise ValueError('Identificador de feriado duplicado ou inválido.')
            ids.add(rule['id'])
            if type(rule['movel']) is not bool:
                raise ValueError('Indicador de data móvel inválido.')
            if rule['movel']:
                if rule['referencia'] != 'pascoa' or type(rule['deslocamento']) is not int or not -60 <= rule['deslocamento'] <= 100:
                    raise ValueError('Regra de feriado móvel inválida.')
            else:
                if type(rule['mes']) is not int or type(rule['dia']) is not int:
                    raise ValueError('Dia e mês devem ser inteiros.')
                date(2000, rule['mes'], rule['dia'])
        custom_ids = set()
        for item in data['personalizados']:
            fields(item)
            exact_date(item['data'])
            if not isinstance(item['id'], str) or not item['id'] or item['id'] in custom_ids:
                raise ValueError('Identificador de feriado personalizado inválido.')
            custom_ids.add(item['id'])
        keys = set()
        for item in data['excecoes']:
            if item['origem_id'] not in ids or type(item['ano']) is not int or not 1 <= item['ano'] <= 9999 or type(item['removido']) is not bool:
                raise ValueError('Ajuste anual de feriado inválido.')
            key = (item['origem_id'], item['ano'])
            if key in keys:
                raise ValueError('Ajuste anual de feriado duplicado.')
            keys.add(key)
            if not item['removido']:
                fields(item)
                if exact_date(item['data']).year != item['ano']:
                    raise ValueError('A data do ajuste deve pertencer ao ano selecionado.')
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Arquivo de feriados incompleto ou inválido.') from exc


def holidays_for_year(store, year):
    pascoa = easter(year)
    data = store.bundle['feriados.json']
    changes = {(x['origem_id'], x['ano']): x for x in data['excecoes']}
    result = []
    for rule in data['feriados']:
        change = changes.get((rule['id'], year))
        if change and change['removido']:
            continue
        if change:
            day = date.fromisoformat(change['data'])
        elif rule['movel']:
            day = pascoa + timedelta(days=rule['deslocamento'])
        else:
            try:
                day = date(year, rule['mes'], rule['dia'])
            except ValueError:  # Regra de 29/02 só ocorre em anos bissextos.
                continue
        entry = change or rule
        result.append(dict(id=rule['id'], data=day.isoformat(), nome=entry['nome'], tipo=entry['tipo'], origem='padrao', ajustado=bool(change)))
    for item in data['personalizados']:
        if date.fromisoformat(item['data']).year == year:
            result.append(dict(item, origem='personalizado', ajustado=False))
    return sorted(result, key=lambda x: (x['data'], x['nome'].casefold()))


def holiday_map(store, year):
    result = {}
    for item in holidays_for_year(store, year):
        result.setdefault(date.fromisoformat(item['data']), []).append(item)
    return result
