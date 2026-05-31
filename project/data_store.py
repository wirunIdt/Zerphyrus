import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

import requests


JSON_LOCK_TIMEOUT = int(os.environ.get("JSON_LOCK_TIMEOUT", "8"))
_THREAD_LOCK = RLock()


@contextmanager
def json_file_lock(path):
    lock_path = f"{path}.lock"
    deadline = time.time() + JSON_LOCK_TIMEOUT
    with _THREAD_LOCK:
        fd = None
        while fd is None:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(fd, str(os.getpid()).encode("ascii"))
            except FileExistsError:
                if time.time() > deadline:
                    raise TimeoutError(f"Could not lock {path}")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                os.close(fd)
            finally:
                try:
                    os.unlink(lock_path)
                except FileNotFoundError:
                    pass


class JsonDataStore:
    def read(self, name, default=None):
        try:
            with json_file_lock(name):
                with open(name, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return default

    def write(self, name, data):
        with json_file_lock(name):
            tmp = f"{name}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, name)

    def init_file(self, name, default):
        if not Path(name).exists():
            with open(name, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)


class SupabaseKVStore:
    def __init__(self):
        self.url = os.environ["SUPABASE_URL"].rstrip("/")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_ANON_KEY"]
        self.table = os.environ.get("SUPABASE_KV_TABLE", "zerphyrus_kv")
        self.timeout = int(os.environ.get("SUPABASE_TIMEOUT", "12"))

    @property
    def headers(self):
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    def read(self, name, default=None):
        try:
            resp = requests.get(
                f"{self.url}/rest/v1/{self.table}",
                headers=self.headers,
                params={"select": "data", "name": f"eq.{name}", "limit": "1"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return default
            resp.raise_for_status()
            rows = resp.json()
            return rows[0]["data"] if rows else default
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return default

    def write(self, name, data):
        resp = requests.post(
            f"{self.url}/rest/v1/{self.table}",
            headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "name"},
            json=[{"name": name, "data": data}],
            timeout=self.timeout,
        )
        resp.raise_for_status()

    def init_file(self, name, default):
        # On serverless hosts, app import must stay cheap and resilient.
        # Missing rows are handled by read defaults and writes will upsert later.
        return None


def _should_use_supabase():
    return (
        os.environ.get("DATA_BACKEND", "").lower() == "supabase"
        and os.environ.get("SUPABASE_URL")
        and (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
    )


_STORE = None


def get_store():
    global _STORE
    if _STORE is None:
        _STORE = SupabaseKVStore() if _should_use_supabase() else JsonDataStore()
    return _STORE


def reset_store_for_tests():
    global _STORE
    _STORE = None


def read_data(name, default=None):
    return get_store().read(name, default)


def write_data(name, data):
    return get_store().write(name, data)


def init_data(name, default):
    return get_store().init_file(name, default)
