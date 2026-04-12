# ระบบจัดการงานลูกค้า v2

## ติดตั้งและรัน

```bash
# 1. ติดตั้ง system dependency
sudo apt install wkhtmltopdf     # Ubuntu/Debian
# brew install wkhtmltopdf       # Mac

# 2. ติดตั้ง Python packages
pip install -r requirements.txt

# 3. รัน
python app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:5000`

---

## หน้าต่างๆ

| URL | คำอธิบาย |
|-----|-----------|
| `/` | ฟอร์มสั่งงาน (+ ปุ่มชำระเงิน/PDF หลังสั่ง) |
| `/tracking` | ตรวจสอบสถานะออเดอร์ |
| `/payment/<task_id>` | หน้าชำระเงิน PromptPay QR |
| `/order_pdf/<task_id>` | ดาวน์โหลด PDF ใบสั่งงาน |
| `/ticket/<code>` | ดู Ticket |
| `/checkin` | Self Check-in |
| `/webhook` | LINE Bot Webhook endpoint |
| `/login` | Admin Login |
| `/admin` | Admin Dashboard |
| `/admin/line_config` | ตั้งค่า LINE Bot & PromptPay |

---

## ฟีเจอร์ทั้งหมด

### 📋 Order Management
- ลูกค้ากรอกฟอร์มสั่งงาน → ได้รหัส Ticket + ลิ้งค์ชำระเงิน + PDF

### 📊 Dashboard & Analytics
- กราฟ 14 วัน, Pie สถานะ, Bar ความเร่งด่วน, KPI cards

### 🏅 Stamp Card  
- แสตมป์เพิ่มอัตโนมัติเมื่องานเสร็จ, ครบ 10 แลกรางวัล

### 🎟️ Ticket & Check-in
- QR Ticket ทุกออเดอร์, Self check-in, Admin check-in

### 💳 PromptPay QR Payment (ใหม่!)
- สร้าง QR PromptPay มาตรฐาน EMVCo โดยอัตโนมัติ
- ระบุจำนวนเงินหรือปล่อยว่างก็ได้
- แสดงในหน้าเว็บและ PDF

### 📄 PDF Export (ใหม่!)
- ใบคำสั่งงานสวยงาม พร้อมข้อมูลครบ
- รองรับภาษาไทย
- มี Ticket code และ PromptPay payload
- ดาวน์โหลดได้ทั้งลูกค้าและ Admin

### 🤖 LINE Bot (ใหม่!)
- Webhook รับข้อความจาก LINE OA
- ลูกค้าส่งรหัส Ticket → ได้สถานะออเดอร์เป็น Flex Card
- ลูกค้าส่งชื่อ → ค้นหาออเดอร์
- ลูกค้าพิมพ์ "คุยกับเจ้าของ" → ส่งข้อความถึง Admin โดยตรง

---

## ตั้งค่า LINE Bot

1. ไปที่ `/admin/line_config`
2. กรอก Channel Access Token, Channel Secret จาก LINE Developers Console
3. กรอก Admin LINE User ID
4. ตั้ง Webhook URL ใน LINE Console: `https://yourdomain.com/webhook`
5. บันทึก แล้วรีสตาร์ทเซิร์ฟเวอร์

---

## โครงสร้างไฟล์

```
project_v2/
├── app.py              ← Flask main app
├── promptpay.py        ← PromptPay QR generator (EMVCo)
├── pdf_generator.py    ← PDF export (pdfkit/wkhtmltopdf)
├── line_handler.py     ← LINE Bot webhook handler
├── requirements.txt
├── .env                ← สร้างอัตโนมัติจาก LINE config page
├── tasks.json
├── users.json          ← admin / admin123
├── stamps.json
├── tickets.json
└── templates/
    ├── order_form.html
    ├── tracking.html
    ├── login.html
    ├── admin_dashboard.html
    ├── ticket.html
    ├── checkin.html
    ├── payment.html     ← ใหม่
    └── line_config.html ← ใหม่
```

> **Default login:** admin / admin123
