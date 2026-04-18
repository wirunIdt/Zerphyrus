import json, os
from datetime import datetime, date, timedelta
from collections import defaultdict

QUEUE_FILE    = 'queue.json'
CALENDAR_FILE = 'work_calendar.json'

DEFAULT_QUEUE = {'order': [], 'estimates': {}}
DEFAULT_CAL   = {'work_days_of_week': [0,1,2,3,4], 'capacity_per_day': 3, 'custom_dates': {}}

def _init_files():
    for path, default in [(QUEUE_FILE, DEFAULT_QUEUE), (CALENDAR_FILE, DEFAULT_CAL)]:
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
_init_files()

def _r(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except: return default

def _w(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def read_calendar():  return _r(CALENDAR_FILE, DEFAULT_CAL)
def write_calendar(d): _w(CALENDAR_FILE, d)

def is_working_day(d: date, cal: dict = None) -> bool:
    if cal is None: cal = read_calendar()
    ds = d.isoformat()
    custom = cal.get('custom_dates', {}).get(ds, {})
    t = custom.get('type', '')
    if t == 'extra': return True
    if t in ('holiday', 'off'): return False
    return d.weekday() in cal.get('work_days_of_week', [0,1,2,3,4])

def get_working_days_in_range(start: date, end: date, cal: dict = None) -> list:
    if cal is None: cal = read_calendar()
    days = []; cur = start
    while cur <= end:
        if is_working_day(cur, cal): days.append(cur)
        cur += timedelta(days=1)
    return days

def working_days_count(year: int, cal: dict = None) -> int:
    if cal is None: cal = read_calendar()
    return len(get_working_days_in_range(date(year,1,1), date(year,12,31), cal))

def add_custom_date(date_str, dtype, note=''):
    cal = read_calendar()
    cal.setdefault('custom_dates', {})[date_str] = {'type': dtype, 'note': note}
    write_calendar(cal)

def remove_custom_date(date_str):
    cal = read_calendar(); cal.setdefault('custom_dates', {}).pop(date_str, None); write_calendar(cal)

def update_calendar_settings(work_days, capacity):
    cal = read_calendar(); cal['work_days_of_week'] = work_days; cal['capacity_per_day'] = capacity; write_calendar(cal)

def read_queue():  return _r(QUEUE_FILE, DEFAULT_QUEUE)
def write_queue(d): _w(QUEUE_FILE, d)

PRIORITY_WEIGHT = {'high': 1, 'medium': 2, 'low': 3}

def sync_queue(tasks):
    q = read_queue()
    active_ids = {t['id'] for t in tasks if t['status'] in ('pending','inprogress')}
    q['order'] = [tid for tid in q['order'] if tid in active_ids]
    existing = set(q['order'])
    new_tasks = sorted([t for t in tasks if t['id'] not in existing and t['status'] in ('pending','inprogress')],
                       key=lambda t: (PRIORITY_WEIGHT.get(t.get('priority','medium'), 2), t.get('createdAt','')))
    q['order'].extend(t['id'] for t in new_tasks)
    write_queue(q); return q

def reorder_queue(new_order):
    q = read_queue(); q['order'] = new_order; write_queue(q)

def set_task_estimate(task_id, hours, note=''):
    q = read_queue(); q.setdefault('estimates', {})[task_id] = {'hours': hours, 'note': note}; write_queue(q)

def get_queue_with_tasks(tasks, cal=None):
    if cal is None: cal = read_calendar()
    q = sync_queue(tasks); task_map = {t['id']: t for t in tasks}
    estimates = q.get('estimates', {}); capacity = cal.get('capacity_per_day', 3)
    today = date.today(); cur = today
    while not is_working_day(cur, cal): cur += timedelta(days=1)
    slot_day = cur; slot_used = 0; result = []
    for pos, tid in enumerate(q['order']):
        task = task_map.get(tid)
        if not task: continue
        est = estimates.get(tid, {}); hours = est.get('hours', 0); note = est.get('note', '')
        if slot_used >= capacity:
            slot_day += timedelta(days=1)
            while not is_working_day(slot_day, cal): slot_day += timedelta(days=1)
            slot_used = 0
        slot_used += 1
        result.append({**task, 'queue_pos': pos+1, 'estimated_hours': hours, 'queue_note': note,
                        'estimated_date': slot_day.isoformat(), 'days_until': (slot_day-today).days})
    return result

MONTH_TH = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.']

def _parse_date(s):
    try: return date.fromisoformat(s[:10])
    except: return None

def yearly_analytics(tasks, year=None, cal=None):
    if year is None: year = date.today().year
    if cal is None: cal = read_calendar()
    capacity_per_day = cal.get('capacity_per_day', 3)
    created_this_year   = [t for t in tasks if t.get('createdAt','')[:4] == str(year)]
    completed_this_year = [t for t in tasks if t.get('status')=='completed' and t.get('updatedAt','')[:4]==str(year)]
    monthly_created = defaultdict(int); monthly_completed = defaultdict(int); monthly_cancelled = defaultdict(int)
    for t in created_this_year: monthly_created[int(t['createdAt'][5:7])] += 1
    for t in tasks:
        if t.get('status')=='completed' and t.get('updatedAt','')[:4]==str(year): monthly_completed[int(t['updatedAt'][5:7])] += 1
        if t.get('status')=='cancelled' and t.get('updatedAt','')[:4]==str(year): monthly_cancelled[int(t['updatedAt'][5:7])] += 1
    months = list(range(1,13))
    monthly_workdays = {}; monthly_capacity = {}
    for m in months:
        try:
            import calendar as cal_mod
            last_day = cal_mod.monthrange(year, m)[1]
            wdays = get_working_days_in_range(date(year,m,1), date(year,m,last_day), cal)
            monthly_workdays[m] = len(wdays); monthly_capacity[m] = len(wdays) * capacity_per_day
        except: monthly_workdays[m] = monthly_capacity[m] = 0
    monthly_rate = {m: round(monthly_completed[m]/monthly_capacity[m]*100,1) if monthly_capacity[m] else 0 for m in months}
    lead_times = []
    for t in tasks:
        if t.get('status')=='completed':
            dc = _parse_date(t.get('createdAt','')); dd = _parse_date(t.get('updatedAt',''))
            if dc and dd and dd >= dc: lead_times.append((dd-dc).days)
    avg_lead = round(sum(lead_times)/len(lead_times),1) if lead_times else 0
    max_lead = max(lead_times) if lead_times else 0
    total_work_days_ytd = len(get_working_days_in_range(date(year,1,1), min(date.today(),date(year,12,31)), cal))
    total_capacity_ytd = total_work_days_ytd * capacity_per_day
    ytd_completed = len(completed_this_year)
    ytd_rate = round(ytd_completed/total_capacity_ytd*100,1) if total_capacity_ytd else 0
    best_month = max(months, key=lambda m: monthly_completed[m])
    all_years = sorted(set(int(t['createdAt'][:4]) for t in tasks if t.get('createdAt','')[:4].isdigit())) or [year]
    return {
        'year': year, 'all_years': all_years, 'month_labels': MONTH_TH,
        'monthly_created': [monthly_created[m] for m in months],
        'monthly_completed': [monthly_completed[m] for m in months],
        'monthly_cancelled': [monthly_cancelled[m] for m in months],
        'monthly_capacity': [monthly_capacity[m] for m in months],
        'monthly_workdays': [monthly_workdays[m] for m in months],
        'monthly_rate': [monthly_rate[m] for m in months],
        'total_created': len(created_this_year), 'total_completed': ytd_completed,
        'total_cancelled': len([t for t in tasks if t.get('status')=='cancelled' and t.get('updatedAt','')[:4]==str(year)]),
        'ytd_work_days': total_work_days_ytd, 'ytd_capacity': total_capacity_ytd, 'ytd_rate': ytd_rate,
        'avg_lead_days': avg_lead, 'max_lead_days': max_lead, 'min_lead_days': min(lead_times) if lead_times else 0,
        'best_month': MONTH_TH[best_month-1], 'capacity_per_day': capacity_per_day,
        'total_work_days_year': working_days_count(year, cal),
        'prio_high': sum(1 for t in created_this_year if t.get('priority')=='high'),
        'prio_medium': sum(1 for t in created_this_year if t.get('priority')=='medium'),
        'prio_low': sum(1 for t in created_this_year if t.get('priority')=='low'),
    }
