"""
app.py — ระบบจัดการงานลูกค้า v10 (Fixed)
Bugs fixed:
  1. /model route: was creating empty task on every GET → now just renders template
  2. get_qr_image(): returned 'promptpay.ext' → now returns 'qr/promptpay.ext'
  3. upload_slip: read 'slip_file' field → now reads 'slip'
  4. payment(): passed slip= single object → now passes slips= full list
  5. ticket.html: used wrong field names → fixed to use correct ticket fields
  6. todos.json not initialized → added to _init loop
  7. .env encoding: auto-fix UTF-8 on startup
"""
import json, os, uuid, secrets as _secrets, io as _io
from datetime import datetime, date, timedelta
from functools import wraps
from collections import defaultdict

from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, make_response, send_from_directory)

from promptpay import generate_promptpay_payload
from queue_manager import (
    read_queue, read_calendar, write_calendar,
    sync_queue, reorder_queue, set_task_estimate,
    get_queue_with_tasks, yearly_analytics,
    add_custom_date, remove_custom_date, update_calendar_settings,
    working_days_count, MONTH_TH
)

try:
    from pdf_generator import generate_order_pdf, generate_spec_sheet
    PDF_ENABLED = True
except Exception:
    PDF_ENABLED = False
    generate_spec_sheet = None

try:
    from line_handler import handle_events, verify_signature
    LINE_ENABLED = True
except Exception:
    LINE_ENABLED = False

# ── FIX 7: Auto-fix .env encoding on startup (Windows cp1252 → UTF-8) ──────────
def _fix_env_encoding():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_path): return
    for enc in ('utf-8', 'utf-8-sig', 'cp1252', 'tis-620', 'latin-1'):
        try:
            with open(env_path, 'r', encoding=enc) as f: text = f.read()
            with open(env_path, 'w', encoding='utf-8') as f: f.write(text)
            break
        except (UnicodeDecodeError, LookupError): continue
_fix_env_encoding()

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-in-production')

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

PREFERRED_SCHEME = os.environ.get('PREFERRED_SCHEME', '')
UPLOAD_FOLDER    = 'uploads'
QR_FOLDER        = os.path.join(UPLOAD_FOLDER, 'qr')
SLIP_FOLDER      = os.path.join(UPLOAD_FOLDER, 'slips')
PRODUCT_IMG_FOLDER = os.path.join(UPLOAD_FOLDER, 'products')
ALLOWED_IMG      = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MODEL_3D_FOLDER  = os.path.join(UPLOAD_FOLDER, '3d_models')
ALLOWED_3D       = {'stl', 'obj', 'step', 'stp', '3mf', 'iges', 'igs', 'f3d', 'blend', 'fbx', 'zip'}

for d in [UPLOAD_FOLDER, QR_FOLDER, SLIP_FOLDER, PRODUCT_IMG_FOLDER, MODEL_3D_FOLDER]:
    os.makedirs(d, exist_ok=True)

PROMPTPAY_PHONE  = os.environ.get('PROMPTPAY_PHONE', '0812345678')
COMPANY_NAME     = os.environ.get('COMPANY_NAME', 'ระบบจัดการงานลูกค้า')
STAMPS_TO_REWARD = 10

@app.context_processor
def inject_globals():
    try: cc = cart_count()
    except: cc = 0
    return dict(cart_count=cc, company_name=COMPANY_NAME)

# ── Data init ──────────────────────────────────────────────────────────────────
def _init(path, default):
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False)

# FIX 6: Added todos.json to init list
for p, d in [
    ('tasks.json', []),
    ('users.json', {'admin': 'admin123'}),
    ('stamps.json', {}),
    ('tickets.json', {}),
    ('slips.json', {}),
    ('products.json', []),
    ('orders_cart.json', {}),
    ('sn_counter.json', {'last_sn': 0}),
    ('todos.json', []),          # ← FIX 6
]:
    _init(p, d)

def _r(p, default):
    try:
        with open(p, 'r', encoding='utf-8') as f: return json.load(f)
    except: return default

def _w(p, data):
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

read_tasks    = lambda: _r('tasks.json', [])
write_tasks   = lambda d: _w('tasks.json', d)
read_users    = lambda: _r('users.json', {'admin': 'admin123'})
write_users   = lambda d: _w('users.json', d)
read_stamps   = lambda: _r('stamps.json', {})
write_stamps  = lambda d: _w('stamps.json', d)
read_tickets  = lambda: _r('tickets.json', {})
write_tickets = lambda d: _w('tickets.json', d)
read_slips    = lambda: _r('slips.json', {})
write_slips   = lambda d: _w('slips.json', d)
read_products = lambda: _r('products.json', [])
write_products= lambda d: _w('products.json', d)
read_todos    = lambda: _r('todos.json', [])
write_todos   = lambda d: _w('todos.json', d)
read_sn       = lambda: _r('sn_counter.json', {'last_sn': 0})
write_sn      = lambda d: _w('sn_counter.json', d)

def next_sn() -> str:
    counter = read_sn(); counter['last_sn'] = counter.get('last_sn', 0) + 1; write_sn(counter)
    return f"ORD-{datetime.now().strftime('%Y%m')}-{counter['last_sn']:04d}"

def backfill_sn():
    tasks = read_tasks(); counter = read_sn(); changed = False
    for t in reversed(tasks):
        if not t.get('sn'):
            counter['last_sn'] = counter.get('last_sn', 0) + 1
            t['sn'] = f"ORD-MIGR-{counter['last_sn']:04d}"; changed = True
    if changed: write_sn(counter); write_tasks(tasks)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG

# ── FIX 2: get_qr_image returns correct subpath 'qr/promptpay.ext' ────────────
def get_qr_image():
    """Return 'qr/promptpay.ext' for URL use — file lives at uploads/qr/."""
    for ext in ALLOWED_IMG:
        path = os.path.join(QR_FOLDER, f'promptpay.{ext}')
        if os.path.exists(path):
            return f'qr/promptpay.{ext}'   # FIX 2
    return None

