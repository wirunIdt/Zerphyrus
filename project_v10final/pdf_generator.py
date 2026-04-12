"""
pdf_generator.py — สร้าง PDF ใบสั่งงาน
ใช้ reportlab (pure-Python) — ไม่ต้อง wkhtmltopdf
รองรับ Thai font อัตโนมัติ, fallback เป็น Helvetica เมื่อไม่มี font ไทย
"""
import io, os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Font: ลองหา Thai font, fallback เป็น built-in Helvetica ────────────────
_THAI_FONT_SEARCH = [
    # Ubuntu/Debian
    ('/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
     '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf'),
    # Loma (Thai)
    ('/usr/share/fonts/truetype/tlwg/Loma.ttf',
     '/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf'),
    # macOS (has basic Thai support in some fonts)
    ('/Library/Fonts/Arial Unicode.ttf', None),
    # Common Windows paths
    ('C:/Windows/Fonts/tahoma.ttf', 'C:/Windows/Fonts/tahomabd.ttf'),
    ('C:/Windows/Fonts/arial.ttf',  'C:/Windows/Fonts/arialbd.ttf'),
]

FONT_NORMAL = 'Helvetica'       # built-in fallback (always works)
FONT_BOLD   = 'Helvetica-Bold'  # built-in fallback

def _try_register_thai():
    global FONT_NORMAL, FONT_BOLD
    for norm_path, bold_path in _THAI_FONT_SEARCH:
        if os.path.exists(norm_path):
            try:
                pdfmetrics.registerFont(TTFont('_ThaiN', norm_path))
                if bold_path and os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont('_ThaiB', bold_path))
                else:
                    pdfmetrics.registerFont(TTFont('_ThaiB', norm_path))
                FONT_NORMAL = '_ThaiN'
                FONT_BOLD   = '_ThaiB'
                return True
            except Exception:
                pass
    return False  # Use built-in Helvetica

_try_register_thai()

# ── Colours ────────────────────────────────────────────────────────────────
C_PURPLE = colors.HexColor('#7c3aed')
C_INDIGO = colors.HexColor('#4f46e5')
C_PLITE  = colors.HexColor('#ede9fe')
C_PMID   = colors.HexColor('#c4b5fd')
C_DARK   = colors.HexColor('#1e1e2e')
C_GRAY   = colors.HexColor('#6b7280')
C_LGRAY  = colors.HexColor('#f3f4f6')
C_LINE   = colors.HexColor('#e5e7eb')
WHITE    = colors.white

_STATUS_CLR  = {
    'pending':    colors.HexColor('#f59e0b'),
    'inprogress': colors.HexColor('#3b82f6'),
    'completed':  colors.HexColor('#10b981'),
    'cancelled':  colors.HexColor('#ef4444'),
}
_PRIO_CLR = {
    'high':   colors.HexColor('#ef4444'),
    'medium': colors.HexColor('#f59e0b'),
    'low':    colors.HexColor('#10b981'),
}
_STATUS_TH  = {'pending':'รอดำเนินการ','inprogress':'กำลังดำเนินการ',
               'completed':'เสร็จสิ้น','cancelled':'ยกเลิก'}
_PRIORITY_TH = {'high':'เร่งด่วน','medium':'ปานกลาง','low':'ไม่เร่งด่วน'}


def _hex_alpha(clr, alpha='30'):
    """Convert reportlab Color to hex string + alpha suffix (e.g. '#ef444430')."""
    r = int(clr.red   * 255)
    g = int(clr.green * 255)
    b = int(clr.blue  * 255)
    return colors.HexColor(f'#{r:02x}{g:02x}{b:02x}{alpha}')


# ── Style / element helpers ────────────────────────────────────────────────
def _style(sz=10, bold=False, clr=colors.black, align=TA_LEFT, leading=None):
    return ParagraphStyle('',
        fontName=FONT_BOLD if bold else FONT_NORMAL,
        fontSize=sz, textColor=clr, alignment=align,
        leading=leading or sz * 1.5, wordWrap='CJK')

def P(txt, sz=10, bold=False, clr=colors.black, align=TA_LEFT, leading=None):
    return Paragraph(str(txt or ''), _style(sz, bold, clr, align, leading))

def sp(h=3):
    return Spacer(1, h * mm)

def section_hdr(title, cw):
    t = Table([[P(title, 10, bold=True, clr=C_PURPLE)]], colWidths=[cw])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), C_PLITE),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LINEBELOW',     (0,0),(-1,-1), 1.5, C_PURPLE),
    ]))
    return t

def info_row(label, value, cw, lw=0.32):
    t = Table([[P(label,9,clr=C_GRAY), P(value or '—',10,bold=True,clr=C_DARK)]],
              colWidths=[cw*lw, cw*(1-lw)])
    t.setStyle(TableStyle([
        ('TOPPADDING',    (0,0),(-1,-1), 3),
        ('BOTTOMPADDING', (0,0),(-1,-1), 3),
        ('LEFTPADDING',   (0,0),(-1,-1), 0),
        ('RIGHTPADDING',  (0,0),(-1,-1), 0),
        ('LINEBELOW',     (0,0),(-1,-1), 0.4, C_LINE),
        ('VALIGN',        (0,0),(-1,-1), 'TOP'),
    ]))
    return t

