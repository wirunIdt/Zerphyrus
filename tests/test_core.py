import importlib
import base64
import hashlib
import hmac
import os
import sys
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
TMP = tempfile.TemporaryDirectory()
OLD_CWD = os.getcwd()

os.chdir(TMP.name)
os.environ.setdefault("DATA_DIR", TMP.name)
sys.path.insert(0, str(PROJECT))

promptpay = importlib.import_module("promptpay")
queue_manager = importlib.import_module("queue_manager")
data_store = importlib.import_module("data_store")
storage_backend = importlib.import_module("storage_backend")
app_module = importlib.import_module("app")
line_handler = importlib.import_module("line_handler")
pdf_generator = importlib.import_module("pdf_generator")

flask_app = app_module.app
flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
app_module.maybe_auto_backup = lambda: None


def tearDownModule():
    os.chdir(OLD_CWD)
    TMP.cleanup()


def reset_json():
    data_store.reset_store_for_tests()
    for key in [
        "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET", "ADMIN_LINE_USER_ID",
        "PROMPTPAY_PHONE", "COMPANY_NAME", "PREFERRED_SCHEME", "EXTERNAL_URL",
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_TLS",
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM",
    ]:
        os.environ.pop(key, None)
    app_module.PROMPTPAY_PHONE = "0812345678"
    app_module.COMPANY_NAME = "ระบบจัดการงานลูกค้า"
    app_module.PREFERRED_SCHEME = ""
    env_path = Path(".env")
    if env_path.exists():
        env_path.unlink()
    app_module._w("tasks.json", [])
    app_module._w("users.json", {"admin": "admin123"})
    app_module._w("stamps.json", {})
    app_module._w("tickets.json", {})
    app_module._w("slips.json", {})
    app_module._w("products.json", [])
    app_module._w("orders_cart.json", {})
    app_module._w("sn_counter.json", {"last_sn": 0})
    app_module._w("todos.json", [])
    app_module._w("events.json", [])
    app_module._w("notifications.json", [])
    app_module._w("gallery.json", [])
    app_module._w("reviews.json", [])
    app_module._w("coupons.json", [])
    app_module._w("invoices.json", {"last_no": 0, "items": {}})
    app_module._w("customers.json", {})
    app_module._w("settings.json", {})
    queue_manager.write_queue({"order": [], "estimates": {}})
    queue_manager.write_calendar({
        "work_days_of_week": [0, 1, 2, 3, 4],
        "capacity_per_day": 2,
        "custom_dates": {},
    })


def csrf_client():
    client = flask_app.test_client()
    with client.session_transaction() as sess:
        sess["_csrf_token"] = "test-token"
    return client


class PromptPayTests(unittest.TestCase):
    def test_normalizes_thai_phone_numbers(self):
        self.assertEqual(promptpay._normalize_phone("081-234-5678"), "0066812345678")
        self.assertEqual(promptpay._normalize_phone("+66 81 234 5678"), "0066812345678")

    def test_payload_includes_amount_and_valid_crc(self):
        payload = promptpay.generate_promptpay_payload("0812345678", 123.45)
        self.assertIn("5406123.45", payload)
        self.assertEqual(payload[-4:], promptpay._crc16(payload[:-4]))