def add_stamp(phone, name=''):
    s = read_stamps()
    if phone not in s:
        s[phone] = {'stamps': 0, 'total_earned': 0, 'rewards_redeemed': 0, 'name': name}
    s[phone]['stamps'] += 1; s[phone]['total_earned'] += 1; write_stamps(s)

def create_ticket(task):
    code = uuid.uuid4().hex[:8].upper(); t = read_tickets()
    t[code] = {'task_id': task['id'], 'customer_name': task['customer']['name'],
               'customer_phone': task['customer']['phone'], 'task_title': task['title'],
               'status': 'active', 'created_at': datetime.now().isoformat(),
               'checked_in_at': None, 'checked_in_by': None}
    write_tickets(t); return code

def build_analytics(tasks):
    sc = defaultdict(int); pc = defaultdict(int)
    for t in tasks: sc[t['status']] += 1; pc[t.get('priority','medium')] += 1
    today = date.today()
    days = [(today - timedelta(days=i)).isoformat() for i in range(13,-1,-1)]
    dc = defaultdict(int)
    for t in tasks: dc[t['createdAt'][:10]] += 1
    n = len(tasks); c = sc.get('completed', 0)
    return {
        'status_labels': ['รอดำเนินการ','กำลังทำ','เสร็จสิ้น','ยกเลิก'],
        'status_values': [sc.get(k,0) for k in ['pending','inprogress','completed','cancelled']],
        'priority_labels': ['เร่งด่วน','ปานกลาง','ไม่เร่งด่วน'],
        'priority_values': [pc.get(k,0) for k in ['high','medium','low']],
        'day_labels': days, 'day_values': [dc[d] for d in days],
        'completion_rate': round(c/n*100,1) if n else 0,
    }

def slip_status_for_task(task_id):
    slips = read_slips(); task_slips = slips.get(task_id, [])
    return task_slips[-1] if task_slips else None

def slips_for_task(task_id):
    """Return all slips for a task as a list."""
    return read_slips().get(task_id, [])

def pending_slips_count():
    return sum(1 for ts in read_slips().values() for s in ts if s.get('status')=='pending')

def get_webhook_url():
    base = request.url_root.rstrip('/')
    if PREFERRED_SCHEME: base = base.replace('http://', f'{PREFERRED_SCHEME}://')
    elif request.headers.get('X-Forwarded-Proto') == 'https': base = base.replace('http://','https://')
    return f"{base}/webhook"

# ── Admin context ──────────────────────────────────────────────────────────────
def admin_context(tasks_override=None):
    all_tasks = read_tasks(); tasks = tasks_override if tasks_override is not None else all_tasks
    stamps = read_stamps(); tickets = read_tickets(); cal = read_calendar()
    yr = date.today().year; slips = read_slips()
    tasks_with_slip = [{**t, 'slip': slip_status_for_task(t['id'])} for t in tasks]
    return dict(
        tasks=tasks_with_slip, username=session.get('username',''),
        stats={'total': len(all_tasks), 'pending': sum(1 for t in all_tasks if t['status']=='pending'),
               'inprogress': sum(1 for t in all_tasks if t['status']=='inprogress'),
               'completed': sum(1 for t in all_tasks if t['status']=='completed')},
        analytics=build_analytics(all_tasks),
        stamps=stamps,
        stamp_stats={'total_customers': len(stamps), 'total_stamps': sum(v['stamps'] for v in stamps.values()),
                     'total_redeemed': sum(v['rewards_redeemed'] for v in stamps.values())},
        tickets=tickets,
        ticket_stats={'total': len(tickets), 'active': sum(1 for t in tickets.values() if t['status']=='active'),
                      'checked_in': sum(1 for t in tickets.values() if t['status']=='checked_in')},
        stamps_to_reward=STAMPS_TO_REWARD, promptpay_phone=PROMPTPAY_PHONE,
        calendar=cal, ya=yearly_analytics(all_tasks, yr, cal),
        queue_tasks=get_queue_with_tasks(all_tasks, cal),
        qr_image=get_qr_image(), all_slips=slips,
        pending_slips=pending_slips_count(), todos=read_todos(),
    )

def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if 'username' not in session: return redirect(url_for('login'))
        return f(*a, **kw)
    return dec

# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('order_form.html', active_page='order')

@app.route('/submit_order', methods=['POST'])
def submit_order():
    tasks = read_tasks()
    task = {
        'id': str(int(datetime.now().timestamp() * 1000)), 'sn': next_sn(),
        'customer': {'name': request.form.get('customer_name',''), 'phone': request.form.get('customer_phone',''), 'email': request.form.get('customer_email','')},
        'title': request.form.get('task_title',''), 'description': request.form.get('task_description',''),
        'priority': request.form.get('priority','medium'), 'deadline': request.form.get('deadline',''),
        'status': 'pending', 'createdBy': 'ลูกค้า',
        'createdAt': datetime.now().isoformat(), 'updatedAt': datetime.now().isoformat(),
    }
    tasks.insert(0, task); write_tasks(tasks); code = create_ticket(task)
    return render_template('order_form.html', success=True, ticket_code=code,
                           customer_name=task['customer']['name'], task_id=task['id'],
                           order_sn=task.get('sn',''), active_page='order')

# ── FIX 1: /model route — was creating empty tasks on every GET ───────────────
@app.route('/model')
def model():
    """3D order form — just renders the template, does NOT create tasks."""
    return render_template('model.html', active_page='model')  # FIX 1

