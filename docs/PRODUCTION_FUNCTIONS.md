# Zerphyrus Production Function Guide

คู่มือนี้สรุปว่าแต่ละฟังก์ชันของระบบใช้ทำอะไร ใช้ยังไง และต้องระวังอะไรเมื่อเปิดใช้จริงเชิงพาณิชย์

## Quick Start

รันจาก root repo:

```powershell
cd C:\Jaochai\Zerphyrus\Zerphyrus
python -m pip install -r project\requirements.txt
python project\app.py
```

เปิดเว็บที่ `http://127.0.0.1:5000`

Admin เริ่มต้น: `admin / admin123`

หมายเหตุ: หลัง login สำเร็จ ระบบจะ upgrade password เก่าที่เป็น plaintext หรือ SHA-256 ให้เป็น hash แบบ bcrypt/scrypt โดยอัตโนมัติ

## Environment Variables

ตั้งค่าใน environment หรือ `.env` ก่อนเปิดใช้จริง:

```text
SECRET_KEY=สุ่มค่าใหม่ยาวๆ
COMPANY_NAME=ชื่อร้าน
PROMPTPAY_PHONE=เบอร์พร้อมเพย์
PREFERRED_SCHEME=https
MONTHLY_REVENUE_TARGET=100000
VAT_RATE=7

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASS=your-password
# หรือ SMTP_PASSWORD=your-password
SMTP_FROM=your@email.com

TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=...
```

## Public Customer Functions

| Function | URL | ใช้ทำอะไร | วิธีใช้ |
| --- | --- | --- | --- |
| Custom Order | `/` | รับงานสั่งทำทั่วไป | ลูกค้ากรอกข้อมูล, ประเภทงาน, ความซับซ้อน, ขนาด, งบ, ไฟล์อ้างอิง แล้วระบบสร้าง order และ draft quote |
| Submit Custom Order | `/submit_order` | บันทึก custom order | ใช้ผ่านฟอร์มหน้า `/` เท่านั้น มี CSRF และรองรับหลายไฟล์ |
| 3D Order | `/model` | รับงาน 3D print | ลูกค้าเลือกวัสดุ, สี, quality, infill, support, finish, ขนาด, deadline และอัปโหลด STL/OBJ/STEP |
| Submit 3D Order | `/model/submit` | บันทึกงาน 3D | ระบบอ่าน STL ด้วย `numpy-stl` ถ้าเป็นไฟล์ STL แล้วคำนวณราคา draft |
| Tracking | `/tracking` | ติดตามงาน | ค้นด้วยชื่อ, เบอร์, order no, หรือชื่องาน |
| Ticket | `/ticket/<code>` | เปิด ticket ของ order | ใช้รหัส ticket หลังส่งงาน |
| Payment | `/payment/<task_id>` | แสดง PromptPay และอัปโหลดสลิป | ถ้า quote approved ระบบดึงยอด deposit หรือ balance ให้อัตโนมัติ |
| Upload Slip | `/upload_slip/<task_id>` | รับสลิปโอนเงิน | ลูกค้าแนบรูปสลิป ระบบแจ้งเตือน admin และรอตรวจ |
| Order PDF | `/order_pdf/<task_id>` | ดาวน์โหลดเอกสาร order | ลูกค้าหรือทีมงานใช้ส่งต่อรายละเอียดงาน |
| Review | `/review/<task_id>` | รีวิวหลังปิดงาน | ใช้กับงาน completed/delivered |
| Gallery | `/gallery` | ผลงานและรีวิว | แสดงงานที่ admin เพิ่มเข้า gallery |
| Customer Register/Login | `/customer/register`, `/customer/login` | บัญชีลูกค้า | ลูกค้าดู order history, quote, payment, profile |

## Admin Functions

