# Zerphyrus Project Skill

Use this skill when working on the Zerphyrus Flask app in this repository.

## Goal

ช่วยแก้และต่อยอดระบบรับงาน/สั่งพิมพ์ 3D ของ Zerphyrus โดยรักษาข้อมูล JSON เดิม, path upload เดิม, และ flow ลูกค้า/admin ให้ใช้งานได้จริง

## Start Here

1. Read `AGENTS.md`
2. Inspect the relevant route in `project/app.py`
3. Inspect the matching template in `project/templates/`
4. Check JSON files at repo root before changing schema
5. Run from repo root with `python project\app.py`

## Important Paths

- App entry: `project/app.py`
- Templates: `project/templates/`
- Uploads: `project/uploads/`
- Requirements: `project/requirements.txt`
- Queue/calendar logic: `project/queue_manager.py`
- PDF logic: `project/pdf_generator.py`
- PromptPay logic: `project/promptpay.py`
- Data files: root `*.json`

## Feature Playbooks

### Status notification LINE/Email

- Trigger from `/admin/update_status`
- Compare old status vs new status before writing
- Add notification helper such as `notify_status_change(task, old_status, new_status)`
- LINE config currently lives around `/admin/line_config`
- Email needs SMTP config fields and must fail softly without blocking status update
- Store notification attempts in a future `notifications.json` or task `events`

### 3D auto pricing

- Source data is `task["specs_3d"]` from `/model/submit`
- Add config for material rates, quality multiplier, infill multiplier, support/finish fee, minimum charge
- Volume may come from manual dimensions first: `size_x * size_y * size_z`
- If true STL volume is needed later, use an STL parser library instead of hand parsing binary STL
- Save calculated quote on the task, not only in the rendered page

### Upload progress for STL

- Current form is in `project/templates/model.html`
- Use `XMLHttpRequest.upload.onprogress` or Fetch streams only if browser support is acceptable
- Backend route remains `/model/submit` unless splitting upload into a separate endpoint
- Show percent, filename, size, and fail state

### Gallery

- Add `gallery.json` or add `gallery_items` if a database migration happens later
- Store images under `project/uploads/gallery`
- Public page should be scan-friendly and show actual finished work
- Admin should be able to mark completed task photos as gallery items

### Online quote

- Add quote fields to task: `quote_status`, `quote_amount`, `quote_note`, `quote_sent_at`, `quote_approved_at`
- Admin action sends quote from dashboard
- Customer dashboard and ticket/payment page should show approve/reject buttons
- Approved quote can unlock payment link with amount prefilled

### STL preview

- Frontend can use Three.js with `STLLoader`
- Keep preview optional and lazy-loaded
- Do not block order submission if preview fails

### PDF EN/TH toggle

- PDF code is in `project/pdf_generator.py`
- Add `lang='th'|'en'` parameter instead of duplicating functions
- Keep Thai font handling intact

### Loyalty points migration

- Existing data is `stamps.json`
- Add compatibility so old stamps still display
- New model should support points balance, lifetime points, redemptions, reason, source task id

## Definition of Done

- Feature works from the intended user page
- Admin and customer views agree on the same data
- JSON writes are backward compatible
- Uploads land in `project/uploads`
- QR/payment/status flows are manually checked if touched
- No unrelated user changes are reverted