class QueueManagerTests(unittest.TestCase):
    def setUp(self):
        reset_json()

    def test_calendar_custom_dates_override_weekdays(self):
        cal = queue_manager.read_calendar()
        saturday = date(2026, 5, 30)
        monday = date(2026, 6, 1)
        self.assertFalse(queue_manager.is_working_day(saturday, cal))
        self.assertTrue(queue_manager.is_working_day(monday, cal))
        queue_manager.add_custom_date(saturday.isoformat(), "extra", "rush day")
        queue_manager.add_custom_date(monday.isoformat(), "holiday", "closed")
        cal = queue_manager.read_calendar()
        self.assertTrue(queue_manager.is_working_day(saturday, cal))
        self.assertFalse(queue_manager.is_working_day(monday, cal))
        queue_manager.remove_custom_date(monday.isoformat())
        self.assertNotIn(monday.isoformat(), queue_manager.read_calendar()["custom_dates"])

    def test_sync_reorder_estimate_and_queue_projection(self):
        tasks = [
            {"id": "a", "status": "pending", "priority": "low", "createdAt": "2026-01-02"},
            {"id": "b", "status": "pending", "priority": "high", "createdAt": "2026-01-01"},
            {"id": "c", "status": "completed", "priority": "high", "createdAt": "2026-01-01"},
        ]
        q = queue_manager.sync_queue(tasks)
        self.assertEqual(q["order"], ["b", "a"])
        queue_manager.reorder_queue(["a", "b"])
        queue_manager.set_task_estimate("a", 3.5, "long print")
        projected = queue_manager.get_queue_with_tasks(tasks)
        self.assertEqual([row["id"] for row in projected], ["a", "b"])
        self.assertEqual(projected[0]["estimated_hours"], 3.5)
        self.assertEqual(projected[0]["queue_note"], "long print")

    def test_sync_queue_skips_write_when_order_is_unchanged(self):
        queue_manager.write_queue({"order": ["a"], "estimates": {}})
        tasks = [{"id": "a", "status": "pending", "priority": "medium", "createdAt": "2026-01-01"}]
        writes = []
        original_write_queue = queue_manager.write_queue

        def spy_write_queue(data):
            writes.append(data.copy())
            original_write_queue(data)

        queue_manager.write_queue = spy_write_queue
        try:
            self.assertEqual(queue_manager.sync_queue(tasks)["order"], ["a"])
            self.assertEqual(writes, [])

            tasks.append({"id": "b", "status": "pending", "priority": "low", "createdAt": "2026-01-02"})
            self.assertEqual(queue_manager.sync_queue(tasks)["order"], ["a", "b"])
            self.assertEqual(len(writes), 1)
        finally:
            queue_manager.write_queue = original_write_queue

    def test_working_days_and_yearly_analytics(self):
        cal = queue_manager.read_calendar()
        self.assertGreater(queue_manager.working_days_count(2026, cal), 200)
        tasks = [
            {"id": "a", "status": "completed", "priority": "high", "createdAt": "2026-01-01T00:00", "updatedAt": "2026-01-03T00:00"},
            {"id": "b", "status": "cancelled", "priority": "low", "createdAt": "2026-02-01T00:00", "updatedAt": "2026-02-02T00:00"},
        ]
        data = queue_manager.yearly_analytics(tasks, 2026, cal)
        self.assertEqual(data["total_created"], 2)
        self.assertEqual(data["total_completed"], 1)
        self.assertEqual(data["avg_lead_days"], 2)
        self.assertIsNone(queue_manager._parse_date(""))