@app.route('/model/submit', methods=['POST'])
def model_submit():
    """3D printing order - full spec + file upload."""
    saved_files = []
    for fkey in ['model_file', 'ref_image']:
        f = request.files.get(fkey)
        if f and f.filename:
            ext = f.filename.rsplit('.', 1)[-1].lower()
            allowed = ALLOWED_3D if fkey == 'model_file' else ALLOWED_IMG
            if ext in allowed:
                fname = str(int(datetime.now().timestamp()*1000)) + '_' + fkey + '.' + ext
                f.save(os.path.join(MODEL_3D_FOLDER, fname))
                saved_files.append({'field': fkey, 'filename': fname, 'original': f.filename, 'ext': ext})

    specs_3d = {
        'material': request.form.get('material', 'PLA'),
        'color':    request.form.get('color', ''),
        'quality':  request.form.get('quality', 'standard'),
        'infill':   request.form.get('infill', '20'),
        'finish':   request.form.get('finish', 'as_printed'),
        'support':  request.form.get('support', 'auto'),
        'quantity': request.form.get('quantity', '1'),
        'size_x':   request.form.get('size_x', ''),
        'size_y':   request.form.get('size_y', ''),
        'size_z':   request.form.get('size_z', ''),
        'scale':    request.form.get('scale', '100'),
        'use_case': request.form.get('use_case', ''),
        'budget':   request.form.get('budget', ''),
        'files':    saved_files,
    }

    qty = specs_3d['quantity']
    mat = specs_3d['material']
    q_map = {'draft':'Draft 0.3mm','standard':'Standard 0.2mm','fine':'Fine 0.1mm','ultra':'Ultra 0.05mm'}
    q = q_map.get(specs_3d['quality'], specs_3d['quality'])
    color_val = specs_3d.get('color') or 'ไม่ระบุ'

    lines = [
        "วัสดุ: " + mat + " | สี: " + color_val,
        "คุณภาพ: " + q + " | Infill: " + specs_3d['infill'] + "%",
        "ผิว: " + specs_3d['finish'] + " | Support: " + specs_3d['support'],
        "จำนวน: " + qty + " ชิ้น",
    ]
    if specs_3d['size_x'] or specs_3d['size_y'] or specs_3d['size_z']:
        lines.append("ขนาด: " + specs_3d['size_x'] + "x" + specs_3d['size_y'] + "x" + specs_3d['size_z'] + " mm")
    if specs_3d['scale'] and specs_3d['scale'] != '100':
        lines[-1] = lines[-1] + " (scale " + specs_3d['scale'] + "%)"
    if specs_3d['use_case']:
        lines.append("วัตถุประสงค์: " + specs_3d['use_case'])
    if specs_3d['budget']:
        lines.append("งบประมาณ: " + specs_3d['budget'])
    extra_desc = request.form.get('task_description', '')
    if extra_desc:
        lines.append("")
        lines.append("รายละเอียดเพิ่มเติม:")
        lines.append(extra_desc)
    if saved_files:
        lines.append("")
        for sf in saved_files:
            lines.append("📎 " + sf['field'] + ": " + sf['original'])
    auto_desc = "\n".join(lines)

    tasks = read_tasks()
    title = request.form.get('task_title', '')
    task = {
        'id':       str(int(datetime.now().timestamp() * 1000)),
        'sn':       next_sn(),
        'customer': {
            'name':  request.form.get('customer_name', ''),
            'phone': request.form.get('customer_phone', ''),
            'email': request.form.get('customer_email', ''),
        },
        'title':       "[3D] " + title + " (" + mat + ", " + qty + " ชิ้น)",
        'description': auto_desc,
        'priority':    request.form.get('priority', 'medium'),
        'deadline':    request.form.get('deadline', ''),
        'status':      'pending',
        'createdBy':   'ลูกค้า (3D)',
        'specs_3d':    specs_3d,
        'createdAt':   datetime.now().isoformat(),
        'updatedAt':   datetime.now().isoformat(),
    }
    tasks.insert(0, task)
    write_tasks(tasks)
    code = create_ticket(task)
    return render_template('model.html', success=True, ticket_code=code,
                           customer_name=task['customer']['name'],
                           task_id=task['id'], order_sn=task.get('sn', ''),
                           saved_files=saved_files, active_page='model')

@app.route('/tracking')
def tracking():
    q = request.args.get('q','').strip().lower()
    if q:
        tasks = read_tasks(); r = tasks
        r = [t for t in r if q in t['customer']['name'].lower() or q in t['customer']['phone'].lower()
             or q in (t.get('sn') or '').lower() or q in t['title'].lower()]
        return render_template('tracking.html', results=r, searched=True, search_q=q, active_page='tracking')
    return render_template('tracking.html', searched=False, active_page='tracking')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ── FIX 4: payment() — pass slips= (full list) instead of slip= (single) ──────
@app.route('/payment/<task_id>')
def payment(task_id):
    tasks = read_tasks(); task = next((t for t in tasks if t['id'] == task_id), None)
    if not task: return 'ไม่พบออเดอร์', 404
    tickets = read_tickets(); code = next((c for c,tk in tickets.items() if tk['task_id']==task_id), '')
    amount = request.args.get('amount', type=float)
    qr_image = get_qr_image()
    payload = generate_promptpay_payload(PROMPTPAY_PHONE, amount) if not qr_image else ''
    return render_template('payment.html', task=task, ticket_code=code,
                           promptpay_payload=payload, promptpay_phone=PROMPTPAY_PHONE,
                           amount=amount, qr_image=qr_image,
                           slips=slips_for_task(task_id))  # FIX 4: slips= list