def badge_cell(text, clr, w):
    bg = _hex_alpha(clr, '30')
    t = Table([[P(text, 9, bold=True, clr=clr, align=TA_CENTER)]], colWidths=[w])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), bg),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
        ('RIGHTPADDING',  (0,0),(-1,-1), 6),
    ]))
    return t


# ── Header/Footer canvas callback ─────────────────────────────────────────
def _make_callbacks(company, order_id, now_str):
    def draw(cvs, doc):
        W, H = A4
        cvs.saveState()
        # top bar
        cvs.setFillColor(C_INDIGO)
        cvs.rect(0, H - 20*mm, W, 20*mm, fill=1, stroke=0)
        cvs.setFillColor(C_PURPLE)
        cvs.rect(0, H - 20*mm, W * 0.45, 20*mm, fill=1, stroke=0)
        cvs.setFont(FONT_BOLD, 13)
        cvs.setFillColor(WHITE)
        cvs.drawString(12*mm, H - 12*mm, company)
        cvs.setFont(FONT_NORMAL, 8)
        cvs.setFillColor(C_PMID)
        cvs.drawString(12*mm, H - 18*mm, 'ใบคำสั่งงาน / Order Bill')
        cvs.setFont(FONT_NORMAL, 8)
        cvs.setFillColor(C_PLITE)
        cvs.drawRightString(W - 12*mm, H - 12*mm, now_str)
        cvs.drawRightString(W - 12*mm, H - 18*mm, f'หน้า {doc.page}  |  #{order_id}')
        # bottom bar
        cvs.setFillColor(C_DARK)
        cvs.rect(0, 0, W, 9*mm, fill=1, stroke=0)
        cvs.setFont(FONT_NORMAL, 7.5)
        cvs.setFillColor(C_PMID)
        cvs.drawCentredString(W / 2, 3*mm,
            'เอกสารนี้สร้างโดยอัตโนมัติ  ·  กรุณาเก็บรหัส Ticket ไว้เพื่ออ้างอิง')
        cvs.restoreState()
    return draw


