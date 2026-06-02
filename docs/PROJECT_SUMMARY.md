# Zerphyrus Project Summary

อัปเดตล่าสุด: 2026-06-02

## ภาพรวม

Zerphyrus เป็นเว็บแอป Flask สำหรับจัดการงานสั่งทำ/งาน 3D print ตั้งแต่หน้าลูกค้าไปจนถึงหลังบ้านของแอดมิน จุดหลักของระบบคือรับคำสั่งทำงาน, คำนวณราคา, ติดตามสถานะ, รับหลักฐานชำระเงิน, จัดคิวงาน, ดู analytics, ส่งออกข้อมูล และ deploy ออนไลน์ด้วย Vercel + Supabase

## ส่วนสำคัญของระบบ

- `project/app.py` คือ Flask app หลัก รวม route หน้าเว็บ, admin, customer portal, payment, export และ health check
- `api/index.py` คือ entrypoint สำหรับ Vercel serverless
- `wsgi.py` คือ entrypoint สำหรับ host แบบ Python WSGI เช่น PaaS ที่ใช้ Gunicorn
- `project/data_store.py` คือ data layer ที่อ่าน/เขียนได้ทั้ง JSON local และ Supabase KV
- `project/storage_backend.py` คือ helper สำหรับ Supabase Storage
- `project/queue_manager.py` คือ logic คิวงาน, calendar และ yearly analytics
- `tests/test_core.py` คือชุด unit/smoke tests หลักของโปรเจค

## Deploy ปัจจุบัน

ทางที่ง่ายและฟรีสุดสำหรับโปรเจคนี้คือ Vercel + Supabase:

- Vercel ใช้รัน Flask ผ่าน serverless function
- Supabase ใช้เก็บข้อมูลแทนไฟล์ JSON บนเครื่อง
- Supabase Storage ใช้เก็บ uploads เช่น slips, QR, model files
- Environment variables ตั้งใน Vercel ไม่ต้องเขียนลง `.env` บน production

ไฟล์คู่มือ deploy หลักอยู่ที่ `docs/DEPLOY_EASY_STEPS.md`

## สถานะล่าสุด

- แก้ปัญหา Vercel read-only filesystem แล้ว โดยไม่ให้ production พยายามเขียน `.env`
- ปรับ data write ให้ fail-soft เมื่อ Supabase write ล้มเหลว เพื่อไม่ทำให้ทั้ง serverless function crash ทันที
- เพิ่ม health check ที่ `/healthz`
- เพิ่ม export data สำหรับดึงข้อมูลออกจากระบบ
- เพิ่ม request-level cache และ preload เพื่อลดการอ่านข้อมูลซ้ำในหน้า admin
- ลดการเขียน queue ซ้ำเมื่อลำดับงานไม่เปลี่ยน
- เพิ่มเอกสาร timeline และสรุปโปรเจค

## Refactor รอบนี้ทำอะไร

- ทำให้ `admin_context()` อ่านง่ายขึ้น แยกตัวแปรชัดเจนกว่าเดิม
- ลด repeated reads จาก `read_slips()` และข้อมูล admin อื่น ๆ
- เพิ่ม `preload_data()` ที่ data layer เพื่อรองรับ bulk read
- ทำให้ `sync_queue()` เขียนข้อมูลเฉพาะตอน queue เปลี่ยนจริง
- เพิ่ม test ยืนยันว่า cache และ queue optimization ทำงานตามที่ตั้งใจ

## การทดสอบ

คำสั่งตรวจสอบหลัก:

```powershell
python -m py_compile api\index.py wsgi.py project\app.py project\data_store.py project\queue_manager.py project\promptpay.py project\pdf_generator.py project\storage_backend.py tests\test_core.py
python -m unittest discover -s tests -v
```

ผลล่าสุด: unit tests ผ่านทั้งหมด

## งานที่แนะนำต่อ

- แยก `project/app.py` ออกเป็น blueprint ตามกลุ่ม route เช่น admin, customer, payment, catalog
- เพิ่ม test สำหรับ POST admin actions เช่น update status, quote, verify slip, product CRUD
- เพิ่ม browser smoke test สำหรับหน้า admin หลัง deploy
- ทำ migration uploads ไป Supabase Storage ให้ครบทุก flow
- เพิ่ม monitoring เบื้องต้นด้วย Vercel logs และ Supabase logs