# ── FIX 3: upload_slip — read 'slip' field not 'slip_file' ────────────────────
@app.route('/upload_slip/<task_id>', methods=['POST'])
def upload_slip(task_id):
    tasks = read_tasks(); task = next((t for t in tasks if t['id']==task_id), None)
    if not task: return 'ไม่พบออเดอร์', 404
    file = request.files.get('slip')   # FIX 3: was 'slip_file'
    if not file or file.filename == '': return redirect(url_for('payment', task_id=task_id)+'?error=no_file')
    if not allowed_file(file.filename): return redirect(url_for('payment', task_id=task_id)+'?error=bad_type')
    ext = file.filename.rsplit('.',1)[1].lower()
    fname = f"{task_id}_{int(datetime.now().timestamp())}.{ext}"
    file.save(os.path.join(SLIP_FOLDER, fname))
    slips = read_slips()
    slips.setdefault(task_id, []).append({'file': f'slips/{fname}', 'uploaded_at': datetime.now().isoformat(),
                                           'status': 'pending', 'note': '', 'amount': request.form.get('amount','')})
    write_slips(slips)
    tickets = read_tickets(); code = next((c for c,tk in tickets.items() if tk['task_id']==task_id), '')
    return render_template('payment.html', task=task, ticket_code=code,
                           promptpay_payload='', promptpay_phone=PROMPTPAY_PHONE,
                           amount=None, qr_image=get_qr_image(),
                           slips=slips_for_task(task_id),  # FIX 4
                           slip_uploaded=True)

@app.route('/order_pdf/<task_id>')
def order_pdf(task_id):
    if not PDF_ENABLED: return 'PDF ไม่พร้อมใช้งาน (ติดตั้ง reportlab)', 500
    try:
        tasks = read_tasks(); task = next((t for t in tasks if t['id']==task_id), None)
        if not task: return 'ไม่พบออเดอร์', 404
        tickets = read_tickets(); code = next((c for c,tk in tickets.items() if tk['task_id']==task_id), '')
        amount = request.args.get('amount', type=float)
        qr_img = get_qr_image(); payload = generate_promptpay_payload(PROMPTPAY_PHONE, amount) if (amount and not qr_img) else ''
        pdf_bytes = generate_order_pdf(task, code, payload, COMPANY_NAME)
        resp = make_response(pdf_bytes)
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'attachment; filename="order_{task_id[-6:]}.pdf"'
        return resp
    except Exception as e:
        return f'เกิดข้อผิดพลาด: {e}', 500

@app.route('/admin/order_pdf/<task_id>')
@admin_required
def admin_order_pdf(task_id):
    if not PDF_ENABLED: return 'PDF ไม่พร้อมใช้งาน', 500
    tasks = read_tasks(); task = next((t for t in tasks if t['id']==task_id), None)
    if not task: return 'ไม่พบ', 404
    tickets = read_tickets(); code = next((c for c,tk in tickets.items() if tk['task_id']==task_id), '')
    inc_qr = request.args.get('qr','0') == '1'; amount = request.args.get('amount', type=float)
    qr_img = get_qr_image(); payload = generate_promptpay_payload(PROMPTPAY_PHONE, amount) if (inc_qr and not qr_img) else ''
    pdf_bytes = generate_order_pdf(task, code, payload, COMPANY_NAME)
    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename="order_{task_id[-6:]}.pdf"'
    return resp

@app.route('/ticket/<code>')
def view_ticket(code):
    tickets = read_tickets(); ticket = tickets.get(code.upper())
    if not ticket: return render_template('ticket.html', error=True, code=code, ticket=None, task=None)
    tasks = read_tasks(); task = next((t for t in tasks if t['id']==ticket['task_id']), None)
    return render_template('ticket.html', ticket=ticket, code=code.upper(), task=task)

@app.route('/checkin', methods=['GET','POST'])
def public_checkin():
    msg = None; ticket = None; code = ''
    if request.method == 'POST':
        code = request.form.get('code','').strip().upper(); tickets = read_tickets()
        if code not in tickets: msg = ('error', f'ไม่พบ Ticket รหัส {code}')
        elif tickets[code]['status'] == 'checked_in':
            msg = ('warning', f'Check-in แล้วเมื่อ {tickets[code]["checked_in_at"][:16].replace("T"," ")}'); ticket = tickets[code]
        else:
            tickets[code].update({'status':'checked_in','checked_in_at':datetime.now().isoformat(),'checked_in_by':'self'})
            write_tickets(tickets); ticket = tickets[code]
            msg = ('success', f'Check-in สำเร็จ! ยินดีต้อนรับ {ticket["customer_name"]} 🎉')
    return render_template('checkin.html', message=msg, ticket=ticket, code=code, active_page='checkin')

@app.route('/webhook', methods=['GET','POST'])
def line_webhook():
    if request.method == 'GET': return jsonify({'status': 'LINE Webhook active'})
    if not LINE_ENABLED: return jsonify({'error': 'LINE not configured'}), 500
    body = request.get_data(); sig = request.headers.get('X-Line-Signature','')
    if not verify_signature(body, sig): return jsonify({'error': 'Bad signature'}), 403
    try: handle_events(json.loads(body).get('events',[]), read_tasks, read_tickets)
    except Exception as e: app.logger.error(f'LINE: {e}')
    return jsonify({'status': 'ok'})

@app.route('/login', methods=['GET','POST'])
def login():
    users = read_users(); ft = len(users) == 0
    if request.method == 'POST':
        u = request.form.get('username',''); p = request.form.get('password','')
        if ft: users[u] = p; write_users(users); session['username'] = u; return redirect(url_for('admin_dashboard'))
        elif u in users and users[u] == p: session['username'] = u; return redirect(url_for('admin_dashboard'))
        else: return render_template('login.html', error='ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', first_time=ft, active_page='login')
    return render_template('login.html', first_time=ft, active_page='login')

@app.route('/logout')
def logout():
    session.pop('username', None); return redirect(url_for('index'))

@app.route('/contact', methods=['GET','POST'])
def contact():
    sent = False
    if request.method == 'POST':
        name = request.form.get('name','').strip(); email = request.form.get('email','').strip()
        phone = request.form.get('phone','').strip()
        if name and (email or phone): sent = True
    return render_template('contact.html', sent=sent, promptpay_phone=PROMPTPAY_PHONE, active_page='contact')

# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', products_count=len(read_products()), **admin_context())

@app.route('/admin/filter/<status>')
@admin_required
def filter_tasks(status):
    all_tasks = read_tasks(); tasks = all_tasks if status=='all' else [t for t in all_tasks if t['status']==status]
    ctx = admin_context(tasks); ctx['current_filter'] = status
    return render_template('admin_dashboard.html', **ctx)

@app.route('/admin/update_status', methods=['POST'])
@admin_required
def update_status():
    task_id = request.form.get('task_id','').strip()
    new_status = request.form.get('new_status','').strip()
    if new_status not in {'pending','inprogress','completed','cancelled'}:
        return jsonify({'status':'error','error':'invalid status'}), 400
    tasks = read_tasks()
    for t in tasks:
        if t['id'] == task_id:
            if new_status == 'completed' and t['status'] != 'completed':
                add_stamp(t['customer']['phone'], t['customer']['name'])
            t['status'] = new_status; t['updatedAt'] = datetime.now().isoformat()
            t['updatedBy'] = session.get('username',''); break
    write_tasks(tasks)
    updated = next((t for t in tasks if t['id']==task_id), None)
    return jsonify({'status':'ok','task':updated})

@app.route('/admin/delete', methods=['POST'])
@admin_required
def delete_task():
    tid = request.form.get('task_id')
    write_tasks([t for t in read_tasks() if t['id']!=tid])
    return jsonify({'status':'ok'})

@app.route('/admin/upload_qr', methods=['POST'])
@admin_required
def upload_qr():
    file = request.files.get('qr')
    if not file or not allowed_file(file.filename):
        return redirect(url_for('line_config')+'?error=bad_file')
    for ext in ALLOWED_IMG:
        old = os.path.join(QR_FOLDER, f'promptpay.{ext}')
        if os.path.exists(old): os.remove(old)
    ext = file.filename.rsplit('.',1)[1].lower()
    file.save(os.path.join(QR_FOLDER, f'promptpay.{ext}'))
    return redirect(url_for('line_config')+'?qr_saved=1')

@app.route('/admin/delete_qr', methods=['POST'])
@admin_required
def delete_qr():
    for ext in ALLOWED_IMG:
        p = os.path.join(QR_FOLDER, f'promptpay.{ext}')
        if os.path.exists(p): os.remove(p)
    return redirect(url_for('line_config'))

@app.route('/admin/verify_slip', methods=['POST'])
@admin_required
def verify_slip():
    task_id = request.form.get('task_id',''); slip_idx = int(request.form.get('slip_idx',0))
    action = request.form.get('action','approve'); note = request.form.get('note','')
    slips = read_slips(); task_slips = slips.get(task_id, [])
    if 0 <= slip_idx < len(task_slips):
        task_slips[slip_idx]['status'] = 'approved' if action=='approve' else 'rejected'
        task_slips[slip_idx]['note'] = note; task_slips[slip_idx]['verified_at'] = datetime.now().isoformat()
        task_slips[slip_idx]['verified_by'] = session.get('username','')
        if action == 'approve':
            tasks = read_tasks()
            for t in tasks:
                if t['id']==task_id and t['status']=='pending':
                    t['status']='inprogress'; t['updatedAt']=datetime.now().isoformat()
            write_tasks(tasks)
    write_slips(slips)
    return jsonify({'status':'ok','slip_status': task_slips[slip_idx]['status'] if 0 <= slip_idx < len(task_slips) else ''})

@app.route('/admin/redeem_stamp', methods=['POST'])
@admin_required
def redeem_stamp():
    phone = request.form.get('phone',''); s = read_stamps()
    if phone in s and s[phone]['stamps'] >= STAMPS_TO_REWARD:
        s[phone]['stamps'] -= STAMPS_TO_REWARD; s[phone]['rewards_redeemed'] += 1; write_stamps(s)
    s = read_stamps()
    return jsonify({'status':'ok','stamps': s.get(phone,{}).get('stamps',0), 'redeemed': s.get(phone,{}).get('rewards_redeemed',0)})

@app.route('/admin/add_stamp_manual', methods=['POST'])
@admin_required
def add_stamp_manual():
    phone = request.form.get('phone','').strip(); name = request.form.get('name','').strip()
    if phone: add_stamp(phone, name)
    s = read_stamps()
    return jsonify({'status':'ok','phone':phone,'stamps': s.get(phone,{}).get('stamps',0)})

@app.route('/admin/checkin_ticket', methods=['POST'])
@admin_required
def admin_checkin_ticket():
    code = request.form.get('code','').strip().upper(); tickets = read_tickets()
    if code in tickets and tickets[code]['status']=='active':
        tickets[code].update({'status':'checked_in','checked_in_at':datetime.now().isoformat(),'checked_in_by':session.get('username','')})
        write_tickets(tickets)
    return jsonify({'status':'ok','code':code})

@app.route('/admin/queue/reorder', methods=['POST'])
@admin_required
def api_reorder_queue():
    data = request.get_json(silent=True) or {}; reorder_queue(data.get('order',[])); return jsonify({'status':'ok'})

@app.route('/admin/queue/estimate', methods=['POST'])
@admin_required
def api_set_estimate():
    set_task_estimate(request.form.get('task_id',''), float(request.form.get('hours',0) or 0), request.form.get('note',''))
    return jsonify({'status':'ok'})

@app.route('/admin/calendar/settings', methods=['POST'])
@admin_required
def api_calendar_settings():
    work_days = [int(d) for d in request.form.getlist('work_days')]
    update_calendar_settings(work_days, int(request.form.get('capacity',3)))
    return jsonify({'status':'ok'})

@app.route('/admin/calendar/add_date', methods=['POST'])
@admin_required
def api_add_date():
    ds = request.form.get('date',''); dtype = request.form.get('type','holiday'); note = request.form.get('note','')
    if ds: add_custom_date(ds, dtype, note)
    return jsonify({'status':'ok'})