# ══════════════════════════════════════════════════════════════════════════
def generate_order_pdf(task: dict, ticket_code: str = '',
                       promptpay_payload: str = '',
                       company_name: str = 'ระบบจัดการงานลูกค้า') -> bytes:
    buf    = io.BytesIO()
    W, H   = A4
    margin = 14 * mm
    cw     = W - 2 * margin

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=24*mm, bottomMargin=13*mm)

    now_str  = datetime.now().strftime('%d/%m/%Y %H:%M')
    status   = task.get('status', 'pending')
    priority = task.get('priority', 'medium')
    sc       = _STATUS_CLR.get(status, C_PURPLE)
    pc       = _PRIO_CLR.get(priority, C_PURPLE)
    created  = task.get('createdAt', '')[:16].replace('T', ' ')
    sn       = task.get('sn', '')

    story = []

    # ── Hero ───────────────────────────────────────────────────────────
    hero = Table([[
        P('ใบคำสั่งงาน', 16, bold=True, clr=C_INDIGO),
        P(f'#{task["id"][-8:]}', 18, bold=True, clr=C_PURPLE, align=TA_RIGHT),
    ]], colWidths=[cw * 0.6, cw * 0.4])
    hero.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), C_PLITE),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('RIGHTPADDING',  (0,0),(-1,-1), 10),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story.append(hero)
    story.append(sp(1))

    # SN + date row
    meta = Table([[
        P(f'SN: {sn}' if sn else '', 9, bold=True, clr=C_PURPLE),
        P(f'สร้างเมื่อ {created}', 9, clr=C_GRAY, align=TA_RIGHT),
    ]], colWidths=[cw * 0.5, cw * 0.5])
    meta.setStyle(TableStyle([
        ('TOPPADDING',    (0,0),(-1,-1), 0),
        ('BOTTOMPADDING', (0,0),(-1,-1), 0),
        ('LEFTPADDING',   (0,0),(-1,-1), 0),
        ('RIGHTPADDING',  (0,0),(-1,-1), 0),
    ]))
    story.append(meta)
    story.append(sp(4))

    # ── Ticket code ────────────────────────────────────────────────────
    if ticket_code:
        tk = Table([
            [P('รหัส Ticket สำหรับ Check-in', 9, clr=C_PMID, align=TA_CENTER)],
            [P(ticket_code, 24, bold=True, clr=WHITE, align=TA_CENTER)],
            [P('เก็บรหัสนี้ไว้เพื่อใช้ตรวจสอบสถานะ', 8, clr=C_PMID, align=TA_CENTER)],
        ], colWidths=[cw])
        tk.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), C_DARK),
            ('TOPPADDING',    (0,0),(-1,-1), 6),
            ('BOTTOMPADDING', (0,0),(-1,-1), 6),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
            ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ]))
        story.append(KeepTogether([tk]))
        story.append(sp(4))

    # ── Customer ───────────────────────────────────────────────────────
    story.append(section_hdr('ข้อมูลลูกค้า', cw))
    story.append(sp(1))
    story.append(info_row('ชื่อลูกค้า', task['customer']['name'], cw))
    story.append(info_row('เบอร์โทร',   task['customer']['phone'], cw))
    if task['customer'].get('email'):
        story.append(info_row('อีเมล', task['customer']['email'], cw))
    story.append(sp(4))

    # ── Order details ──────────────────────────────────────────────────
    story.append(section_hdr('รายละเอียดงาน', cw))
    story.append(sp(1))
    story.append(info_row('ชื่องาน',   task.get('title', ''), cw))
    story.append(info_row('กำหนดส่ง', task.get('deadline') or '—', cw))
    story.append(info_row('สร้างโดย', task.get('createdBy', '—'), cw))
    story.append(sp(2))

    # Description box
    story.append(P('รายละเอียด', 9, clr=C_GRAY))
    story.append(sp(1))
    desc_box = Table([[P(task.get('description') or '—', 10, clr=C_DARK, leading=16)]],
                     colWidths=[cw])
    desc_box.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), C_LGRAY),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('RIGHTPADDING',  (0,0),(-1,-1), 10),
    ]))
    story.append(desc_box)
    story.append(sp(3))

    # Badges row
    bw = (cw - 8) / 2
    badges = Table([[
        badge_cell(f'สถานะ: {_STATUS_TH.get(status, status)}', sc, bw),
        sp(0),
        badge_cell(f'ความเร่งด่วน: {_PRIORITY_TH.get(priority, priority)}', pc, bw),
    ]], colWidths=[bw, 8, bw])
    badges.setStyle(TableStyle([
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0),(-1,-1), 0),
        ('BOTTOMPADDING', (0,0),(-1,-1), 0),
        ('LEFTPADDING',   (0,0),(-1,-1), 0),
        ('RIGHTPADDING',  (0,0),(-1,-1), 0),
    ]))
    story.append(badges)
    story.append(sp(4))

    # ── PromptPay ──────────────────────────────────────────────────────
    if promptpay_payload:
        story.append(section_hdr('ชำระเงินผ่าน PromptPay', cw))
        story.append(sp(2))
        pp = Table([
            [P('นำ Payload ด้านล่างไปสแกนผ่านแอปธนาคาร', 9, clr=C_GRAY, align=TA_CENTER)],
            [P(promptpay_payload, 8, bold=True, clr=C_PURPLE, align=TA_CENTER)],
        ], colWidths=[cw])
        pp.setStyle(TableStyle([
            ('BACKGROUND',   (0,0),(-1,-1), C_PLITE),
            ('TOPPADDING',   (0,0),(-1,-1), 8),
            ('BOTTOMPADDING',(0,0),(-1,-1), 8),
            ('LINEABOVE',    (0,1),(-1,1), 0.5, C_PMID),
        ]))
        story.append(pp)
        story.append(sp(4))

    # ── Signature ──────────────────────────────────────────────────────
    sw = (cw - 12) / 2
    sig = Table([
        [P('ลงชื่อลูกค้า', 9, clr=C_GRAY, align=TA_CENTER),
         sp(0),
         P('ลงชื่อผู้รับงาน', 9, clr=C_GRAY, align=TA_CENTER)],
        [sp(0), sp(0), sp(0)],
        [P('(....................................)', 8, clr=C_GRAY, align=TA_CENTER),
         sp(0),
         P('(....................................)', 8, clr=C_GRAY, align=TA_CENTER)],
        [P('วันที่  ......./......./.......', 8, clr=C_GRAY, align=TA_CENTER),
         sp(0),
         P('วันที่  ......./......./.......', 8, clr=C_GRAY, align=TA_CENTER)],
    ], colWidths=[sw, 12, sw],
       rowHeights=[10*mm, 8*mm, 6*mm, 7*mm])
    sig.setStyle(TableStyle([
        ('ALIGN',         (0,0),(-1,-1), 'CENTER'),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
        ('BACKGROUND',    (0,0),(-1,-1), C_LGRAY),
        ('TOPPADDING',    (0,0),(-1,-1), 2),
        ('BOTTOMPADDING', (0,0),(-1,-1), 2),
        ('LEFTPADDING',   (0,0),(-1,-1), 4),
        ('RIGHTPADDING',  (0,0),(-1,-1), 4),
    ]))
    story.append(KeepTogether([
        section_hdr('ลายเซ็นรับทราบ', cw),
        sp(2), sig,
    ]))

    cb = _make_callbacks(company_name, task['id'][-8:], now_str)
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()
