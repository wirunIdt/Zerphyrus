import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT / "project"

sys.path.insert(0, str(PROJECT_DIR))
os.chdir(ROOT)

from data_store import SupabaseKVStore  # noqa: E402


DATA_FILES = [
    "tasks.json",
    "users.json",
    "stamps.json",
    "tickets.json",
    "slips.json",
    "products.json",
    "orders_cart.json",
    "sn_counter.json",
    "todos.json",
    "events.json",
    "notifications.json",
    "gallery.json",
    "reviews.json",
    "coupons.json",
    "invoices.json",
    "customers.json",
    "queue.json",
    "work_calendar.json",
]


def read_json(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def count_records(data):
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return len(data)
    return 1 if data is not None else 0


def migrate(dry_run=False):
    store = None if dry_run else SupabaseKVStore(strict=True)
    report = {
        "started_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "files": [],
    }
    for name in DATA_FILES:
        data = read_json(ROOT / name)
        row = {"name": name, "exists": data is not None, "records": count_records(data)}
        if data is not None and not dry_run:
            store.write(name, data)
            row["uploaded"] = True
        else:
            row["uploaded"] = False
        report["files"].append(row)
    report["finished_at"] = datetime.now().isoformat()
    out = ROOT / "migration_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description="Migrate Zerphyrus JSON data to Supabase KV storage.")
    parser.add_argument("--dry-run", action="store_true", help="Build a migration report without uploading.")
    args = parser.parse_args()
    report = migrate(dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
