# Deploy Zerphyrus for Free

เอกสารนี้คือ checklist สำหรับเอา Zerphyrus ขึ้นออนไลน์โดยไม่ใช้ PC เป็น host

## สถานะปัจจุบันของโปรเจกต์

- Flask app entrypoint: `project/app.py`
- WSGI entrypoint สำหรับ production: `wsgi.py`
- Vercel entrypoint: `api/index.py`
- Vercel config: `vercel.json`
- Root requirements: `requirements.txt`
- Supabase schema: `supabase/schema.sql`
- JSON to Supabase migration: `scripts/migrate_json_to_supabase.py`
- Health check URL: `/healthz`
- Start command สำหรับ PaaS: `gunicorn wsgi:app`
- Data backend รองรับ 2 โหมด:
  - `DATA_BACKEND=json` สำหรับ local/dev
  - `DATA_BACKEND=supabase` สำหรับ Vercel production
- Uploads รองรับ Supabase Storage เมื่อกำหนด `SUPABASE_STORAGE_BUCKET`
- Admin data export:
  - `/admin/export_data.json` โหลดข้อมูล JSON รวมทุกชุด
  - `/admin/export_data.zip` โหลด JSON รวม + ไฟล์ JSON แยก + uploads
  - `/admin/backup` โหลด backup zip แบบเดิม

## ตัวเลือกที่แนะนำ

### ทางที่ดีที่สุดระยะยาว: Vercel + Supabase

เหมาะที่สุดถ้าต้องการเว็บออนไลน์ฟรี/ต้นทุนต่ำและดึงข้อมูลออกมาได้ชัดเจน เพราะ app อยู่บน Vercel ส่วนข้อมูลอยู่ใน Supabase Postgres/Storage

ขั้นตอน:

1. สร้าง Supabase project
2. เปิด Supabase SQL Editor แล้วรันไฟล์ `supabase/schema.sql`
3. ไปที่ Project Settings > API แล้วเตรียมค่า:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. ตั้ง environment variables ในเครื่องหรือบน Vercel:

```text
DATA_BACKEND=supabase
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_KV_TABLE=zerphyrus_kv
SUPABASE_STORAGE_BUCKET=zerphyrus-uploads
SUPABASE_STORAGE_PUBLIC=0
SECRET_KEY=...
PREFERRED_SCHEME=https
FLASK_DEBUG=0
```

5. migrate JSON เดิมเข้า Supabase:

```bash
python scripts/migrate_json_to_supabase.py --dry-run
python scripts/migrate_json_to_supabase.py
```

6. ตรวจ `migration_report.json`
7. Deploy ไป Vercel:

```bash
vercel
vercel --prod
```

8. ทดสอบ:
   - `/healthz`
   - `/`
   - `/admin`
   - `/admin/export_data.json`
   - `/admin/export_data.zip`

วิธีดึงข้อมูลออก:

- Supabase Table Editor: ดู row ใน `zerphyrus_kv`
- Supabase SQL Editor: query/export ค่า `data`
- หน้า admin: `/admin/export_data.json`
- หน้า admin: `/admin/export_data.zip`
- Supabase Storage: ดาวน์โหลดไฟล์ใน bucket `zerphyrus-uploads`

ข้อควรระวัง:

- ห้ามใส่ `SUPABASE_SERVICE_ROLE_KEY` ใน frontend JavaScript
- ใช้ service role เฉพาะ backend/serverless function เท่านั้น
- ถ้า bucket ไม่ public, `/uploads/...` จะ stream ผ่าน backend
- งานประมวลผลหนักมาก เช่น PDF/STL ใหญ่ อาจชน timeout ของ serverless ได้

### ทางง่ายสุด: PythonAnywhere Free

เหมาะกับ Flask + JSON data store ขนาดเล็ก และไม่ต้องเปิด PC เอง

เหมาะที่สุดถ้าต้องการ "ดึงข้อมูลออกมาได้" แบบฟรี เพราะข้อมูลอยู่เป็นไฟล์ใน account ของเรา และยังโหลดออกจากหน้า admin ได้ผ่าน `/admin/export_data.json` หรือ `/admin/export_data.zip`

ขั้นตอน:

