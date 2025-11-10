"""
Utility script to ingest external nutrient tables (Excel or CSV) into the
CatalogFood table.

Usage examples:
    # 식품의약품안전처 통합 영양 성분 CSV 전체 추가
    python load_food_catalog.py \
        --path "data/식품의약품안전처_통합식품영양성분정보_20250630.csv" \
        --truncate

Requires pandas + openpyxl (already listed in requirements.txt).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from nutrifit import create_app, db
from nutrifit.models import CatalogFood

EXCEL_COLUMN_MAP = {
    "Food and Description(English)": "name",
    "Food groups": "food_group",
    "ENERC": "kcal",
    "PROCNP": "protein_g",
    "FAT": "fat_g",
    "CHOCDF": "carb_g",
}

CSV_COLUMN_MAP = {
    "식품명": "name",
    "에너지(kcal)": "kcal",
    "단백질(g)": "protein_g",
    "지방(g)": "fat_g",
    "탄수화물(g)": "carb_g",
}
CSV_TAG_FIELDS = [
    "데이터구분명",
    "출처명",
    "원산지국명",
    "데이터생성방법명",
]


def _coerce_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compose_tags(row, candidates: list[str]) -> str:
    tags: list[str] = []
    for col in candidates:
        if col not in row:
            continue
        val = row[col]
        if isinstance(val, str):
            cleaned = val.strip()
            if cleaned and cleaned.lower() != "nan":
                tags.append(cleaned)
        elif pd.notna(val):
            tags.append(str(val))
    # Preserve order but deduplicate
    seen = set()
    unique = []
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        unique.append(tag)
    return ",".join(unique)


def load_from_excel(path: Path, limit: int | None = None) -> List[dict]:
    df = pd.read_excel(
        path,
        header=3,
        engine="openpyxl",
        dtype=str,
    )
    df.columns = [str(col).strip() for col in df.columns]
    rename_map = {
        src: dest for src, dest in EXCEL_COLUMN_MAP.items() if src in df.columns
    }
    if not rename_map:
        raise KeyError(
            "Could not find expected header columns in the Excel sheet. "
            "확보한 엑셀 파일의 헤더 구조가 표준 영양 데이터 양식과 일치하는지 확인하세요."
        )

    df = df.rename(columns=rename_map)
    if "name" not in df.columns:
        raise KeyError("Missing 'Food and Description(English)' column in Excel file.")
    df = df[df["name"].notnull()]
    if limit:
        df = df.head(limit)

    records = []
    for _, row in df.iterrows():
        record = {
            "name": row["name"].strip(),
            "kcal": _coerce_float(row.get("kcal")) or 0.0,
            "protein_g": _coerce_float(row.get("protein_g")) or 0.0,
            "fat_g": _coerce_float(row.get("fat_g")) or 0.0,
            "carb_g": _coerce_float(row.get("carb_g")) or 0.0,
            "tags": row.get("food_group") or "",
        }
        records.append(record)
    return records


def load_from_csv(path: Path, limit: int | None = None) -> List[dict]:
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        dtype=str,
    )
    df.columns = [str(col).strip() for col in df.columns]
    rename_map = {src: dest for src, dest in CSV_COLUMN_MAP.items() if src in df.columns}
    if len(rename_map) < 5:
        raise KeyError(
            "Could not find required columns in the CSV. "
            "Confirm the file matches 식품의약품안전처 통합 영양 성분 다운로드 형식."
        )
    df = df.rename(columns=rename_map)
    if "name" not in df.columns:
        raise KeyError("CSV missing '식품명' column.")
    df = df[df["name"].notnull()]
    if limit:
        df = df.head(limit)

    tag_candidates = [col for col in CSV_TAG_FIELDS if col in df.columns]
    records = []
    for _, row in df.iterrows():
        record = {
            "name": row["name"].strip(),
            "kcal": _coerce_float(row.get("kcal")) or 0.0,
            "protein_g": _coerce_float(row.get("protein_g")) or 0.0,
            "fat_g": _coerce_float(row.get("fat_g")) or 0.0,
            "carb_g": _coerce_float(row.get("carb_g")) or 0.0,
            "tags": _compose_tags(row, tag_candidates),
        }
        records.append(record)
    return records


def load_records(path: Path, limit: int | None = None) -> List[dict]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return load_from_excel(path, limit)
    if suffix == ".csv":
        return load_from_csv(path, limit)
    raise ValueError(f"Unsupported file type for {path}. Use .xlsx or .csv.")


def bulk_insert(records: Iterable[dict], truncate: bool = False) -> int:
    app = create_app()
    with app.app_context():
        if truncate:
            CatalogFood.query.delete()
            db.session.commit()

        existing_rows = {
            name: row
            for name, row in db.session.query(CatalogFood.name, CatalogFood).all()
        }

        seen = set()
        to_insert: list[dict] = []
        updated = 0
        for rec in records:
            name = rec.get("name")
            if not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            row = existing_rows.get(name)
            if row:
                row.kcal = rec.get("kcal", row.kcal)
                row.protein_g = rec.get("protein_g", row.protein_g)
                row.fat_g = rec.get("fat_g", row.fat_g)
                row.carb_g = rec.get("carb_g", row.carb_g)
                row.tags = rec.get("tags", row.tags)
                updated += 1
            else:
                to_insert.append(rec)

        inserted = 0
        chunk_size = 5000
        for idx in range(0, len(to_insert), chunk_size):
            chunk = to_insert[idx : idx + chunk_size]
            db.session.bulk_insert_mappings(CatalogFood, chunk)
            inserted += len(chunk)

        db.session.commit()
        print(f"Updated {updated} existing rows.")
        return inserted


def main():
    parser = argparse.ArgumentParser(description="Load food catalog from CSV/XLSX files")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("data/식품의약품안전처_통합식품영양성분정보_20250630.csv"),
        help="Path to the source file (.csv or .xlsx)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of rows to ingest",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Remove existing catalog_food rows before inserting",
    )
    args = parser.parse_args()

    records = load_records(args.path, args.limit)
    inserted = bulk_insert(records, truncate=args.truncate)
    print(f"Inserted {inserted} new catalog_food rows.")


if __name__ == "__main__":
    main()
