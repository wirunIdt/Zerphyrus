"""
LINE Bot Handler - Manual implementation using requests
No line-bot-sdk required — just raw HTTP to LINE Messaging API.

Config (set as environment variables or in .env):
    LINE_CHANNEL_ACCESS_TOKEN  — Long-lived channel access token
    LINE_CHANNEL_SECRET        — Channel secret (for signature verification)
    ADMIN_LINE_USER_ID         — Admin's LINE user ID (to receive forwarded msgs)
"""

import hashlib
import hmac
import base64
import json
import os
import requests as req
from datetime import datetime

LINE_API = 'https://api.line.me/v2/bot'
CHANNEL_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET', '')
ADMIN_USER_ID = os.environ.get('ADMIN_LINE_USER_ID', '')

HEADERS = lambda: {
    'Authorization': f'Bearer {CHANNEL_TOKEN}',
    'Content-Type': 'application/json',
}


# ── Signature verification ─────────────────────────────────────────────────────

def verify_signature(body: bytes, x_line_signature: str) -> bool:
    if not CHANNEL_SECRET:
        return True  # Skip verification if not configured
    hash_ = hmac.new(
        CHANNEL_SECRET.encode('utf-8'), body, hashlib.sha256
    ).digest()
    return base64.b64encode(hash_).decode('utf-8') == x_line_signature


# ── Reply helpers ──────────────────────────────────────────────────────────────

def reply_text(reply_token: str, text: str):
    """Reply a single text message."""
    payload = {
        'replyToken': reply_token,
        'messages': [{'type': 'text', 'text': text}]
    }
    try:
        req.post(f'{LINE_API}/message/reply', headers=HEADERS(),
                 json=payload, timeout=5)
    except Exception:
        pass


def push_text(user_id: str, text: str):
    """Push a text message to a user."""
    payload = {
        'to': user_id,
        'messages': [{'type': 'text', 'text': text}]
    }
    try:
        req.post(f'{LINE_API}/message/push', headers=HEADERS(),
                 json=payload, timeout=5)
    except Exception:
        pass


def reply_flex(reply_token: str, alt_text: str, contents: dict):
    """Reply with a Flex Message."""
    payload = {
        'replyToken': reply_token,
        'messages': [{
            'type': 'flex',
            'altText': alt_text,
            'contents': contents
        }]
    }
    try:
        req.post(f'{LINE_API}/message/reply', headers=HEADERS(),
                 json=payload, timeout=5)
    except Exception:
        pass


# ── Order status card ──────────────────────────────────────────────────────────

STATUS_TH = {
    'pending': '⏳ รอดำเนินการ',
    'inprogress': '⚙️ กำลังดำเนินการ',
    'completed': '✅ เสร็จสิ้น',
    'cancelled': '❌ ยกเลิก',
}
STATUS_COLOR = {
    'pending': '#f59e0b',
    'inprogress': '#3b82f6',
    'completed': '#10b981',
    'cancelled': '#ef4444',
}
PRIORITY_TH = {'high': '🔴 เร่งด่วน', 'medium': '🟡 ปานกลาง', 'low': '🟢 ไม่เร่งด่วน'}


def build_order_card(task: dict, ticket_code: str = '') -> dict:
    """Build a LINE Flex Message bubble for an order."""
    status = task.get('status', 'pending')
    color = STATUS_COLOR.get(status, '#8b5cf6')
    return {
        'type': 'bubble',
        'header': {
            'type': 'box', 'layout': 'vertical',
            'backgroundColor': color,
            'contents': [{
                'type': 'text',
                'text': '🎟️ สถานะออเดอร์ของคุณ',
                'color': '#ffffff', 'weight': 'bold', 'size': 'lg'
            }]
        },
        'body': {
            'type': 'box', 'layout': 'vertical', 'spacing': 'sm',
            'contents': [
                {'type': 'text', 'text': task.get('title', '—'),
                 'weight': 'bold', 'size': 'xl', 'wrap': True},
                {'type': 'separator', 'margin': 'sm'},
                _row('👤 ลูกค้า', task['customer']['name']),
                _row('📋 สถานะ', STATUS_TH.get(status, status)),
                _row('⚡ ความเร่งด่วน', PRIORITY_TH.get(task.get('priority','medium'), '')),
                _row('📅 สร้างเมื่อ', task['createdAt'][:10]),
                *([ _row('🚚 กำหนดส่ง', task['deadline'])] if task.get('deadline') else []),
                *([ _row('🎟️ Ticket', ticket_code)] if ticket_code else []),
            ]
        },
        'footer': {
            'type': 'box', 'layout': 'vertical',
            'contents': [{
                'type': 'text', 'wrap': True, 'size': 'sm', 'color': '#888888',
                'text': 'ส่ง "คุยกับเจ้าของ" เพื่อติดต่อโดยตรง'
            }]
        }
    }