| Function | URL | ใช้ทำอะไร | วิธีใช้ |
| --- | --- | --- | --- |
| Dashboard | `/admin` | ศูนย์ควบคุมงาน | ดูงาน, สถานะ, quote, payment, queue, calendar, CRM, analytics |
| Filter Tasks | `/admin/filter/<status>` | กรองงาน | ใช้ pill filter ใน dashboard |
| Update Status | `/admin/update_status` | เปลี่ยนสถานะงานเดี่ยว | เลือก status ใน task card ระบบบันทึก timeline และแจ้ง Email/SMS ถ้าตั้งค่าไว้ |
| Bulk Status | `/admin/bulk/status` | เปลี่ยนสถานะหลายงาน | ติ๊ก checkbox หลาย task แล้วเลือก Bulk status |
| Delete Task | `/admin/delete` | ลบงาน | ใช้ปุ่มลบใน task card |
| Quote | `/admin/quote` | ส่งใบเสนอราคา | กด Quote ใน task, ใส่ amount, deposit percent, note |
| Timeline | `/admin/task_events/<task_id>` | ดูประวัติงาน | กด Timeline ใน task card |
| Comment/Note | `/task/comment` | เพิ่ม note หรือข้อความใน timeline | Admin เพิ่มจาก timeline modal, ลูกค้าเพิ่มได้ถ้าเป็นเจ้าของงาน |
| Notifications | `/admin/notifications` | ข้อมูล bell icon | ใช้ polling ทุก 30 วินาที |
| Invoice PDF | `/admin/invoice/<task_id>` | ออกใบแจ้งหนี้/ใบเสร็จเบื้องต้น | ดึงยอดจาก quote/order total, คำนวณ VAT, running invoice number |
| Backup | `/admin/backup` | สำรอง JSON และ uploads | ดาวน์โหลด ZIP |
| Restore | `/admin/restore` | กู้ข้อมูล | อัปโหลด ZIP backup |
| SQLite Export | `/admin/migrate_sqlite` | export JSON ไป SQLite | ใช้เตรียมย้ายฐานข้อมูลจริง |
| CRM Detail | `/admin/customer/<phone>` | ประวัติลูกค้า | เปิดจากปุ่ม Customer หรือ CRM tab |
| CRM Tags | `/admin/customer/<phone>/tags` | tag/note ลูกค้า | ใช้ tag เช่น VIP, เครดิต, blacklist |
| Gallery Add | `/admin/gallery/add` | เพิ่มผลงาน | ใช้ทำหน้า public gallery |
| Job Sheet | `/admin/job_sheet/<task_id>` | ใบงานภายใน | ใช้กับงานผลิตและ QC |
| QR Upload/Delete | `/admin/upload_qr`, `/admin/delete_qr` | ตั้งค่า QR PromptPay | ใช้หน้า settings |
| Verify Slip | `/admin/verify_slip` | อนุมัติ/ปฏิเสธสลิป | ใช้ tab Slips |
| Stamp/Loyalty | `/admin/add_stamp_manual`, `/admin/redeem_stamp` | stamp card | เพิ่ม/แลกรางวัลลูกค้า |
| Queue | `/admin/queue/reorder`, `/admin/queue/estimate` | จัดลำดับงาน | ลากคิวและตั้งเวลาประเมิน |
| Calendar | `/admin/calendar/*` | วันทำงาน/capacity | ตั้งวันหยุด วันพิเศษ และกำลังผลิต |
| Yearly Analytics | `/admin/api/yearly/<year>` | สถิติรายปี | ใช้ chart ใน dashboard |
| LINE Config | `/admin/line_config` | ตั้งค่า LINE/PromptPay | ใช้ webhook URL และ QR |
| Todo | `/admin/todos/*` | checklist ทีมงาน | เพิ่ม, toggle, ลบ todo |
| Products | `/admin/products` | จัดการสินค้า catalog | เพิ่ม/แก้/ลบ/เปิดปิดสินค้า |
| Export Excel | `/admin/export_excel` | export order | ดาวน์โหลด `.xlsx` |
| Spec Sheet | `/admin/spec_sheet/<task_id>` | PDF spec 3D | ใช้แนบให้ช่างหรือ QC |
| Task Files | `/admin/task_files/<task_id>` | ดูไฟล์แนบ | รองรับทั้ง 3D files และ custom order reference files |

## Commerce Workflow

### Custom Order

1. ลูกค้าเข้า `/`
2. กรอกข้อมูลลูกค้า
3. เลือกประเภทงาน เช่น ออกแบบ, เลเซอร์, CNC, งานสั่งทำทั่วไป
4. ระบุความซับซ้อน, จำนวน, ขนาด, วัสดุ/สี, ผิวงาน, วิธีรับงาน
5. แนบไฟล์อ้างอิง
6. ระบบสร้าง task, ticket, draft quote และ `pricing_gaps`
7. Admin เปิด task แล้วกด Quote
8. ลูกค้า approve quote ใน customer dashboard
9. ลูกค้าชำระ deposit หรือยอดเต็ม
10. Admin ตรวจสลิป, เปลี่ยนสถานะ, ออก invoice, ส่งงาน

### 3D Order

1. ลูกค้าเข้า `/model`
2. แนบไฟล์ 3D และรูปอ้างอิง
3. เลือก material, color, quality, infill, quantity, dimensions, finish, support
4. ถ้าเป็น STL ระบบพยายามอ่าน volume
5. ระบบคำนวณ draft price จาก:
   - volume cm3
   - material density
   - material price per gram
   - infill
   - support waste
   - finish/support fee
   - machine hour
   - rush multiplier ตาม deadline
6. Admin ตรวจ `auto_pricing`, ปรับราคา, ส่ง quote
7. ลูกค้า approve และจ่าย deposit
8. ทีมงานผลิตตาม job sheet และ spec sheet

## Pricing Logic

### 3D Pricing

ฟังก์ชัน: `calculate_3d_price(specs, overrides=None)`

Input สำคัญ:

| Field | ความหมาย |
| --- | --- |
| `material` | PLA, ABS, PETG, TPU, Resin, Nylon, ASA, CF-PLA |
| `volume_cm3` | ปริมาตรจาก STL หรือ manual dimension |
| `size_x/y/z` | ใช้คำนวณ volume fallback |
| `infill` | 5 ถึง 100 |
| `quantity` | จำนวนชิ้น |
| `quality` | draft, standard, fine, ultra |
| `support` | none, auto, minimal, full |
| `finish` | as_printed, sanded, polished, painted |
| `deadline` | ใช้คิด rush multiplier |

