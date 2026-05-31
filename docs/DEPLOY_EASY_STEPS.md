# Deploy Zerphyrus: Easy Step-by-Step

วิธีที่แนะนำ: Vercel + Supabase

เป้าหมาย:

- เว็บออนไลน์โดยไม่ต้องเปิด PC
- ข้อมูลอยู่ใน Supabase ดึงออกได้
- ไฟล์ upload อยู่ใน Supabase Storage
- Vercel ใช้รันเว็บ

## Step 0: สิ่งที่ต้องมี

- GitHub account
- Supabase account
- Vercel account
- โปรเจกต์ Zerphyrus นี้ push ขึ้น GitHub แล้ว

## Step 1: สร้าง Supabase Project

1. เข้า Supabase
2. กด New project
3. ตั้งชื่อ project เช่น `zerphyrus`
4. เลือก region ที่ใกล้ไทย เช่น Singapore ถ้ามี
5. ตั้ง database password แล้วเก็บไว้
6. รอ project สร้างเสร็จ

## Step 2: สร้างตารางและ Storage

1. ใน Supabase ไปที่ SQL Editor
2. เปิดไฟล์ `supabase/schema.sql` ในโปรเจกต์นี้
3. Copy SQL ทั้งหมด
4. วางใน SQL Editor
5. กด Run

หลังจบ step นี้ Supabase จะมี:

- table `zerphyrus_kv`
- storage bucket `zerphyrus-uploads`

## Step 3: เอาค่า API จาก Supabase

1. ไปที่ Project Settings
2. ไปที่ API
3. จดค่าเหล่านี้:
   - Project URL
   - anon public key
   - service_role key

ใช้ map เป็น env แบบนี้:

```text
SUPABASE_URL=Project URL
SUPABASE_ANON_KEY=anon public key
SUPABASE_SERVICE_ROLE_KEY=service_role key
```

สำคัญ: ห้ามเอา `SUPABASE_SERVICE_ROLE_KEY` ไปใส่ใน frontend JavaScript หรือเปิดเผยสาธารณะ

## Step 4: ตั้งค่า env ในเครื่องเพื่อ migrate

สร้างไฟล์ `.env` หรือ set environment variables ให้มีค่าประมาณนี้:

```text
DATA_BACKEND=supabase
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_KV_TABLE=zerphyrus_kv
SUPABASE_STORAGE_BUCKET=zerphyrus-uploads
SUPABASE_STORAGE_PUBLIC=0
SECRET_KEY=replace-with-long-random-secret
PREFERRED_SCHEME=https
FLASK_DEBUG=0
```

## Step 5: ทดสอบ migrate แบบไม่อัปโหลด

รันจาก root โปรเจกต์:

```powershell
python scripts\migrate_json_to_supabase.py --dry-run
```

ดูว่าไม่มี error และมีไฟล์ `migration_report.json`

## Step 6: migrate ข้อมูลจริงขึ้น Supabase

```powershell
python scripts\migrate_json_to_supabase.py
```

จากนั้นเปิด Supabase Table Editor แล้วดู table `zerphyrus_kv` ต้องมี row เช่น:

- `tasks.json`
- `users.json`
- `tickets.json`
- `customers.json`
- `queue.json`
- `work_calendar.json`

## Step 7: Push โปรเจกต์ขึ้น GitHub

```powershell
git add .
git commit -m "Prepare Zerphyrus for Vercel and Supabase"
git push
```

## Step 8: Deploy บน Vercel

1. เข้า Vercel
2. กด Add New Project
3. เลือก GitHub repo ของ Zerphyrus
4. Framework Preset เลือก Other
5. Build/Output ปล่อย default ได้
6. ตรวจว่ามีไฟล์:
   - `vercel.json`
   - `api/index.py`
   - `requirements.txt`
7. ไปที่ Environment Variables แล้วเพิ่ม:

```text
DATA_BACKEND=supabase
SUPABASE_URL=your-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_KV_TABLE=zerphyrus_kv
SUPABASE_STORAGE_BUCKET=zerphyrus-uploads
SUPABASE_STORAGE_PUBLIC=0
SECRET_KEY=replace-with-long-random-secret
PREFERRED_SCHEME=https
FLASK_DEBUG=0
COMPANY_NAME=Zerphyrus
PROMPTPAY_PHONE=0812345678
```

8. กด Deploy

## Step 9: ตรวจหลัง Deploy

หลัง Vercel deploy สำเร็จ ให้เปิด:

```text
https://your-vercel-domain.vercel.app/healthz
```

ต้องได้ประมาณนี้:

```json
{
  "status": "ok",
  "app": "zerphyrus"
}
```

จากนั้นทดสอบ:

1. เปิดหน้าแรก `/`
2. เปิด `/model`
3. Login admin ที่ `/login`
4. เปิด `/admin`
5. เปิด `/admin/export_data.json`
6. เปิด `/admin/export_data.zip`

## Step 10: วิธีดึงข้อมูลออก

วิธีง่ายสุด:

```text
/admin/export_data.zip
```

วิธีสำรอง:

- Supabase Table Editor > `zerphyrus_kv`
- Supabase Storage > bucket `zerphyrus-uploads`
- Supabase SQL Editor query ข้อมูลจาก `zerphyrus_kv`

## ถ้า Deploy Fail ให้เช็กตามนี้

- ตั้ง env ใน Vercel ครบไหม
- รัน `supabase/schema.sql` แล้วหรือยัง
- `SUPABASE_SERVICE_ROLE_KEY` ถูกไหม
- Vercel log มี error อะไร
- เปิด `/healthz` ได้ไหม
- `requirements.txt` อยู่ที่ root หรือไม่

## คำสั่ง verify ก่อน deploy

```powershell
python -m py_compile wsgi.py api\index.py project\app.py project\queue_manager.py project\data_store.py project\storage_backend.py project\promptpay.py project\pdf_generator.py tests\test_core.py scripts\migrate_json_to_supabase.py
python -m unittest discover -s tests -v
```

ผลล่าสุดในเครื่องนี้:

```text
Ran 21 tests
OK
```
