# File Organization Notes

อัปเดตล่าสุด: 2026-06-02

## Standalone Pages

- `project/static_pages/studio_landing.html`
  - ที่มา: ย้ายมาจาก `C:\Jaochai\Zerphyrus\cpmpage.html`
  - หน้าที่: หน้า landing/marketing ของ Zerphyrus สำหรับโชว์บริการ, catalog mock, cart mock, order/payment/contact sections
  - การเชื่อมกับโปรเจคหลัก: เปิดผ่าน route `/studio` และเพิ่มลิงก์ใน sidebar ของ main app แล้ว
  - หมายเหตุ: ฟอร์มในหน้านี้เป็นหน้า showcase เดิม จึงเชื่อมปุ่มสำคัญให้พาไป flow จริงของ Flask เช่น `/`, `/tracking`, `/catalog`, `/contact`

- `project/static_pages/if_clause_learning.html`
  - ที่มา: ย้ายมาจาก `project/index.html`
  - หน้าที่: หน้าเรียนภาษาอังกฤษเรื่อง If Clause พร้อม quiz ในตัว
  - การเชื่อมกับโปรเจคหลัก: เปิดผ่าน route `/extras/if-clause` และเพิ่มลิงก์ใน sidebar แล้ว
  - หมายเหตุ: เป็น archive/extra page ไม่ใช่ flow หลักของ Zerphyrus

## Main App Folders

- `project/templates/`: Jinja templates สำหรับ Flask routes หลัก
- `project/static_pages/`: HTML standalone ที่ไม่ต้องผ่าน Jinja แต่ยังเปิดผ่าน Flask ได้
- `project/uploads/`: ไฟล์ upload/runtime data สำหรับ local development
- `project/backups/`: backup zip/runtime output สำหรับ local development
- `docs/`: คู่มือ deploy, production notes, project summary และบันทึกการจัดไฟล์

## Cleanup Notes

- ไม่ได้ลบ `uploads` หรือ `backups` ที่ถูก track อยู่เดิม เพราะอาจเป็น sample/runtime data ที่ผู้ใช้ยังต้องใช้
- ไฟล์ generated อย่าง `__pycache__` ไม่ควรเพิ่มใหม่เข้า commit รอบถัดไป
