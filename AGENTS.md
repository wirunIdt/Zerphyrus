# Zerphyrus Agent Guide

เอกสารนี้มีไว้ให้ AI/coding agent อ่านก่อนแก้โปรเจกต์ Zerphyrus เพื่อรู้ว่าอะไรอยู่ตรงไหน ควรทำงานอย่างไร และต้องระวังอะไรเป็นพิเศษ

## ภาพรวมโปรเจกต์

Zerphyrus เป็นเว็บ Flask สำหรับรับออเดอร์งานลูกค้าและงาน 3D printing มีหน้า public สำหรับลูกค้า, dashboard สำหรับ admin, ระบบชำระเงิน PromptPay, อัปโหลดสลิป, queue งาน, ticket/check-in, catalog/cart, customer account, PDF และ export Excel

ไฟล์หลัก:

- `project/app.py` คือ Flask app หลัก รวม route ส่วนใหญ่ไว้ที่นี่
- `project/queue_manager.py` จัดคิวงาน ปฏิทินวันทำงาน และ analytics รายปี
- `project/promptpay.py` สร้าง PromptPay payload
- `project/pdf_generator.py` สร้าง order PDF และ 3D spec sheet ด้วย ReportLab
- `project/templates/` เก็บ Jinja templates ทั้ง public/admin/customer
- `project/uploads/` เก็บไฟล์ที่ user/admin upload เช่น QR, slips, product images, 3D models
- `*.json` ที่ root repo เป็น data store แบบไฟล์ เช่น `tasks.json`, `products.json`, `customers.json`

## วิธีรัน

ให้รันจาก root repo:

```powershell
cd C:\Jaochai\Zerphyrus\Zerphyrus
python -m pip install -r project\requirements.txt
python project\app.py
```

เปิดเว็บที่ `http://127.0.0.1:5000`

เหตุผลที่ควรรันจาก root: ไฟล์ JSON data store ใช้ path แบบ relative หลายจุด ถ้ารันจากโฟลเดอร์อื่นอาจสร้าง data file คนละชุดและทำให้ข้อมูลเหมือนหาย

## โครงสร้างข้อมูล JSON

- `tasks.json` รายการออเดอร์/งานหลัก
- `tickets.json` ticket code สำหรับติดตามงานและ check-in
- `slips.json` สลิปชำระเงินของแต่ละ task
- `products.json` สินค้าใน catalog
- `orders_cart.json` ออเดอร์จาก cart/session
- `customers.json` บัญชีลูกค้า
- `users.json` admin login ปัจจุบัน default คือ `admin/admin123`
- `stamps.json` ระบบสะสม stamp เดิม
- `queue.json` ลำดับคิวและ estimate
- `work_calendar.json` วันทำงาน capacity และวันหยุดพิเศษ
- `todos.json` todo ของ admin dashboard
- `sn_counter.json` running order number

ก่อนแก้ logic ที่เขียน JSON ให้ดู helper `_r`, `_w`, `read_*`, `write_*` ใน `project/app.py` และ `queue_manager.py` ก่อนเสมอ

## หน้าสำคัญ

Public/customer:

- `/` ฟอร์มสั่งงานทั่วไป ใช้ `order_form.html`
- `/model` และ `/model/submit` ฟอร์มสั่งงาน 3D ใช้ `model.html`
- `/tracking` ติดตามงาน
- `/payment/<task_id>` ชำระเงินและอัปโหลดสลิป
- `/catalog`, `/product/<pid>`, `/cart`, `/cart/checkout` ระบบสินค้าและตะกร้า
- `/customer/register`, `/customer/login`, `/customer/dashboard`, `/customer/profile`

Admin:

- `/login`, `/logout`
- `/admin` dashboard หลัก ใช้ `admin_dashboard.html`
- `/admin/line_config` ตั้งค่า LINE, PromptPay, QR
- `/admin/products` จัดการสินค้า
- `/admin/export_excel`
- `/admin/spec_sheet/<task_id>`
- `/admin/task_files/<task_id>`

## เรื่องที่ต้องระวัง

- อย่าย้าย data JSON โดยไม่ตั้งใจ เพราะ app ยังไม่ได้ใช้ database จริง
- อย่าแก้ path upload แบบ relative เพิ่ม ควรอิง path เดียวกับ `project/uploads`
- route หลายตัวคืน JSON เพื่อให้ JS ใน template ใช้ ถ้าเปลี่ยน response ต้องเช็ก frontend ด้วย
- ไฟล์ template มี Thai text จำนวนมาก ต้องเก็บ encoding เป็น UTF-8
- มีการแก้ `project/index.html` อยู่ก่อนแล้ว อย่าทับหรือ revert ถ้าไม่ได้เกี่ยวกับงาน
- อย่าลบไฟล์ใน `project/uploads/` เว้นแต่ผู้ใช้สั่งชัดเจน
- ถ้าเพิ่ม feature ใหญ่ ให้เพิ่ม data schema แบบ backward compatible เพราะ JSON เก่าอาจไม่มี field ใหม่

## Roadmap ที่ผู้ใช้ต้องการ

Priority สูง:

- แจ้งเตือน LINE/Email เมื่อ status เปลี่ยน
- คิดราคา 3D อัตโนมัติจาก volume, material rate, quantity, quality, infill, finish และ support

Priority กลาง:

- Upload progress สำหรับไฟล์ STL/3D ขนาดใหญ่
- Gallery ผลงานที่พิมพ์เสร็จ เพิ่ม trust ให้ลูกค้า
- Online quote: admin ส่งราคา ลูกค้ากด approve/reject ผ่านระบบ

Priority ต่ำ:

- 3D model preview ใน browser สำหรับ `.stl`
- PDF สองภาษา EN/TH toggle
- Loyalty Points แทน Stamp Cards

ข้อเสนอเพิ่มที่ควรพิจารณา:

- Audit log ของ task/status/payment เพื่อย้อนดูว่าใครทำอะไรเมื่อไหร่
- Backup/restore JSON data เป็น zip จากหน้า admin
- Role-based admin user เช่น owner/staff/viewer
- Search และ filter ขั้นสูงใน admin dashboard
- Payment status timeline ในหน้าลูกค้า
- Quote expiry date และ deposit/payment split
- Email template settings สำหรับแจ้งเตือนลูกค้า
- Basic test suite สำหรับ helper สำคัญ เช่น PromptPay, queue, pricing, JSON migration

## แนวทาง implement feature ใหม่

1. เริ่มจากอ่าน route และ template ที่เกี่ยวข้อง
2. เพิ่ม helper function ก่อนถ้า logic ถูกใช้หลาย route
3. เพิ่ม field ใหม่ใน JSON แบบ optional และใส่ default เวลาอ่าน
4. อัปเดต admin UI และ customer UI ให้สอดคล้องกัน
5. ทดสอบ flow ด้วย Flask dev server และอย่างน้อยเช็ก route ที่แตะ
6. ถ้าเป็น upload/payment/notification ให้ทดสอบกรณี fail ด้วย

## Suggested implementation order

1. Fix/verify QR upload and upload path behavior
2. Add 3D pricing config and quote draft model
3. Add online quote approve flow
4. Add notifications on status/quote/payment changes
5. Add upload progress for 3D files
6. Add gallery
7. Add STL preview
8. Add bilingual PDF
9. Migrate stamps to loyalty points