class AppHelperTests(unittest.TestCase):
    def setUp(self):
        reset_json()

    def sample_task(self):
        return {
            "id": "task-1",
            "sn": "ORD-1",
            "customer": {"name": "Ada", "phone": "0812345678", "email": "ada@example.com"},
            "title": "Widget",
            "description": "Make one widget",
            "priority": "medium",
            "deadline": "",
            "status": "pending",
            "createdAt": "2026-01-01T10:00:00",
            "updatedAt": "2026-01-02T10:00:00",
        }

    def test_password_helpers_support_modern_and_legacy_hashes(self):
        hashed = app_module.hash_password("secret123")
        self.assertTrue(app_module.verify_password(hashed, "secret123"))
        self.assertFalse(app_module.verify_password(hashed, "wrong"))
        self.assertTrue(app_module.verify_password("legacy", "legacy"))
        self.assertTrue(app_module.password_needs_upgrade("legacy"))

    def test_numeric_price_helpers(self):
        self.assertEqual(app_module._num("bad", 7.5), 7.5)
        self.assertEqual(app_module._int("4.9"), 4)
        self.assertEqual(app_module._positive_quantity("-2"), 1)
        self.assertEqual(app_module._split_amount(1000, 30), (300, 700))
        soon = (date.today() + timedelta(days=2)).isoformat()
        later = (date.today() + timedelta(days=20)).isoformat()
        self.assertEqual(app_module._rush_multiplier(soon), 1.35)
        self.assertEqual(app_module._rush_multiplier(later), 1.0)

    def test_3d_and_custom_pricing_are_consistent(self):
        price = app_module.calculate_3d_price({
            "material": "PLA", "quantity": "2", "size_x": "100", "size_y": "20",
            "size_z": "10", "infill": "20", "quality": "standard",
            "finish": "as_printed", "support": "none",
        })
        self.assertEqual(price["confidence"], "high")
        self.assertAlmostEqual(price["amount"], price["deposit_amount"] + price["balance_amount"], places=2)

        custom = app_module.calculate_custom_order_price({
            "service_type": "design", "quantity": "1", "width_mm": "100",
            "height_mm": "50", "depth_mm": "10", "finish_level": "basic",
            "reference_files": [{"filename": "brief.pdf"}],
        })
        self.assertEqual(custom["confidence"], "medium")
        self.assertGreaterEqual(custom["amount"], 250)

    def test_json_backed_helpers(self):
        task = self.sample_task()
        app_module.write_tasks([task])
        self.assertEqual(app_module.find_task(app_module.read_tasks(), "task-1")["title"], "Widget")
        with flask_app.test_request_context("/"):
            event = app_module.add_event("task-1", "created", "ok")
        self.assertEqual(event["actor"], "system")
        self.assertEqual(len(app_module.events_for_task("task-1")), 1)

        app_module.log_notification("task-1", "email", "a@example.com", "sent", "Hi")
        self.assertEqual(app_module.read_notifications()[0]["status"], "sent")
        app_module.add_stamp("0812345678", "Ada")
        self.assertEqual(app_module.read_stamps()["0812345678"]["stamps"], 1)
        ticket = app_module.create_ticket(task)
        self.assertIn(ticket, app_module.read_tickets())
        self.assertTrue(app_module.allowed_file("proof.PNG"))
        self.assertFalse(app_module.allowed_file("model.stl"))

    def test_reporting_helpers(self):
        task = self.sample_task()
        task["quote"] = {"amount": 1070, "status": "approved", "deposit_amount": 535, "balance_amount": 535}
        app_module.write_tasks([task])
        app_module.write_customers({"0812345678": {"name": "Ada", "email": "ada@example.com"}})
        slips = {"task-1": [{"status": "approved", "amount": "500", "verified_at": "2026-01-10"}]}
        self.assertEqual(app_module.pending_slips_count(), 0)
        self.assertEqual(app_module.slip_status_for_task("task-1"), None)
        app_module.write_slips(slips)
        self.assertEqual(app_module.slips_for_task("task-1")[0]["amount"], "500")
        self.assertEqual(app_module.revenue_analytics(slips)["total"], 500)
        self.assertEqual(app_module.crm_summary([task])[0]["total_spend"], 1070)
        self.assertEqual(app_module.invoice_for_task(task)["total"], 1070)
        self.assertEqual(app_module.payment_amount_for_task(task, None, "balance"), 535)
        self.assertEqual(app_module.build_analytics([task])["completion_rate"], 0)

    def test_export_data_bundle_has_json_and_zip_modes(self):
        task = self.sample_task()
        app_module.write_tasks([task])
        bundle = app_module.export_data_bundle()
        self.assertEqual(bundle["app"], "zerphyrus")
        self.assertEqual(bundle["files"]["tasks.json"][0]["id"], "task-1")
        self.assertIn("customers.json", bundle["files"])

        stamp, zip_bytes = app_module.export_data_bundle(include_uploads=True)
        self.assertRegex(stamp, r"^\d{8}_\d{4}$")
        with zipfile.ZipFile(app_module._io.BytesIO(zip_bytes)) as archive:
            names = set(archive.namelist())
        self.assertIn("zerphyrus_data.json", names)
        self.assertIn("tasks.json", names)

    def test_json_data_store_and_storage_helpers(self):
        store = data_store.JsonDataStore()
        store.write("sample.json", {"ok": True})
        self.assertEqual(store.read("sample.json", {})["ok"], True)
        self.assertEqual(store.read("missing.json", {"fallback": True})["fallback"], True)
        self.assertEqual(storage_backend.normalize_storage_path("\\slips\\proof.png"), "slips/proof.png")
        self.assertFalse(storage_backend.storage_enabled())

    def test_request_cache_preloads_data_once_per_request(self):
        class CountingStore:
            def __init__(self):
                self.read_calls = []
                self.read_many_calls = []

            def read(self, name, default=None):
                self.read_calls.append(name)
                return {"name": name}

            def read_many(self, names):
                self.read_many_calls.append(list(names))
                return {name: {"name": name} for name in names}

            def write(self, name, data):
                return True

            def init_file(self, name, default):
                return None

        original_store = data_store._STORE
        store = CountingStore()
        data_store._STORE = store
        try:
            with flask_app.test_request_context("/"):
                data_store.preload_data(["a.json", "b.json", "a.json"])
                self.assertEqual(data_store.read_data("a.json")["name"], "a.json")
                self.assertEqual(data_store.read_data("b.json")["name"], "b.json")
                self.assertEqual(data_store.read_data("c.json")["name"], "c.json")

            self.assertEqual(store.read_many_calls, [["a.json", "b.json"]])
            self.assertEqual(store.read_calls, ["c.json"])
        finally:
            data_store._STORE = original_store

    def test_task_file_listing_uses_correct_upload_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_folder = app_module.MODEL_3D_FOLDER
            app_module.MODEL_3D_FOLDER = tmp
            try:
                Path(tmp, "part.stl").write_text("solid test\nendsolid test", encoding="utf-8")
                task = {"specs_3d": {"files": [{"filename": "part.stl", "original": "part.stl"}]}}
                files = app_module.uploaded_task_files(task)
                self.assertEqual(files[0]["url"], "/uploads/3d_models/part.stl")
                self.assertTrue(files[0]["exists"])
                self.assertGreater(files[0]["size"], 0)
            finally:
                app_module.MODEL_3D_FOLDER = old_folder

    def test_pdf_generation_smoke(self):
        task = self.sample_task()
        task["specs_3d"] = {"material": "PLA", "quantity": "1", "files": []}
        self.assertEqual(pdf_generator.FONT_NORMAL, "_ThaiN")
        self.assertIn("NotoSansThai-Regular.ttf", pdf_generator.FONT_SOURCE.replace("\\", "/"))
        self.assertTrue(pdf_generator.generate_order_pdf(task).startswith(b"%PDF"))
        self.assertTrue(pdf_generator.generate_spec_sheet(task).startswith(b"%PDF"))


