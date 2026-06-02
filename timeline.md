# Zerphyrus Timeline

## Current Status (Latest)

- วันที่อัปเดตล่าสุด: 2026-06-02
- สถานะล่าสุด: refactor รอบ performance/readability สำหรับหน้า admin, data store cache, queue sync และเอกสารสรุปโปรเจคเสร็จแล้ว
- คำสั่งตรวจสอบล่าสุด:
  - `python -m py_compile api\index.py wsgi.py project\app.py project\data_store.py project\queue_manager.py project\promptpay.py project\pdf_generator.py project\storage_backend.py tests\test_core.py`
  - `python -m unittest discover -s tests -v`
- ผลล่าสุด: `Ran 23 tests ... OK`

## 2026-06-02

### Status Update

- โปรเจค deploy flow หลักเป็น Vercel + Supabase
- หน้า health check ใช้ตรวจว่า backend ทำงานได้ที่ `/healthz`
- ข้อมูลหลักยังอยู่ใน JSON-compatible store ผ่าน `project/data_store.py` และสามารถใช้ Supabase table `zerphyrus_kv` ได้เมื่อกำหนด `DATA_BACKEND=supabase`
- ไฟล์ upload สามารถย้ายไป Supabase Storage ได้ผ่าน `project/storage_backend.py`

### Refactor / Performance

- เพิ่ม request-level cache ใน `project/data_store.py` เพื่อลดการอ่าน JSON/Supabase ซ้ำใน request เดียวกัน
- เพิ่ม `preload_data()` เพื่อให้หน้า admin โหลดข้อมูลหลายไฟล์ในรอบเดียวเมื่อ backend รองรับ
- ปรับ `admin_context()` ใน `project/app.py` ให้อ่านง่ายขึ้นและใช้ข้อมูล slips ที่โหลดไว้แล้ว แทนการเรียกซ้ำต่อ task
- ปิด auto backup อัตโนมัติบน Vercel/Supabase โดย default เพื่อลด overhead และเลี่ยงปัญหา filesystem แบบ read-only
- ปรับ `sync_queue()` ใน `project/queue_manager.py` ให้ไม่เขียน queue ซ้ำถ้าลำดับงานไม่เปลี่ยน
- เพิ่ม guard ให้ queue/calendar analytics ทนกับข้อมูลผิด shape มากขึ้น

### Documentation

- เพิ่ม `docs/PROJECT_SUMMARY.md` สำหรับสรุปภาพรวมโปรเจค, entrypoint, data backend, deploy, tests และงานที่แนะนำต่อ

### Tests

- เพิ่ม test สำหรับ data request cache
- เพิ่ม test สำหรับ queue sync ที่ต้องไม่เขียนข้อมูลซ้ำเมื่อ order ไม่เปลี่ยน
- รัน syntax check และ unit tests ผ่านทั้งหมด

บันทึกนี้ใช้ติดตามว่าแต่ละวันทำอะไรไปถึงไหนแล้วในโปรเจกต์ Zerphyrus

## Current Status

- วันที่อัปเดตล่าสุด: 2026-05-31
- สถานะล่าสุด: เตรียม Vercel + Supabase migration package พร้อม data/storage backend, export, และ migration dry-run แล้ว
- คำสั่งตรวจสอบล่าสุด:
  - `python -m py_compile wsgi.py project\app.py project\queue_manager.py project\promptpay.py project\pdf_generator.py tests\test_core.py`
  - `python -m unittest discover -s tests -v`
- ผลล่าสุด: `Ran 21 tests ... OK`

## 2026-05-31

### Easy Deploy Guide

- เพิ่มคู่มือ deploy แบบทำตามทีละ step ที่ `docs/DEPLOY_EASY_STEPS.md`
- คู่มือนี้สรุปทางที่ง่ายสุดสำหรับ Vercel + Supabase:
  - สร้าง Supabase project
  - รัน `supabase/schema.sql`
  - ตั้ง env
  - dry-run migration
  - migrate ข้อมูลจริง
  - deploy ผ่าน Vercel
  - ตรวจ `/healthz`
  - ดึงข้อมูลผ่าน `/admin/export_data.zip`

### Deployment Prep

