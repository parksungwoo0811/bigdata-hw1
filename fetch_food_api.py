"""Fetch food nutrition data from MFDS open API and upsert into catalog_food."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Iterable, List

import requests

from nutrifit import create_app, db
from nutrifit.models import CatalogFood

DEFAULT_API_URL = (
    "https://apis.data.go.kr/1470000/FoodNtrIrdntInfoService1/"
    "getFoodNtrItdntList1"
)


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_page(api_key: str, page: int, per_page: int, api_url: str) -> List[dict]:
    params = {
        "serviceKey": api_key,
        "pageNo": page,
        "numOfRows": per_page,
        "type": "json",
    }
    resp = requests.get(api_url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    body = data.get("body") or data.get("Body") or {}
    items = body.get("items") or body.get("item") or data.get("items") or []
    if isinstance(items, dict):
        items = items.get("item", [])
    return items or []


def normalize(item: dict) -> dict | None:
    name = (item.get("DESC_KOR") or item.get("food_name") or "").strip()
    if not name:
        return None

    return {
        "name": name,
        "kcal": _to_float(item.get("NUTR_CONT1")),
        "carb_g": _to_float(item.get("NUTR_CONT2")),
        "protein_g": _to_float(item.get("NUTR_CONT3")),
        "fat_g": _to_float(item.get("NUTR_CONT4")),
        "tags": item.get("GROUP_NAME")
        or item.get("FOOD_CD")
        or "mfds",
    }


def bulk_insert(records: Iterable[dict], truncate: bool = False) -> int:
    app = create_app()
    with app.app_context():
        if truncate:
            CatalogFood.query.delete()
            db.session.commit()

        existing = {name for (name,) in db.session.query(CatalogFood.name)}
        to_insert = [rec for rec in records if rec and rec["name"] not in existing]
        if not to_insert:
            return 0
        db.session.bulk_insert_mappings(CatalogFood, to_insert)
        db.session.commit()
        return len(to_insert)


def main():
    parser = argparse.ArgumentParser(description="Fetch MFDS nutrition API data")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to fetch")
    parser.add_argument("--per-page", type=int, default=100, help="Rows per page")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete existing catalog before inserting",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Seconds to sleep between requests to avoid throttling",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Override API endpoint if necessary",
    )
    args = parser.parse_args()

    api_key = os.getenv("MFDS_API_KEY")
    if not api_key:
        raise SystemExit("MFDS_API_KEY is not set in environment or .env file")

    records: List[dict] = []
    for page in range(1, args.pages + 1):
        items = fetch_page(api_key, page, args.per_page, args.api_url)
        if not items:
            break
        for item in items:
            rec = normalize(item)
            if rec:
                records.append(rec)
        time.sleep(args.sleep)

    inserted = bulk_insert(records, truncate=args.truncate)
    print(f"Inserted {inserted} rows from MFDS API.")


if __name__ == "__main__":
    main()
