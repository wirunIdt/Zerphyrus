"""
pdf_generator.py — Order PDF + 3D Spec Sheet
Uses reportlab (pure Python, no wkhtmltopdf needed)
"""
import io, os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Font: try Thai, fallback Helvetica ─────────────────────────────────────────
FONT_NORMAL = 'Helvetica'
FONT_BOLD   = 'Helvetica-Bold'

_THAI_PATHS = [
    ('/usr/share/fonts/truetype/tlwg/Loma.ttf',
     '/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf'),
    ('/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
     '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf'),
    ('C:/Windows/Fonts/tahoma.ttf', 'C:/Windows/Fonts/tahomabd.ttf'),
    ('C:/Windows/Fonts/arial.ttf',  'C:/Windows/Fonts/arialbd.ttf'),
]
for n, b in _THAI_PATHS:
    if os.path.exists(n):
        try:
            pdfmetrics.registerFont(TTFont('_ThaiN', n))
            pdfmetrics.registerFont(TTFont('_ThaiB', b if b and os.path.exists(b) else n))
            FONT_NORMAL, FONT_BOLD = '_ThaiN', '_ThaiB'
            break
        except Exception:
            pass

# ── Colors ─────────────────────────────────────────────────────────────────────
C_INDIGO  = colors.HexColor('#4f46e5')
C_PURPLE  = colors.HexColor('#7c3aed')
C_PLITE   = colors.HexColor('#ede9fe')
C_PMID    = colors.HexColor('#c4b5fd')
C_DARK    = colors.HexColor('#1e1e2e')
C_GRAY    = colors.HexColor('#6b7280')
C_LGRAY   = colors.HexColor('#f3f4f6')
C_LINE    = colors.HexColor('#e5e7eb')
C_GREEN   = colors.HexColor('#10b981')
C_AMBER   = colors.HexColor('#f59e0b')
C_RED     = colors.HexColor('#ef4444')
WHITE     = colors.white

_STATUS_CLR = {'pending': C_AMBER, 'inprogress': colors.HexColor('#3b82f6'),
               'completed': C_GREEN, 'cancelled': C_RED}
_PRIO_CLR   = {'high': C_RED, 'medium': C_AMBER, 'low': C_GREEN}
_STATUS_TH  = {'pending':'รอดำเนินการ','inprogress':'กำลังดำเนินการ',
               'completed':'เสร็จสิ้น','cancelled':'ยกเลิก'}
_PRIORITY_TH= {'high':'เร่งด่วน','medium':'ปานกลาง','low':'ไม่เร่งด่วน'}

def _thin():
    s = colors.HexColor('#D1D5DB')
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus.tables import TableStyle
    from reportlab.lib import colors as C
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Table
    side = colors.HexColor('#D1D5DB')
    from reportlab.platypus.tables import _BCCommand
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.lib import colors
    side = colors.HexColor('#D1D5DB')
    from reportlab.platypus import Table
    from reportlab.platypus.tables import TableStyle
    B = colors.HexColor('#D1D5DB')
    from reportlab.platypus.tables import Border
    pass

from reportlab.platypus.tables import TableStyle
from reportlab.lib.styles import ParagraphStyle

def _border():
    s = colors.HexColor('#D1D5DB')
    from reportlab.lib.styles import ParagraphStyle
    side = ('LINEABOVE', (0,0), (-1,-1), 0.4, s)
    return [('BOX',(0,0),(-1,-1),0.5,s),('INNERGRID',(0,0),(-1,-1),0.3,s)]

def P(txt, sz=9, bold=False, clr=colors.black, align=TA_LEFT, leading=None):
    st = ParagraphStyle('', fontName=FONT_BOLD if bold else FONT_NORMAL,
                        fontSize=sz, textColor=clr, alignment=align,
                        leading=leading or sz*1.5, wordWrap='CJK')
    return Paragraph(str(txt or ''), st)

def sp(h=3): return Spacer(1, h*mm)

def hdr_row(cells, widths, bg=C_INDIGO):
    t = Table([cells], colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), bg),
        ('TEXTCOLOR',(0,0),(-1,-1), WHITE),
        ('FONTNAME',(0,0),(-1,-1), FONT_BOLD),
        ('FONTSIZE',(0,0),(-1,-1), 9),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    return t

