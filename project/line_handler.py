import base64
import hashlib
import hmac
import os

import requests


def verify_signature(body, signature):
    secret = os.environ.get("LINE_CHANNEL_SECRET", "")
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


def _reply(reply_token, text):
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token or not reply_token:
        return False
    resp = requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text[:4900]}]},
        timeout=5,
    )
    return resp.ok


def _status_text(value):
    labels = {
        "pending": "รอคิว",
        "inprogress": "กำลังดำเนินการ",
        "completed": "เสร็จแล้ว",
        "cancelled": "ยกเลิก",
    }
    return labels.get(value, value or "-")


def _find_task(tasks, query):
    q = (query or "").strip().lower()
    for task in tasks:
        candidates = [
            str(task.get("id", "")),
            str(task.get("sn", "")),
            str(task.get("title", "")),
        ]
        if any(q and q == item.lower() for item in candidates):
            return task
    return None


def order_status_message(query, read_tasks, read_tickets):
    raw = (query or "").strip()
    if not raw:
        return None
    tasks = read_tasks()
    tickets = read_tickets()
    code = raw.upper()
    task = None
    ticket = tickets.get(code)
    if ticket:
        task = _find_task(tasks, ticket.get("task_id", ""))
    if task is None:
        task = _find_task(tasks, raw)
    if task is None:
        return None
    title = task.get("title") or task.get("sn") or task.get("id")
    status = _status_text(task.get("status"))
    deadline = task.get("deadline") or "-"
    sn = task.get("sn") or task.get("id", "-")
    return f"สถานะงาน {sn}\n{title}\nสถานะ: {status}\nกำหนดส่ง: {deadline}"


def handle_events(events, read_tasks, read_tickets):
    for event in events:
        reply_token = event.get("replyToken")
        source = event.get("source") or {}
        user_id = source.get("userId", "")
        event_type = event.get("type")

        if event_type == "follow":
            if user_id:
                _reply(reply_token, f"เชื่อมต่อ LINE OA แล้ว\nLINE User ID:\n{user_id}")
            continue

        if event_type != "message":
            continue
        message = event.get("message") or {}
        if message.get("type") != "text":
            continue

        text = (message.get("text") or "").strip()
        if text.lower() in {"id", "line id", "user id", "userid"}:
            _reply(reply_token, f"LINE User ID:\n{user_id}\nนำค่านี้ไปใส่ช่อง LINE Admin User ID")
            continue

        status = order_status_message(text, read_tasks, read_tickets)
        if status:
            _reply(reply_token, status)
        else:
            _reply(reply_token, "ส่งรหัส Ticket หรือเลข SN เพื่อตรวจสอบสถานะงาน\nส่งคำว่า id เพื่อดู LINE User ID")