Output สำคัญ:

| Field | ความหมาย |
| --- | --- |
| `amount` | ราคาสุทธิแนะนำ |
| `material_weight_g` | น้ำหนักวัสดุโดยประมาณ |
| `material_cost` | ต้นทุนวัสดุ |
| `machine_hours` | ชั่วโมงเครื่องโดยประมาณ |
| `machine_cost` | ค่าเครื่อง |
| `finish_support_fee` | ค่าเก็บผิวและ support |
| `confidence` | high, medium, low |
| `pricing_gaps` | ข้อมูลที่ยังขาดก่อน quote จริง |

### Custom Order Pricing

ฟังก์ชัน: `calculate_custom_order_price(specs, overrides=None)`

ใช้กับงาน non-3D เช่น design, laser, CNC, print, assembly, repair, custom

Input สำคัญ:

| Field | ความหมาย |
| --- | --- |
| `service_type` | ประเภทงาน |
| `complexity` | simple, standard, complex |
| `quantity` | จำนวน |
| `width_mm/height_mm/depth_mm` | ขนาด |
| `finish_level` | none, basic, premium |
| `deadline` | ใช้คิด rush |
| `reference_files` | ไฟล์อ้างอิง |

Output:

| Field | ความหมาย |
| --- | --- |
| `amount` | ราคาสุทธิแนะนำ |
| `labor_hours` | ชั่วโมงแรงงานโดยประมาณ |
| `service_rate` | rate ตั้งต้น |
| `area_cm2`, `volume_cm3` | ขนาดแปลงหน่วย |
| `confidence` | ความมั่นใจ |
| `pricing_gaps` | ช่องว่างข้อมูล |

## Status Flow

ลำดับสถานะหลัก:

```text
pending -> quoted -> approved -> inprogress -> printing -> postprocessing -> qc -> ready -> delivered -> completed
```

สถานะพิเศษ:

```text
cancelled
```

เมื่อ status เปลี่ยน ระบบจะ:

1. บันทึก timeline event
2. ส่ง email ถ้าตั้ง SMTP
3. ส่ง SMS ถ้าตั้ง Twilio
4. ถ้า completed จะเพิ่ม stamp ให้ลูกค้า

## Security Checklist

มีแล้ว:

- Admin/customer password hash ด้วย bcrypt ถ้ามี package, fallback เป็น Werkzeug secure hash
- Legacy plaintext/SHA password upgrade ตอน login
- CSRF token สำหรับ POST/PUT/PATCH/DELETE
- Rate limit `/login` 5 ครั้งต่อ 15 นาทีต่อ IP
- JSON file lock และ atomic replace
- Upload extension allowlist
- Admin routes มี `@admin_required`
- Backup/restore กัน path traversal เบื้องต้น

ต้องทำก่อน deploy public:

- ตั้ง `SECRET_KEY` ใหม่ ห้ามใช้ default
- เปิด HTTPS ผ่าน reverse proxy
- จำกัดขนาด upload ที่ web server หรือ Flask config
- ทำ daily offsite backup
- ย้ายไป SQLite/PostgreSQL เมื่อ concurrent order เยอะ
- แยก admin role ถ้ามีพนักงานหลายคน

## Debug Checklist

ใช้ก่อนเปิดร้านทุกครั้ง:

```powershell
python -m compileall project
python -m py_compile project\app.py project\queue_manager.py project\promptpay.py project\pdf_generator.py
python project\app.py
```

เปิดเช็ก:

- `/`
- `/model`
- `/tracking`
- `/customer/login`
- `/admin`
- `/catalog`
- `/cart`
- `/admin/products`
- `/admin/line_config`

ฟังก์ชันที่ต้องลอง manual:

1. ส่ง custom order พร้อมไฟล์อ้างอิง
2. ส่ง 3D order พร้อม STL
3. Admin ส่ง quote
4. Customer approve quote
5. Upload slip
6. Admin approve slip
7. เปลี่ยน status
8. ดาวน์โหลด invoice/order PDF/spec sheet
9. Backup ZIP
10. Restore ในเครื่อง test เท่านั้น

## Known Limits

- JSON datastore ใช้ง่ายและมี lock แล้ว แต่ยังไม่เหมาะกับ concurrent traffic สูงมาก
- SMS ใช้ Twilio config เป็นค่าเริ่มต้น ถ้าใช้ Thai SMS gateway ให้เพิ่ม adapter แยก
- STL volume จะอ่านได้เฉพาะไฟล์ที่ parser รองรับและ mesh ไม่เสีย
- Invoice PDF ตอนนี้ใช้ generator เดิมเป็น invoice summary ยังไม่ใช่รูปแบบใบกำกับภาษีเต็มตามกรมสรรพากร
- LINE webhook จะใช้งานได้เมื่อมี `line_handler.py` และตั้งค่า channel ถูกต้อง