@app.route('/admin/calendar/remove_date', methods=['POST'])
@admin_required
def api_remove_date():
    ds = request.form.get('date','')
    if ds: remove_custom_date(ds)
    return jsonify({'status':'ok'})

@app.route('/admin/api/yearly/<int:year>')
@admin_required
def api_yearly(year):
    return jsonify(yearly_analytics(read_tasks(), year, read_calendar()))

@app.route('/admin/line_config', methods=['GET','POST'])
@admin_required
def line_config():
    msg = None; qr_saved = request.args.get('qr_saved') == '1'
    if request.method == 'POST':
        lines = []
        for k in ['LINE_CHANNEL_ACCESS_TOKEN','LINE_CHANNEL_SECRET','ADMIN_LINE_USER_ID',
                  'PROMPTPAY_PHONE','COMPANY_NAME','PREFERRED_SCHEME']:
            v = request.form.get(k,'').strip()
            if v: os.environ[k] = v; lines.append(f"{k}={v}")
        if lines:
            with open('.env', 'w', encoding='utf-8') as f: f.write('\n'.join(lines)+'\n')
        msg = 'บันทึกเรียบร้อย — รีสตาร์ทเซิร์ฟเวอร์เพื่อให้มีผล'
    return render_template('line_config.html', msg=msg, qr_saved=qr_saved, qr_image=get_qr_image(),
                           token=os.environ.get('LINE_CHANNEL_ACCESS_TOKEN',''),
                           secret=os.environ.get('LINE_CHANNEL_SECRET',''),
                           admin_id=os.environ.get('ADMIN_LINE_USER_ID',''),
                           promptpay=PROMPTPAY_PHONE, company=COMPANY_NAME, scheme=PREFERRED_SCHEME,
                           webhook_url=get_webhook_url())

@app.route('/admin/todos/add', methods=['POST'])
@admin_required
def admin_todos_add():
    todos = read_todos()
    todo = {'id': str(int(datetime.now().timestamp()*1000)), 'text': request.form.get('text','').strip(),
            'done': False, 'priority': request.form.get('priority','medium'), 'due': request.form.get('due',''),
            'createdAt': datetime.now().isoformat()}
    if not todo['text']: return jsonify({'status':'error','error':'empty'}), 400
    todos.insert(0, todo); write_todos(todos)
    return jsonify({'status':'ok','todo':todo})

@app.route('/admin/todos/toggle/<tid>', methods=['POST'])
@admin_required
def admin_todos_toggle(tid):
    todos = read_todos()
    for t in todos:
        if t['id']==tid: t['done'] = not t['done']; break
    write_todos(todos); return jsonify({'status':'ok'})

@app.route('/admin/todos/delete/<tid>', methods=['POST'])
@admin_required
def admin_todos_delete(tid):
    write_todos([t for t in read_todos() if t['id']!=tid]); return jsonify({'status':'ok'})

# ── Product catalog ────────────────────────────────────────────────────────────
def _cart_key():
    if 'cart_id' not in session: session['cart_id'] = _secrets.token_hex(16)
    return session['cart_id']

def get_cart():
    cid = _cart_key(); carts = _r('orders_cart.json', {}); return carts.get(cid, [])

def save_cart(items):
    cid = _cart_key(); carts = _r('orders_cart.json', {}); carts[cid] = items; _w('orders_cart.json', carts)

def cart_count(): return sum(i['qty'] for i in get_cart())

@app.route('/catalog')
def catalog():
    products = [p for p in read_products() if p.get('active', True)]
    category = request.args.get('cat',''); search = request.args.get('q','').lower()
    cats = sorted({p.get('category','') for p in products if p.get('category')})
    if category: products = [p for p in products if p.get('category','')==category]
    if search: products = [p for p in products if search in p['name'].lower() or search in p.get('description','').lower()]
    return render_template('catalog.html', products=products, categories=cats, active_cat=category, search=search)

@app.route('/product/<pid>')
def product_detail(pid):
    products = read_products(); product = next((p for p in products if p['id']==pid), None)
    if not product or not product.get('active',True): return redirect(url_for('catalog'))
    return render_template('product_detail.html', product=product)

@app.route('/cart')
def view_cart():
    cart = get_cart(); products = read_products(); pid_map = {p['id']:p for p in products}
    items = []; total = 0
    for item in cart:
        p = pid_map.get(item['product_id'])
        if p:
            subtotal = p['price'] * item['qty']; total += subtotal
            items.append({**item,'product':p,'subtotal':subtotal})
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add', methods=['POST'])
def cart_add():
    pid = request.form.get('product_id',''); qty = max(1, int(request.form.get('qty',1)))
    back = request.form.get('back', url_for('catalog'))
    products = read_products(); product = next((p for p in products if p['id']==pid and p.get('active',True)), None)
    if not product: return redirect(back)
    cart = get_cart()
    for item in cart:
        if item['product_id']==pid:
            item['qty'] = min(item['qty']+qty, product.get('stock',9999)); break
    else: cart.append({'product_id':pid,'qty':qty})
    save_cart(cart)
    if request.form.get('buy_now'): return redirect(url_for('cart_checkout'))
    return redirect(back)

@app.route('/cart/update', methods=['POST'])
def cart_update():
    pid = request.form.get('product_id',''); qty = int(request.form.get('qty',0))
    products = read_products(); product = next((p for p in products if p['id']==pid), None)
    cart = get_cart()
    if qty <= 0: cart = [i for i in cart if i['product_id']!=pid]
    else:
        stock = product.get('stock') if product else None
        if stock is not None: qty = min(qty, stock)
        for item in cart:
            if item['product_id']==pid: item['qty']=qty; break
    save_cart(cart); return redirect(url_for('view_cart'))

