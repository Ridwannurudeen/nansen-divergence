"""Scan result caching — stores latest scan as JSON file."""

import json
import os
from datetime import datetime, timezone

DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".nansen-divergence", "cache")


def save_cached_scan(data: dict, cache_dir: str | None = None) -> str:
    d = cache_dir or DEFAULT_CACHE_DIR
    os.makedirs(d, exist_ok=True)
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    path = os.path.join(d, "latest.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def get_latest_scan(cache_dir: str | None = None) -> dict | None:
    d = cache_dir or DEFAULT_CACHE_DIR
    path = os.path.join(d, "latest.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