class FlaskRouteSmokeTests(unittest.TestCase):
    def setUp(self):
        reset_json()
        self.client = csrf_client()

    def test_public_get_routes_render(self):
        for path in ["/", "/model", "/tracking", "/catalog", "/cart", "/checkin", "/customer/register", "/customer/login", "/webhook", "/healthz", "/health"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertLess(response.status_code, 500)

    def test_standalone_pages_are_linked_into_app(self):
        studio = self.client.get("/studio", buffered=True)
        self.assertEqual(studio.status_code, 200)
        self.assertIn(b"Premium Manufacturing Studio", studio.data)

        lesson = self.client.get("/extras/if-clause", buffered=True)
        self.assertEqual(lesson.status_code, 200)
        self.assertIn(b"If Clause", lesson.data)

    def test_healthcheck_reports_service_status(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app"], "zerphyrus")

    def test_order_submission_creates_task_ticket_and_events(self):
        response = self.client.post("/submit_order", data={
            "csrf_token": "test-token",
            "customer_name": "Ada",
            "customer_phone": "0812345678",
            "customer_email": "ada@example.com",
            "task_title": "Custom stand",
            "service_type": "design",
            "quantity": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(app_module.read_tasks()), 1)
        self.assertEqual(len(app_module.read_tickets()), 1)
        self.assertGreaterEqual(len(app_module.read_events()), 2)

    def test_login_and_admin_json_route(self):
        response = self.client.post("/login", data={
            "csrf_token": "test-token",
            "username": "admin",
            "password": "admin123",
        })
        self.assertEqual(response.status_code, 302)
        task = AppHelperTests().sample_task()
        task["specs_3d"] = {"files": [{"filename": "missing.stl"}]}
        app_module.write_tasks([task])
        response = self.client.get("/admin/task_files/task-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["files"][0]["url"], "/uploads/3d_models/missing.stl")

    def test_admin_can_add_admin_user(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

        response = self.client.post("/admin/users/add", data={
            "csrf_token": "test-token",
            "username": "staff_admin",
            "password": "secret123",
            "password2": "secret123",
        })
        self.assertEqual(response.status_code, 302)
        users = app_module.read_users()
        self.assertIn("staff_admin", users)
        self.assertNotEqual(users["staff_admin"], "secret123")
        self.assertTrue(app_module.verify_password(users["staff_admin"], "secret123"))

        self.client.get("/logout")
        response = self.client.post("/login", data={
            "csrf_token": "test-token",
            "username": "staff_admin",
            "password": "secret123",
        })
        self.assertEqual(response.status_code, 302)

    def test_admin_add_user_validates_input(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

        response = self.client.post("/admin/users/add", data={
            "csrf_token": "test-token",
            "username": "bad user",
            "password": "secret123",
            "password2": "secret123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("bad user", app_module.read_users())

    def test_admin_product_add_persists_and_validates(self):
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

        response = self.client.post("/admin/products/add", data={
            "csrf_token": "test-token",
            "name": "PLA spool",
            "description": "Material",
            "price": "1,299",
            "stock": "7",
            "category": "Filament",
            "active": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        products = app_module.read_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["name"], "PLA spool")
        self.assertEqual(products[0]["price"], 1299)
        self.assertTrue(products[0]["active"])

        response = self.client.post("/admin/products/add", data={
            "csrf_token": "test-token",
            "name": "Broken stock",
            "price": "99",
            "stock": "many",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_stock")
        self.assertEqual(len(app_module.read_products()), 1)

    def test_admin_product_add_reports_persistence_failure(self):
        class FailingStore:
            def read(self, name, default=None):
                return [] if name == "products.json" else default

            def read_many(self, names):
                return {}

            def write(self, name, data):
                return False

            def init_file(self, name, default):
                return None

        original_store = data_store._STORE
        data_store._STORE = FailingStore()
        try:
            with self.client.session_transaction() as sess:
                sess["username"] = "admin"

            response = self.client.post("/admin/products/add", data={
                "csrf_token": "test-token",
                "name": "Unwritten",
                "price": "99",
            })
            self.assertEqual(response.status_code, 500)
            self.assertEqual(response.get_json()["code"], "persist_failed")
        finally:
            data_store._STORE = original_store

    def test_line_config_saves_line_and_twilio_settings(self):
        Path(".env").write_text("SECRET_KEY=keep-me\n", encoding="utf-8")
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

        response = self.client.post("/admin/line_config", data={
            "csrf_token": "test-token",
            "LINE_CHANNEL_ACCESS_TOKEN": "line-token",
            "LINE_CHANNEL_SECRET": "line-secret",
            "ADMIN_LINE_USER_ID": "Uadmin",
            "TWILIO_ACCOUNT_SID": "AC123",
            "TWILIO_AUTH_TOKEN": "twilio-token",
            "TWILIO_FROM": "+15551234567",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(os.environ["LINE_CHANNEL_SECRET"], "line-secret")
        self.assertEqual(os.environ["TWILIO_ACCOUNT_SID"], "AC123")
        env_text = Path(".env").read_text(encoding="utf-8")
        self.assertIn("SECRET_KEY=keep-me", env_text)
        self.assertIn("LINE_CHANNEL_ACCESS_TOKEN=line-token", env_text)
        self.assertIn("TWILIO_FROM=+15551234567", env_text)

    def test_line_config_saves_settings_on_vercel_without_env_file(self):
        os.environ["VERCEL"] = "1"
        try:
            with self.client.session_transaction() as sess:
                sess["username"] = "admin"

            response = self.client.post("/admin/line_config", data={
                "csrf_token": "test-token",
                "PROMPTPAY_PHONE": "089-111-2222",
                "COMPANY_NAME": "Deploy Shop",
                "PREFERRED_SCHEME": "https",
                "EXTERNAL_URL": "https://example.com",
            })
            self.assertEqual(response.status_code, 200)
            self.assertFalse(Path(".env").exists())
            self.assertEqual(app_module.read_settings()["PROMPTPAY_PHONE"], "089-111-2222")
            self.assertEqual(app_module.current_promptpay_phone(), "089-111-2222")
            self.assertIn(b"089-111-2222", response.data)
        finally:
            os.environ.pop("VERCEL", None)

    def test_line_webhook_signature_accepts_empty_events(self):
        os.environ["LINE_CHANNEL_SECRET"] = "line-secret"
        body = b'{"events":[]}'
        digest = hmac.new(b"line-secret", body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode("ascii")

        self.assertTrue(line_handler.verify_signature(body, signature))
        response = self.client.post(
            "/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Line-Signature": signature},
        )
        self.assertEqual(response.status_code, 200)

    def test_line_handler_finds_ticket_status(self):
        task = AppHelperTests().sample_task()
        task["sn"] = "ZP-0001"
        task["status"] = "inprogress"
        task["deadline"] = "2026-06-30"
        app_module.write_tasks([task])
        app_module.write_tickets({"ABCD1234": {"task_id": "task-1"}})

        text = line_handler.order_status_message("ABCD1234", app_module.read_tasks, app_module.read_tickets)
        self.assertIn("ZP-0001", text)
        self.assertIn("กำลังดำเนินการ", text)

    def test_customer_register_login_dashboard_flow(self):
        response = self.client.post("/customer/register", data={
            "csrf_token": "test-token",
            "name": "Ada",
            "phone": "0812345678",
            "email": "ada@example.com",
            "password": "secret123",
            "password2": "secret123",
        })
        self.assertEqual(response.status_code, 302)
        self.client.get("/customer/logout")
        response = self.client.post("/customer/login", data={
            "csrf_token": "test-token",
            "phone": "0812345678",
            "password": "secret123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertLess(self.client.get("/customer/dashboard").status_code, 500)

    def test_get_route_inventory_smoke(self):
        task = AppHelperTests().sample_task()
        task["status"] = "completed"
        task["quote"] = {"status": "approved", "amount": 500, "deposit_amount": 250, "balance_amount": 250}
        task["specs_3d"] = {"material": "PLA", "quantity": "1", "files": [{"filename": "missing.stl"}]}
        app_module.write_tasks([task])
        app_module.write_tickets({"ABCD1234": {
            "task_id": "task-1",
            "customer_name": "Ada",
            "customer_phone": "0812345678",
            "task_title": "Widget",
            "status": "active",
            "created_at": "2026-01-01T00:00:00",
            "checked_in_at": None,
            "checked_in_by": None,
        }})
        app_module.write_products([{
            "id": "prod-1",
            "name": "PLA spool",
            "description": "Material",
            "price": 199,
            "category": "Filament",
            "active": True,
            "stock": 5,
        }])
        app_module.write_customers({"0812345678": {"name": "Ada", "phone": "0812345678", "email": "ada@example.com"}})
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"
            sess["customer_phone"] = "0812345678"
            sess["customer_name"] = "Ada"

        paths = [
            "/", "/model", "/tracking?q=ada", "/healthz", "/payment/task-1", "/order_pdf/task-1",
            "/admin/order_pdf/task-1", "/admin/invoice/task-1", "/ticket/ABCD1234",
            "/checkin", "/webhook", "/login", "/contact", "/gallery", "/review/task-1",
            "/admin", "/admin/task_events/task-1", "/admin/notifications", "/admin/backup",
            "/admin/export_data.json", "/admin/export_data.zip",
            "/admin/customer/0812345678", "/admin/job_sheet/task-1", "/api/yearly/2026",
            "/admin/line_config", "/catalog", "/product/prod-1", "/cart", "/cart/checkout",
            "/admin/products", "/admin/export_excel", "/admin/spec_sheet/task-1",
            "/admin/task_files/task-1", "/customer/dashboard", "/customer/profile",
            "/studio", "/extras/if-clause",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path, buffered=True)
                self.assertLess(response.status_code, 500)

    def test_admin_export_data_routes_download_data(self):
        task = AppHelperTests().sample_task()
        app_module.write_tasks([task])
        with self.client.session_transaction() as sess:
            sess["username"] = "admin"

        response = self.client.get("/admin/export_data.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["files"]["tasks.json"][0]["id"], "task-1")
        self.assertIn("attachment", response.headers["Content-Disposition"])

        response = self.client.get("/admin/export_data.zip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/zip")


if __name__ == "__main__":
    unittest.main()