- เพิ่ม production WSGI entrypoint ที่ `wsgi.py`
- เพิ่ม Vercel serverless entrypoint ที่ `api/index.py`
- เพิ่ม `vercel.json`
- เพิ่ม root `requirements.txt` สำหรับ Vercel build
- เพิ่ม `Procfile` สำหรับ host แบบ PaaS ที่ใช้ start command `gunicorn wsgi:app`
- เพิ่ม `.env.example` สำหรับ environment variables ที่ต้องตั้งก่อน deploy
- เพิ่ม `docs/DEPLOY_FREE.md` เป็น checklist สำหรับเอา Zerphyrus ขึ้นออนไลน์แบบฟรี
- อัปเดต `docs/DEPLOY_FREE.md` ให้เน้นตัวเลือกที่ดึงข้อมูลออกได้ โดยแนะนำ PythonAnywhere Free เป็นทางเริ่มต้น
- เพิ่ม health check route:
  - `/healthz`
  - `/health`
- เพิ่ม admin data export route:
  - `/admin/export_data.json`
  - `/admin/export_data.zip`
- เพิ่ม Supabase KV data layer:
  - `project/data_store.py`
  - รองรับ `DATA_BACKEND=json`
  - รองรับ `DATA_BACKEND=supabase`
- เพิ่ม Supabase Storage helper:
  - `project/storage_backend.py`
  - route `/uploads/...` อ่านจาก local ก่อน แล้ว fallback ไป Supabase Storage
- เพิ่ม Supabase schema:
  - `supabase/schema.sql`
- เพิ่ม migration script:
  - `scripts/migrate_json_to_supabase.py`
- ปรับ local startup ให้ใช้ `FLASK_DEBUG` และ `PORT` จาก environment variable แทนการเปิด debug ตลอดเวลา
- เพิ่ม `gunicorn` ใน `project/requirements.txt` สำหรับ production hosting
- เพิ่ม `.gitignore` สำหรับ `migration_report.json`

### Tests

- เพิ่ม test สำหรับ health check response
- เพิ่ม `/healthz` และ `/health` เข้า route smoke test
- เพิ่ม test สำหรับ export data แบบ JSON และ ZIP
- เพิ่ม `/admin/export_data.json` และ `/admin/export_data.zip` เข้า route smoke test
- เพิ่ม test สำหรับ JSON data store และ storage helper

### Debug / Verification

- รัน `py_compile` ผ่าน
- รัน test ทั้งหมดผ่าน:

```text
Ran 21 tests in 2.037s
OK
```

- รัน migration dry-run ผ่าน:

```text
python scripts\migrate_json_to_supabase.py --dry-run
```

## 2026-05-30

### Refactor

- ปรับ `project/app.py` ให้ส่วนคำนวณราคางาน 3D และ custom order อ่านง่ายขึ้น
- แยกค่าคงที่ด้าน pricing ออกมาเป็นกลุ่มชัดเจน เช่น material, quality, finish, support, service rate
- เพิ่ม helper ย่อย:
  - `_positive_quantity`
  - `_rush_multiplier`
  - `_split_amount`
  - `payment_amount_for_task`
  - `uploaded_task_files`
- ปรับ route `/payment/<task_id>` ให้เรียก helper สำหรับเลือกยอดชำระ แทนการฝัง logic ใน route โดยตรง
- ปรับ route `/admin/task_files/<task_id>` ให้เรียก helper สำหรับสร้างรายการไฟล์แนบ
- ล้างโค้ดรกใน `project/pdf_generator.py` ที่ฟังก์ชัน `_thin()`

### Tests

- เพิ่มไฟล์ `tests/test_core.py`
- ใช้ `unittest` เพื่อไม่ต้องติดตั้ง dependency เพิ่ม
- test ใช้ temp directory สำหรับ JSON data store จึงไม่แตะข้อมูลจริงของร้าน
- ครอบคลุมส่วนหลัก:
  - PromptPay payload และ CRC
  - queue/calendar logic
  - pricing helpers
  - password helpers
  - JSON-backed helpers เช่น events, notifications, stamps, tickets
  - revenue, CRM, invoice, analytics helpers
  - PDF smoke test
  - public/customer/admin route smoke test

### Debug / Verification

- รัน `py_compile` ผ่าน
- รัน test ทั้งหมดผ่าน:

```text
Ran 17 tests in 1.358s
OK
```

## Next Suggested Work

- ขยาย test สำหรับ POST admin actions เช่น update status, quote, slip verification, product CRUD
- เพิ่ม test สำหรับ upload flow ด้วยไฟล์จำลอง
- แยก logic จาก route ใหญ่ใน `project/app.py` เพิ่มทีละส่วน โดยเน้นจุดที่มี business logic ซ้ำ
- ตรวจ template route ด้วย browser smoke test ถ้าจะปรับ UI ต่อ