def _row(label: str, value: str) -> dict:
    return {
        'type': 'box', 'layout': 'horizontal', 'margin': 'sm',
        'contents': [
            {'type': 'text', 'text': label, 'size': 'sm',
             'color': '#555555', 'flex': 3},
            {'type': 'text', 'text': value, 'size': 'sm',
             'color': '#111111', 'flex': 5, 'wrap': True, 'weight': 'bold'},
        ]
    }


# ── Help message ───────────────────────────────────────────────────────────────

HELP_TEXT = (
    "สวัสดีครับ! ฉันช่วยอะไรได้บ้าง?\n\n"
    "🎟️ พิมพ์ รหัส Ticket (8 ตัว) → ดูสถานะออเดอร์\n"
    "🔍 พิมพ์ชื่อของคุณ → ค้นหาออเดอร์\n"
    "💬 พิมพ์ 'คุยกับเจ้าของ' → ส่งข้อความถึงเจ้าของโดยตรง\n"
    "❓ พิมพ์ 'ช่วยเหลือ' → ดูคำสั่งนี้"
)


# ── Main event handler ─────────────────────────────────────────────────────────

def handle_events(events: list, read_tasks, read_tickets):
    """Process all LINE webhook events."""
    for event in events:
        if event.get('type') != 'message':
            continue
        msg = event.get('message', {})
        if msg.get('type') != 'text':
            continue

        reply_token = event['replyToken']
        user_id = event['source'].get('userId', '')
        text = msg.get('text', '').strip()
        text_lower = text.lower()

        # ── Help ──────────────────────────────────────────────────
        if text_lower in ['ช่วยเหลือ', 'help', 'สวัสดี', 'hi', 'hello', 'เริ่ม']:
            reply_text(reply_token, HELP_TEXT)
            continue

        # ── Chat with owner ───────────────────────────────────────
        if 'คุยกับเจ้าของ' in text_lower or 'ติดต่อเจ้าของ' in text_lower:
            reply_text(reply_token,
                       "✅ ส่งข้อความถึงเจ้าของแล้ว!\n"
                       "เจ้าของจะตอบกลับผ่าน LINE นี้โดยตรงครับ\n\n"
                       "พิมพ์ข้อความที่ต้องการส่งได้เลย เจ้าของจะเห็นทุกข้อความ")
            if ADMIN_USER_ID:
                push_text(ADMIN_USER_ID,
                          f"💬 ลูกค้า (LINE: {user_id}) ต้องการคุยด้วย!\n"
                          f"ข้อความ: {text}\n\n"
                          f"กรุณาตอบกลับผ่าน LINE OA หรือโทรหาลูกค้าครับ")
            continue

        # ── Ticket lookup (8-char hex code) ──────────────────────
        if len(text) == 8 and text.upper().isalnum():
            tickets = read_tickets()
            code = text.upper()
            if code in tickets:
                ticket = tickets[code]
                tasks = read_tasks()
                task = next((t for t in tasks if t['id'] == ticket['task_id']), None)
                if task:
                    flex = build_order_card(task, code)
                    reply_flex(reply_token, f"ออเดอร์ {task['title']}", flex)
                    continue
                else:
                    reply_text(reply_token,
                               f"🎟️ Ticket {code}\n"
                               f"ลูกค้า: {ticket['customer_name']}\n"
                               f"งาน: {ticket['task_title']}\n"
                               f"สถานะ: {'✅ Check-in แล้ว' if ticket['status']=='checked_in' else '🟢 Active'}")
                    continue

        # ── Name search ───────────────────────────────────────────
        if len(text) >= 2:
            tasks = read_tasks()
            tickets = read_tickets()
            matches = [t for t in tasks
                       if text_lower in t['customer']['name'].lower()]
            if matches:
                task = matches[0]
                # Find ticket for this task
                code = next((c for c, tk in tickets.items()
                             if tk['task_id'] == task['id']), '')
                flex = build_order_card(task, code)
                alt = f"พบ {len(matches)} ออเดอร์ / แสดงล่าสุด: {task['title']}"
                reply_flex(reply_token, alt, flex)
                if ADMIN_USER_ID and user_id != ADMIN_USER_ID:
                    push_text(ADMIN_USER_ID,
                              f"🔔 ลูกค้าค้นหาออเดอร์: '{text}'\n"
                              f"พบ {len(matches)} ออเดอร์")
                continue

        # ── Forward unrecognised message to admin ─────────────────
        reply_text(reply_token,
                   "ขออภัยครับ ไม่พบข้อมูลที่ค้นหา\n\n" + HELP_TEXT)
        if ADMIN_USER_ID and user_id != ADMIN_USER_ID:
            push_text(ADMIN_USER_ID,
                      f"📩 ข้อความจากลูกค้า (LINE: {user_id}):\n'{text}'")
