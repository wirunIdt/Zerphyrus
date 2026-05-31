import os
from pathlib import Path

import requests


def storage_enabled():
    return bool(
        os.environ.get("SUPABASE_URL")
        and (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
        and os.environ.get("SUPABASE_STORAGE_BUCKET")
    )


def _config():
    return {
        "url": os.environ["SUPABASE_URL"].rstrip("/"),
        "key": os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_ANON_KEY"],
        "bucket": os.environ["SUPABASE_STORAGE_BUCKET"],
        "timeout": int(os.environ.get("SUPABASE_TIMEOUT", "20")),
    }


def _headers(content_type=None):
    cfg = _config()
    headers = {
        "apikey": cfg["key"],
        "Authorization": f"Bearer {cfg['key']}",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def normalize_storage_path(path):
    return str(Path(path).as_posix()).lstrip("/")


def upload_bytes(storage_path, data, content_type="application/octet-stream"):
    if not storage_enabled():
        return None
    cfg = _config()
    storage_path = normalize_storage_path(storage_path)
    resp = requests.post(
        f"{cfg['url']}/storage/v1/object/{cfg['bucket']}/{storage_path}",
        headers={**_headers(content_type), "x-upsert": "true"},
        data=data,
        timeout=cfg["timeout"],
    )
    resp.raise_for_status()
    return storage_path


def upload_path(storage_path, local_path, content_type="application/octet-stream"):
    if not storage_enabled():
        return None
    with open(local_path, "rb") as f:
        return upload_bytes(storage_path, f.read(), content_type)


def public_url(storage_path):
    if not storage_enabled():
        return None
    cfg = _config()
    storage_path = normalize_storage_path(storage_path)
    return f"{cfg['url']}/storage/v1/object/public/{cfg['bucket']}/{storage_path}"


def download_bytes(storage_path):
    if not storage_enabled():
        return None
    cfg = _config()
    storage_path = normalize_storage_path(storage_path)
    resp = requests.get(
        f"{cfg['url']}/storage/v1/object/{cfg['bucket']}/{storage_path}",
        headers=_headers(),
        timeout=cfg["timeout"],
    )
    resp.raise_for_status()
    return resp.content


def delete_object(storage_path):
    if not storage_enabled():
        return False
    cfg = _config()
    storage_path = normalize_storage_path(storage_path)
    resp = requests.delete(
        f"{cfg['url']}/storage/v1/object/{cfg['bucket']}",
        headers=_headers("application/json"),
        json={"prefixes": [storage_path]},
        timeout=cfg["timeout"],
    )
    resp.raise_for_status()
    return True