def section_title(txt, cw):
    t = Table([[P(txt, 9, bold=True, clr=C_PURPLE)]], colWidths=[cw])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1), C_PLITE),
        ('LEFTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LINEBELOW',(0,0),(-1,-1),1.5, C_PURPLE),
    ]))
    return t

def info_row(label, value, cw, lw=0.32):
    t = Table([[P(label,8,clr=C_GRAY), P(str(value or '—'),9,bold=True,clr=C_DARK)]],
              colWidths=[cw*lw, cw*(1-lw)])
    t.setStyle(TableStyle([
        ('TOPPADDING',(0,0),(-1,-1),3), ('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('LEFTPADDING',(0,0),(-1,-1),0), ('RIGHTPADDING',(0,0),(-1,-1),0),
        ('LINEBELOW',(0,0),(-1,-1),0.4, C_LINE), ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    return t

def _header_footer(company, order_id, now_str):
    def draw(cvs, doc):
        W, H = A4
        cvs.saveState()
        cvs.setFillColor(C_INDIGO); cvs.rect(0, H-18*mm, W, 18*mm, fill=1, stroke=0)
        cvs.setFillColor(C_PURPLE); cvs.rect(0, H-18*mm, W*0.42, 18*mm, fill=1, stroke=0)
        cvs.setFont(FONT_BOLD, 12); cvs.setFillColor(WHITE)
        cvs.drawString(10*mm, H-11*mm, company)
        cvs.setFont(FONT_NORMAL, 7.5); cvs.setFillColor(C_PMID)
        cvs.drawString(10*mm, H-16.5*mm, 'ใบคำสั่งงาน / Order Bill')
        cvs.setFont(FONT_NORMAL, 7.5); cvs.setFillColor(C_PLITE)
        cvs.drawRightString(W-10*mm, H-11*mm, now_str)
        cvs.drawRightString(W-10*mm, H-16.5*mm, f'หน้า {doc.page}  |  #{order_id}')
        cvs.setFillColor(C_DARK); cvs.rect(0, 0, W, 8*mm, fill=1, stroke=0)
        cvs.setFont(FONT_NORMAL, 7); cvs.setFillColor(C_PMID)
        cvs.drawCentredString(W/2, 2.5*mm, 'เอกสารนี้สร้างโดยอัตโนมัติ · กรุณาเก็บรหัส Ticket ไว้เพื่ออ้างอิง')
        cvs.restoreState()
    return draw

# ══════════════════════════════════════════════════════════════════════════════
def generate_order_pdf(task: dict, ticket_code: str = '',
                       promptpay_payload: str = '',
                       company_name: str = 'ShopOS') -> bytes:
    buf = io.BytesIO(); W, H = A4; m = 13*mm; cw = W - 2*m
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=m, rightMargin=m,
                            topMargin=22*mm, bottomMargin=12*mm)
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    status   = task.get('status','pending')
    priority = task.get('priority','medium')
    sc = _STATUS_CLR.get(status, C_PURPLE)
    pc = _PRIO_CLR.get(priority, C_PURPLE)
    story = []

    # Hero
    hero = Table([[P('ใบคำสั่งงาน',14,bold=True,clr=C_INDIGO),
                   P(f"#{task['id'][-8:]}",16,bold=True,clr=C_PURPLE,align=TA_RIGHT)]],
                 colWidths=[cw*0.6, cw*0.4])
    hero.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_PLITE),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(hero); story.append(sp(1))

    meta = Table([[P(f"SN: {task.get('sn','')}" if task.get('sn') else '', 8, bold=True, clr=C_PURPLE),
                   P(f"สร้างเมื่อ {task.get('createdAt','')[:16].replace('T',' ')}", 8, clr=C_GRAY, align=TA_RIGHT)]],
                 colWidths=[cw*0.5, cw*0.5])
    meta.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
                               ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.append(meta); story.append(sp(4))

    # Ticket code
    if ticket_code:
        tk = Table([[P('รหัส Ticket สำหรับ Check-in',8,clr=C_PMID,align=TA_CENTER)],
                    [P(ticket_code,22,bold=True,clr=WHITE,align=TA_CENTER)],
                    [P('เก็บรหัสนี้ไว้เพื่อติดตามสถานะ',7.5,clr=C_PMID,align=TA_CENTER)]],
                   colWidths=[cw])
        tk.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_DARK),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.append(KeepTogether([tk])); story.append(sp(4))

    # Customer
    story.append(section_title('ข้อมูลลูกค้า', cw)); story.append(sp(1))
    story.append(info_row('ชื่อลูกค้า', task['customer']['name'], cw))
    story.append(info_row('เบอร์โทร', task['customer']['phone'], cw))
    if task['customer'].get('email'):
        story.append(info_row('อีเมล', task['customer']['email'], cw))
    story.append(sp(4))

    # Order details
    story.append(section_title('รายละเอียดงาน', cw)); story.append(sp(1))
    story.append(info_row('ชื่องาน', task.get('title',''), cw))
    story.append(info_row('กำหนดส่ง', task.get('deadline') or '—', cw))
    story.append(sp(2))

    # Status badges
    bw = (cw-8)/2
    def badge(txt, clr, w):
        t = Table([[P(txt,8,bold=True,clr=clr,align=TA_CENTER)]], colWidths=[w])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_LGRAY),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        return t
    badges = Table([[badge(f"สถานะ: {_STATUS_TH.get(status,status)}", sc, bw),
                     sp(0),
                     badge(f"ความเร่งด่วน: {_PRIORITY_TH.get(priority,priority)}", pc, bw)]],
                   colWidths=[bw,8,bw])
    badges.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
                                 ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.append(badges); story.append(sp(3))

    # Description
    if task.get('description'):
        story.append(P('รายละเอียด', 8, clr=C_GRAY)); story.append(sp(1))
        desc_box = Table([[P(task['description'], 9, clr=C_DARK, leading=14)]], colWidths=[cw])
        desc_box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_LGRAY),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10)]))
        story.append(desc_box); story.append(sp(3))

    # 3D Specs (if present)
    specs = task.get('specs_3d')
    if specs:
        story.append(section_title('3D Print Specifications', cw)); story.append(sp(1))
        spec_data = [
            ['วัสดุ (Material)', specs.get('material','—'),
             'สี (Color)', specs.get('color','—')],
            ['คุณภาพ (Quality)', specs.get('quality','—').replace('standard','Standard 0.2mm').replace('fine','Fine 0.1mm').replace('draft','Draft 0.3mm').replace('ultra','Ultra 0.05mm'),
             'Infill', specs.get('infill','—')+'%'],
            ['ผิว (Surface)', specs.get('finish','—'),
             'Support', specs.get('support','—')],
            ['จำนวน (Qty)', specs.get('quantity','1')+' ชิ้น',
             'Scale', specs.get('scale','100')+'%'],
        ]
        if any(specs.get(k) for k in ['size_x','size_y','size_z']):
            spec_data.append(['ขนาด (mm)', f"{specs.get('size_x','?')} × {specs.get('size_y','?')} × {specs.get('size_z','?')} mm", 'วัตถุประสงค์', specs.get('use_case','—')])
        if specs.get('budget'):
            spec_data.append(['งบประมาณ', specs.get('budget','—'), '', ''])

        w1, w2, w3, w4 = cw*0.2, cw*0.3, cw*0.2, cw*0.3
        spec_table_data = []
        for row in spec_data:
            spec_table_data.append([
                P(row[0],8,clr=C_GRAY), P(row[1],9,bold=True,clr=C_DARK),
                P(row[2],8,clr=C_GRAY), P(row[3],9,bold=True,clr=C_DARK),
            ])
        spec_t = Table(spec_table_data, colWidths=[w1,w2,w3,w4])
        spec_t.setStyle(TableStyle([
            ('GRID',(0,0),(-1,-1),0.4,C_LINE),
            ('BACKGROUND',(0,0),(0,-1),C_LGRAY), ('BACKGROUND',(2,0),(2,-1),C_LGRAY),
            ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ]))
        story.append(spec_t); story.append(sp(3))

        # Uploaded files list
        if specs.get('files'):
            story.append(P('ไฟล์แนบ:', 8, bold=True, clr=C_GRAY)); story.append(sp(1))
            for sf in specs['files']:
                story.append(P(f"  📎 {sf.get('original','—')} ({sf.get('ext','').upper()})", 8, clr=C_DARK))
            story.append(sp(2))

    # PromptPay
    if promptpay_payload:
        story.append(section_title('ชำระเงินผ่าน PromptPay', cw)); story.append(sp(2))
        pp = Table([[P('Payload PromptPay (สแกนด้วยแอปธนาคาร)', 8, clr=C_GRAY, align=TA_CENTER)],
                    [P(promptpay_payload, 7.5, bold=True, clr=C_PURPLE, align=TA_CENTER)]],
                   colWidths=[cw])
        pp.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_PLITE),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.append(pp); story.append(sp(4))

    # Signature
    sw = (cw-10)/2
    sig = Table([
        [P('ลงชื่อลูกค้า',8,clr=C_GRAY,align=TA_CENTER), sp(0),
         P('ลงชื่อผู้รับงาน',8,clr=C_GRAY,align=TA_CENTER)],
        [sp(0),sp(0),sp(0)],
        [P('(....................................)',7.5,clr=C_GRAY,align=TA_CENTER), sp(0),
         P('(....................................)',7.5,clr=C_GRAY,align=TA_CENTER)],
        [P('วันที่  ......./......./.......',7.5,clr=C_GRAY,align=TA_CENTER), sp(0),
         P('วันที่  ......./......./.......',7.5,clr=C_GRAY,align=TA_CENTER)],
    ], colWidths=[sw,10,sw], rowHeights=[9*mm,8*mm,6*mm,7*mm])
    sig.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('BACKGROUND',(0,0),(-1,-1),C_LGRAY),
        ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]))
    story.append(KeepTogether([section_title('ลายเซ็นรับทราบ', cw), sp(2), sig]))

    cb = _header_footer(company_name, task['id'][-8:], now_str)
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
def generate_spec_sheet(task: dict, company_name: str = 'ShopOS') -> bytes:
    """Generate a dedicated 3D Print Spec Sheet PDF."""
    buf = io.BytesIO(); W, H = A4; m = 13*mm; cw = W - 2*m
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=m, rightMargin=m,
                            topMargin=22*mm, bottomMargin=12*mm)
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    specs = task.get('specs_3d', {})
    story = []

    # Title block
    title_t = Table([[
        P('3D PRINT SPEC SHEET', 18, bold=True, clr=C_INDIGO),
        P(task.get('sn','—'), 12, bold=True, clr=C_PURPLE, align=TA_RIGHT),
    ]], colWidths=[cw*0.65, cw*0.35])
    title_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),C_PLITE),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LINEBELOW',(0,0),(-1,-1),3, C_INDIGO),
    ]))
    story.append(title_t); story.append(sp(3))

    # Job + Customer info side by side
    cust = task.get('customer', {})
    left_rows = [
        ('ชื่องาน', task.get('title','—')),
        ('ลูกค้า', cust.get('name','—')),
        ('เบอร์โทร', cust.get('phone','—')),
        ('อีเมล', cust.get('email','—') or '—'),
        ('วันสั่ง', task.get('createdAt','')[:10]),
        ('กำหนดส่ง', task.get('deadline','—') or '—'),
    ]
    right_rows = [
        ('สถานะ', _STATUS_TH.get(task.get('status',''),'—')),
        ('ความเร่งด่วน', _PRIORITY_TH.get(task.get('priority',''),'—')),
        ('Ticket Code', '—'),
        ('เริ่มพิมพ์', '_______________'),
        ('เสร็จพิมพ์', '_______________'),
        ('ตรวจ QC โดย', '_______________'),
    ]
    hw = cw*0.46; gap = cw*0.08
    def mini_info(rows, w):
        data = [[P(k,7.5,clr=C_GRAY), P(str(v),8.5,bold=True,clr=C_DARK)] for k,v in rows]
        t = Table(data, colWidths=[w*0.38, w*0.62])
        t.setStyle(TableStyle([
            ('GRID',(0,0),(-1,-1),0.3,C_LINE),
            ('BACKGROUND',(0,0),(0,-1),C_LGRAY),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ]))
        return t
    top = Table([[mini_info(left_rows,hw), sp(0), mini_info(right_rows,hw)]],
                colWidths=[hw, gap, hw])
    top.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
                              ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.append(top); story.append(sp(5))

    # 3D Specs full table
    story.append(section_title('PRINT SPECIFICATIONS', cw)); story.append(sp(2))

    q_map = {'standard':'Standard 0.2mm','fine':'Fine 0.1mm',
             'draft':'Draft 0.3mm','ultra':'Ultra 0.05mm'}
    finish_map = {'as_printed':'As Printed','sanded':'Sanded','polished':'Polished','painted':'Painted'}
    support_map = {'auto':'Auto','none':'ไม่ใช้','minimal':'Minimal','full':'Full'}

    SPEC_ROWS = [
        ('วัสดุ (Material)',  specs.get('material','—'),         'สี (Color)',         specs.get('color','—') or '—'),
        ('Layer Height',     q_map.get(specs.get('quality',''),'—'), 'Infill Density',    (specs.get('infill','—') or '—')+'%'),
        ('Surface Finish',   finish_map.get(specs.get('finish',''),'—'), 'Support',      support_map.get(specs.get('support',''),'—')),
        ('จำนวนชิ้น (Qty)', (specs.get('quantity','1') or '1')+' ชิ้น',  'Scale',        (specs.get('scale','100') or '100')+'%'),
        ('ขนาด X (mm)',      specs.get('size_x','—') or '—',    'ขนาด Y (mm)',        specs.get('size_y','—') or '—'),
        ('ขนาด Z (mm)',      specs.get('size_z','—') or '—',    'วัตถุประสงค์',       specs.get('use_case','—') or '—'),
        ('งบประมาณ',         specs.get('budget','—') or '—',    'ไฟล์ต้นแบบ',
         ', '.join(sf.get('original','') for sf in specs.get('files',[])) or '—'),
    ]
    w1,w2,w3,w4 = cw*0.2, cw*0.3, cw*0.2, cw*0.3
    spec_rows_data = [[P(r[0],8,clr=C_GRAY,bold=True), P(r[1],9,clr=C_DARK,bold=True),
                       P(r[2],8,clr=C_GRAY,bold=True), P(r[3],9,clr=C_DARK,bold=True)]
                      for r in SPEC_ROWS]
    spec_t = Table(spec_rows_data, colWidths=[w1,w2,w3,w4])
    spec_t.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.5,C_LINE),
        ('BACKGROUND',(0,0),(0,-1),C_PLITE), ('BACKGROUND',(2,0),(2,-1),C_PLITE),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[WHITE, C_LGRAY]),
    ]))
    story.append(spec_t); story.append(sp(5))

    # QC Checklist
    story.append(section_title('QC CHECKLIST', cw)); story.append(sp(2))
    checks = [
        'ตรวจสอบขนาดชิ้นงานตรงตาม Spec',
        'ตรวจสอบผิวชิ้นงาน ไม่มี Layer Delamination',
        'ตรวจสอบ Infill แน่นสม่ำเสมอ',
        'ตรวจสอบ Support ลอกออกครบถ้วน',
        'ตรวจสอบสี ตรงตามที่สั่ง',
        'ตรวจสอบจำนวนชิ้นครบถ้วน',
        'บรรจุหีบห่อเรียบร้อย',
        'แจ้งลูกค้า / ถ่ายรูปก่อนส่ง',
    ]
    check_data = [[P('☐', 10, clr=C_PURPLE), P(c, 9, clr=C_DARK)] for c in checks]
    check_t = Table(check_data, colWidths=[8*mm, cw-8*mm])
    check_t.setStyle(TableStyle([
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
        ('LINEBELOW',(0,0),(-1,-1),0.3,C_LINE),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[WHITE, C_LGRAY]),
    ]))
    story.append(check_t); story.append(sp(5))

    # Notes
    story.append(section_title('หมายเหตุ / บันทึก Admin', cw)); story.append(sp(1))
    lines_t = Table([[P('', 9)]] * 5, colWidths=[cw])
    lines_t.setStyle(TableStyle([
        ('LINEBELOW',(0,0),(-1,-1),0.6, C_LINE),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(lines_t)

    cb = _header_footer(company_name, task['id'][-8:], now_str)
    doc.build(story, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()