@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    pid = request.form.get('product_id',''); save_cart([i for i in get_cart() if i['product_id']!=pid])
    return redirect(url_for('view_cart'))

@app.route('/cart/checkout', methods=['GET','POST'])
def cart_checkout():
    cart = get_cart()
    if not cart: return redirect(url_for('catalog'))
    products = read_products(); pid_map = {p['id']:p for p in products}
    items = []; total = 0
    for item in cart:
        p = pid_map.get(item['product_id'])
        if p:
            subtotal = p['price']*item['qty']; total += subtotal
            items.append({**item,'product':p,'subtotal':subtotal})
    if request.method == 'POST':
        name = request.form.get('name',''); phone = request.form.get('phone','')
        email = request.form.get('email',''); addr = request.form.get('address','')
        tasks = read_tasks()
        desc = 'สินค้า:\n' + '\n'.join(f'- {i["product"]["name"]} x{i["qty"]}  ฿{i["subtotal"]:.0f}' for i in items) + f'\n\nที่อยู่จัดส่ง: {addr}'
        task = {'id': str(int(datetime.now().timestamp()*1000)), 'sn': next_sn(),
                'customer': {'name':name,'phone':phone,'email':email},
                'title': f'คำสั่งซื้อออนไลน์ ({len(items)} รายการ)', 'description': desc,
                'priority': 'medium', 'deadline': '', 'status': 'pending', 'createdBy': 'ลูกค้า (cart)',
                'createdAt': datetime.now().isoformat(), 'updatedAt': datetime.now().isoformat(),
                'order_total': total}
        tasks.insert(0, task); write_tasks(tasks); create_ticket(task); save_cart([])
        for item in items:
            for p in products:
                if p['id']==item['product_id'] and p.get('stock') is not None:
                    p['stock'] = max(0, p['stock']-item['qty'])
        write_products(products)
        return redirect(url_for('payment', task_id=task['id'])+f'?amount={total:.0f}')
    return render_template('checkout.html', items=items, total=total)

@app.route('/admin/products')
@admin_required
def admin_products():
    return render_template('admin_products.html', products=read_products(), username=session.get('username',''))

@app.route('/admin/products/add', methods=['POST'])
@admin_required
def admin_product_add():
    products = read_products(); pid = str(int(datetime.now().timestamp()*1000))
    stock_val = request.form.get('stock','').strip()
    product = {'id':pid, 'name':request.form.get('name','').strip(),
               'description':request.form.get('description','').strip(),
               'price':float(request.form.get('price',0) or 0),
               'category':request.form.get('category','').strip(),
               'stock':int(stock_val) if stock_val else None,
               'active':request.form.get('active')=='on', 'image':'',
               'createdAt':datetime.now().isoformat()}
    file = request.files.get('image')
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.',1)[1].lower(); fname = f'{pid}.{ext}'
        file.save(os.path.join(PRODUCT_IMG_FOLDER, fname)); product['image'] = f'products/{fname}'
    products.insert(0, product); write_products(products)
    return jsonify({'status':'ok','id':pid,'name':product['name']})

@app.route('/admin/products/edit/<pid>', methods=['POST'])
@admin_required
def admin_product_edit(pid):
    products = read_products(); updated_name = ''
    for p in products:
        if p['id']==pid:
            p['name'] = request.form.get('name',p['name']).strip()
            p['description'] = request.form.get('description',p.get('description','')).strip()
            try: p['price'] = float(request.form.get('price',p['price']) or 0)
            except: pass
            stock_val = request.form.get('stock','').strip()
            p['stock'] = int(stock_val) if stock_val else None
            p['category'] = request.form.get('category',p.get('category','')).strip()
            p['active'] = request.form.get('active','off') == 'on'
            updated_name = p['name']
            file = request.files.get('image')
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.',1)[1].lower(); fname = f'{pid}.{ext}'
                file.save(os.path.join(PRODUCT_IMG_FOLDER, fname)); p['image'] = f'products/{fname}'
            break
    write_products(products); return jsonify({'status':'ok','name':updated_name})

@app.route('/admin/products/delete/<pid>', methods=['POST'])
@admin_required
def admin_product_delete(pid):
    write_products([p for p in read_products() if p['id']!=pid])
    for ext in ALLOWED_IMG:
        path = os.path.join(PRODUCT_IMG_FOLDER, f'{pid}.{ext}')
        if os.path.exists(path): os.remove(path)
    return jsonify({'status':'ok'})

@app.route('/admin/products/toggle/<pid>', methods=['POST'])
@admin_required
def admin_product_toggle(pid):
    products = read_products()
    for p in products:
        if p['id']==pid: p['active'] = not p.get('active',True); break
    write_products(products); return jsonify({'status':'ok'})

@app.route('/admin/export_excel')
@admin_required
def export_excel():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        tasks = read_tasks(); slips = read_slips()
        wb = Workbook(); ws = wb.active; ws.title = 'Orders'
        headers = ['SN','ชื่องาน','ชื่อลูกค้า','เบอร์โทร','สถานะ','ความเร่งด่วน','กำหนดส่ง','วันที่สร้าง']
        for col, h in enumerate(headers, 1): ws.cell(row=1, column=col, value=h).font = Font(bold=True)
        for i, task in enumerate(tasks, 2):
            ws.cell(row=i, column=1, value=task.get('sn',''))
            ws.cell(row=i, column=2, value=task.get('title',''))
            ws.cell(row=i, column=3, value=task['customer']['name'])
            ws.cell(row=i, column=4, value=task['customer']['phone'])
            ws.cell(row=i, column=5, value=task.get('status',''))
            ws.cell(row=i, column=6, value=task.get('priority',''))
            ws.cell(row=i, column=7, value=task.get('deadline',''))
            ws.cell(row=i, column=8, value=task.get('createdAt','')[:10])
        buf = _io.BytesIO(); wb.save(buf)
        fname = f'orders_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        resp = make_response(buf.getvalue())
        resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp
    except Exception as e: return f'เกิดข้อผิดพลาด: {e}', 500

