import calendar
from datetime import date, timedelta

MONTHS = ('JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO')
WEEKDAYS = ('DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SÁB')


def month_weeks(year, month):
    if not 1 <= year <= 9999:
        raise ValueError('Escolha um ano entre 1 e 9999.')
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    return weeks + [[0] * 7 for _ in range(6 - len(weeks))]


def year_data(store, year):
    if not 1 <= year <= 9999:
        raise ValueError('Escolha um ano entre 1 e 9999.')
    employees = {e['id']: e for e in store.employees}
    days, selected = {}, set()
    for v in store.vacations:
        start = max(date.fromisoformat(v['inicio']), date(year, 1, 1))
        end = min(date.fromisoformat(v['fim']), date(year, 12, 31))
        if start > end:
            continue
        selected.add(v['funcionario_id'])
        for offset in range((end - start).days + 1):
            days.setdefault(start + timedelta(days=offset), []).append(employees[v['funcionario_id']])
    legend = sorted((employees[i] for i in selected), key=lambda e: e['nome'].casefold())
    for staff in days.values():
        staff.sort(key=lambda e: e['nome'].casefold())
    return days, legend