1. สมัคร PythonAnywhere
2. อัปโหลด/clone โปรเจกต์นี้ไปที่ PythonAnywhere
3. เปิด Bash console แล้วเข้าโฟลเดอร์ repo
4. สร้าง virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r project/requirements.txt
```

5. ไปที่หน้า Web > Add a new web app > Manual configuration > Python 3.x
6. ตั้งค่า Source code เป็นโฟลเดอร์ repo เช่น `/home/<username>/Zerphyrus`
7. ตั้งค่า Working directory เป็นโฟลเดอร์ repo เดียวกัน
8. แก้ WSGI config ให้ import จาก `wsgi.py`:

```python
import sys
path = '/home/<username>/Zerphyrus'
if path not in sys.path:
    sys.path.insert(0, path)

from wsgi import application
```

9. ตั้งค่า virtualenv เป็น `/home/<username>/Zerphyrus/.venv`
10. ตั้ง environment variables จาก `.env.example` โดยเฉพาะ `SECRET_KEY`
11. กด Reload
12. เปิด `https://<username>.pythonanywhere.com/healthz` ต้องเห็น `{"status":"ok"}`
13. Login admin แล้วทดสอบโหลดข้อมูล:
    - `https://<username>.pythonanywhere.com/admin/export_data.json`
    - `https://<username>.pythonanywhere.com/admin/export_data.zip`

ข้อควรระวัง:

- Free plan เหมาะกับงานเล็กและ traffic ไม่สูง
- Outbound API บางอย่างอาจถูกจำกัด จึงต้องทดสอบ LINE/Email/SMS หลัง deploy
- ควรกด backup data เป็นระยะ

วิธีดึงข้อมูลออก:

- ทางหน้าเว็บ: Login admin แล้วเปิด `/admin/export_data.zip`
- ทาง console: ดาวน์โหลดไฟล์ `*.json` และ `project/uploads/` จาก Files tab ของ PythonAnywhere
- ทาง backup: เปิด `/admin/backup` เพื่อโหลด zip backup

### ทาง PaaS: Render หรือ Railway

ใช้ได้ง่ายกว่า VPS แต่ต้องระวังเรื่อง free tier และ disk

ตั้งค่าหลัก:

- Build command: `pip install -r project/requirements.txt`
- Start command: `gunicorn wsgi:app`
- Health check path: `/healthz`
- Environment variables: ตั้งตาม `.env.example`

ข้อควรระวัง:

- ถ้า host มี ephemeral filesystem ข้อมูล JSON/upload ที่เขียนหลัง deploy อาจหายตอน redeploy/restart
- ควรย้าย data ไป SQLite/Postgres และ upload ไป storage แยกก่อนใช้งานจริง

ถ้าจะใช้ Render/Railway และยังอยากดึงข้อมูลออกได้จริง แนะนำให้เลือก plan/setting ที่มี persistent volume หรือย้าย data ไปบริการ database เช่น Supabase Postgres ก่อน

### ทางเปิดตลอดกว่า: Oracle Cloud Always Free

เหมาะถ้าต้องการ server เปิดตลอดกว่า free PaaS แต่ต้องดูแล Linux เอง

ขั้นตอนภาพรวม:

1. สร้าง VM Ubuntu Always Free
2. ติดตั้ง Python, nginx, certbot
3. Clone repo
4. ติดตั้ง dependencies
5. รันด้วย gunicorn service
6. reverse proxy ด้วย nginx
7. เปิด HTTPS ด้วย certbot
8. ตั้ง backup cron

## Checklist ก่อนใช้งานจริง

- เปลี่ยน `SECRET_KEY`
- เปลี่ยนรหัส admin เริ่มต้น
- ทดสอบ `/healthz`
- ทดสอบ `/admin/export_data.json`
- ทดสอบ `/admin/export_data.zip`
- ทดสอบสร้าง order
- ทดสอบ tracking/ticket
- ทดสอบ upload slip
- ทดสอบ admin dashboard
- ทดสอบ backup download
- ตั้งเวลาสำรองข้อมูล

## งานที่ควรทำต่อ

- ย้าย JSON data ไป database
- ย้าย uploads ไป storage แยก
- เพิ่ม test สำหรับ POST admin actions
- เพิ่ม deploy script หรือ GitHub Actions หลังเลือก host แน่นอน