# ── Spec Sheet PDF ────────────────────────────────────────────────────────────
@app.route('/admin/spec_sheet/<task_id>')
@admin_required
def admin_spec_sheet(task_id):
    if not PDF_ENABLED or not generate_spec_sheet:
        return 'PDF ไม่พร้อมใช้งาน', 500
    tasks = read_tasks()
    task  = next((t for t in tasks if t['id'] == task_id), None)
    if not task: return 'ไม่พบ', 404
    pdf_bytes = generate_spec_sheet(task, COMPANY_NAME)
    resp = make_response(pdf_bytes)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = f'inline; filename="spec_{task_id[-6:]}.pdf"'
    return resp

# ── 3D File viewer (list files for a task) ────────────────────────────────────
@app.route('/admin/task_files/<task_id>')
@admin_required
def admin_task_files(task_id):
    tasks = read_tasks()
    task  = next((t for t in tasks if t['id'] == task_id), None)
    if not task: return jsonify({'error': 'not found'}), 404
    files = task.get('specs_3d', {}).get('files', [])
    # Build URLs
    file_list = []
    for sf in files:
        fname = sf.get('filename', '')
        path  = os.path.join(MODEL_3D_FOLDER, fname)
        file_list.append({
            **sf,
            'url':    f'/uploads/3d_models/{fname}',
            'exists': os.path.exists(path),
            'size':   os.path.getsize(path) if os.path.exists(path) else 0,
        })
    return jsonify({'task_id': task_id, 'title': task.get('title',''), 'files': file_list})

# ── Customer Accounts ──────────────────────────────────────────────────────────
def read_customers():  return _r('customers.json', {})
def write_customers(d): _w('customers.json', d)

_init('customers.json', {})

import hashlib as _hashlib
def _hash_pw(pw): return _hashlib.sha256(pw.encode()).hexdigest()

@app.route('/customer/register', methods=['GET','POST'])
def customer_register():
    error = None; success = False
    if request.method == 'POST':
        name  = request.form.get('name','').strip()
        phone = request.form.get('phone','').strip()
        email = request.form.get('email','').strip().lower()
        pw    = request.form.get('password','')
        pw2   = request.form.get('password2','')
        customers = read_customers()
        if not name or not phone or not pw:
            error = 'กรุณากรอกข้อมูลให้ครบถ้วน'
        elif phone in customers:
            error = 'เบอร์โทรนี้ลงทะเบียนแล้ว กรุณาเข้าสู่ระบบ'
        elif len(pw) < 6:
            error = 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร'
        elif pw != pw2:
            error = 'รหัสผ่านไม่ตรงกัน'
        else:
            customers[phone] = {
                'name': name, 'phone': phone, 'email': email,
                'password': _hash_pw(pw),
                'created_at': datetime.now().isoformat(),
            }
            write_customers(customers)
            session['customer_phone'] = phone
            session['customer_name']  = name
            return redirect('/customer/dashboard')
    return render_template('customer_register.html', error=error, active_page='register')

@app.route('/customer/login', methods=['GET','POST'])
def customer_login():
    error = None
    if request.method == 'POST':
        phone = request.form.get('phone','').strip()
        pw    = request.form.get('password','')
        customers = read_customers()
        c = customers.get(phone)
        if not c or c['password'] != _hash_pw(pw):
            error = 'เบอร์โทรหรือรหัสผ่านไม่ถูกต้อง'
        else:
            session['customer_phone'] = phone
            session['customer_name']  = c['name']
            return redirect('/customer/dashboard')
    return render_template('customer_login.html', error=error, active_page='clogin')

@app.route('/customer/logout')
def customer_logout():
    session.pop('customer_phone', None)
    session.pop('customer_name',  None)
    return redirect('/')

@app.route('/customer/dashboard')
def customer_dashboard():
    phone = session.get('customer_phone')
    if not phone: return redirect('/customer/login')
    tasks = [t for t in read_tasks() if t['customer']['phone'] == phone]
    tasks.sort(key=lambda t: t.get('createdAt',''), reverse=True)
    customers = read_customers()
    customer  = customers.get(phone, {})
    slips     = read_slips()
    # Attach slip info
    tasks_with_info = []
    for t in tasks:
        tc = dict(t)
        tc['slips'] = slips.get(t['id'], [])
        tasks_with_info.append(tc)
    return render_template('customer_dashboard.html',
                           customer=customer, tasks=tasks_with_info,
                           active_page='customer_dash')

@app.route('/customer/profile', methods=['GET','POST'])
def customer_profile():
    phone = session.get('customer_phone')
    if not phone: return redirect('/customer/login')
    customers = read_customers()
    customer  = customers.get(phone, {})
    message   = None; error = None
    if request.method == 'POST':
        name  = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        pw    = request.form.get('new_password','')
        pw2   = request.form.get('new_password2','')
        if name:
            customer['name']  = name
            session['customer_name'] = name
        if email:
            customer['email'] = email
        if pw:
            if len(pw) < 6:
                error = 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร'
            elif pw != pw2:
                error = 'รหัสผ่านใหม่ไม่ตรงกัน'
            else:
                customer['password'] = _hash_pw(pw)
                message = 'อัปเดตข้อมูลเรียบร้อย'
        if not error:
            customers[phone] = customer
            write_customers(customers)
            message = message or 'อัปเดตข้อมูลเรียบร้อย'
    return render_template('customer_profile.html', customer=customer,
                           message=message, error=error, active_page='customer_profile')

# ── Startup ────────────────────────────────────────────────────────────────────
with app.app_context():
    backfill_sn()

if __name__ == '__main__':
    if os.path.exists('.env'):
        with open('.env', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
    app.run(debug=True, port=5000)
