#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GENERATED = DATA / "generated"
MASTER = GENERATED / "master"
WORKBOOKS = GENERATED / "workbooks"
CONTROL = DATA / "control"
SCHEMA_PATH = DATA / "schema.json"
OVERRIDES_PATH = CONTROL / "admin_overrides.json"

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    return s or "workbook"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def col_to_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref)
    if not letters:
        return 0
    n = 0
    for ch in letters.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def clean_scalar(value: Any) -> Any:
    if isinstance(value, str):
        v = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        return v if v != "" else None
    return value


def unique_headers(row: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for i, raw in enumerate(row):
        base = str(raw).strip() if raw not in (None, "") else f"Column_{i+1}"
        base = re.sub(r"\s+", " ", base)
        count = seen.get(base, 0) + 1
        seen[base] = count
        out.append(base if count == 1 else f"{base}__{count}")
    return out


@dataclass
class SheetData:
    name: str
    rows: list[list[Any]]
    formulas: dict[str, str]


class XLSXReader:
    def __init__(self, path: Path):
        self.path = path

    def _shared_strings(self, z: zipfile.ZipFile) -> list[str]:
        try:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        result: list[str] = []
        for si in root.findall(f"{{{NS_MAIN}}}si"):
            texts: list[str] = []
            for t in si.iter(f"{{{NS_MAIN}}}t"):
                texts.append(t.text or "")
            result.append("".join(texts))
        return result

    def _sheet_targets(self, z: zipfile.ZipFile) -> list[tuple[str, str]]:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in rels.findall(f"{{{NS_PKG_REL}}}Relationship")
        }
        output: list[tuple[str, str]] = []
        sheets = wb.find(f"{{{NS_MAIN}}}sheets")
        if sheets is None:
            return output
        for s in sheets:
            name = s.attrib.get("name", "Sheet")
            rid = s.attrib.get(f"{{{NS_REL}}}id")
            target = rel_map.get(rid or "", "")
            if target.startswith("/"):
                target = target.lstrip("/")
            elif not target.startswith("xl/"):
                target = "xl/" + target.lstrip("/")
            output.append((name, target))
        return output

    def read(self) -> list[SheetData]:
        with zipfile.ZipFile(self.path) as z:
            shared = self._shared_strings(z)
            sheets: list[SheetData] = []
            for name, target in self._sheet_targets(z):
                try:
                    root = ET.fromstring(z.read(target))
                except KeyError:
                    continue
                row_map: dict[int, dict[int, Any]] = {}
                formulas: dict[str, str] = {}
                max_col = 0
                max_row = 0
                sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
                if sheet_data is None:
                    sheets.append(SheetData(name, [], {}))
                    continue
                for row in sheet_data.findall(f"{{{NS_MAIN}}}row"):
                    r_idx = int(row.attrib.get("r", "1")) - 1
                    max_row = max(max_row, r_idx)
                    row_map.setdefault(r_idx, {})
                    for c in row.findall(f"{{{NS_MAIN}}}c"):
                        ref = c.attrib.get("r", "A1")
                        c_idx = col_to_index(ref)
                        max_col = max(max_col, c_idx)
                        t = c.attrib.get("t")
                        f = c.find(f"{{{NS_MAIN}}}f")
                        if f is not None and f.text:
                            formulas[ref] = f.text
                        value: Any = None
                        if t == "inlineStr":
                            is_node = c.find(f"{{{NS_MAIN}}}is")
                            if is_node is not None:
                                value = "".join((n.text or "") for n in is_node.iter(f"{{{NS_MAIN}}}t"))
                        else:
                            v = c.find(f"{{{NS_MAIN}}}v")
                            raw = v.text if v is not None else None
                            if raw is not None:
                                if t == "s":
                                    try:
                                        value = shared[int(raw)]
                                    except (ValueError, IndexError):
                                        value = raw
                                elif t == "b":
                                    value = raw == "1"
                                elif t in ("str", "e"):
                                    value = raw
                                else:
                                    try:
                                        num = float(raw)
                                        value = int(num) if num.is_integer() else num
                                    except ValueError:
                                        value = raw
                        row_map[r_idx][c_idx] = clean_scalar(value)
                rows: list[list[Any]] = []
                for r in range(max_row + 1):
                    vals = [row_map.get(r, {}).get(c) for c in range(max_col + 1)]
                    while vals and vals[-1] is None:
                        vals.pop()
                    rows.append(vals)
                while rows and not any(v is not None for v in rows[-1]):
                    rows.pop()
                sheets.append(SheetData(name, rows, formulas))
            return sheets


def rows_to_records(rows: list[list[Any]], header_row: int, start_row: int | None = None, end_row: int | None = None) -> tuple[list[str], list[dict[str, Any]]]:
    if header_row < 1 or header_row > len(rows):
        return [], []
    header = unique_headers(rows[header_row - 1])
    first = start_row or header_row + 1
    last = min(end_row or len(rows), len(rows))
    records: list[dict[str, Any]] = []
    for idx in range(first - 1, last):
        row = rows[idx] if idx < len(rows) else []
        padded = row + [None] * max(0, len(header) - len(row))
        record = {header[i]: clean_scalar(padded[i]) for i in range(len(header))}
        if any(v is not None for v in record.values()):
            record["_source_row"] = idx + 1
            records.append(record)
    return header, records


def match_workbook_config(filename: str, schema: dict[str, Any]) -> dict[str, Any] | None:
    low = filename.lower()
    for cfg in schema.get("workbooks", []):
        if str(cfg.get("match_contains", "")).lower() in low:
            return cfg
    return None


def deterministic_samco_id(activity_code: str, prefix: str, digits: int) -> str:
    seed = hashlib.sha1(activity_code.encode("utf-8")).hexdigest()[:14]
    number = int(seed, 16) % (10 ** digits)
    return f"{prefix}{number:0{digits}d}"


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def norm_key(record: dict[str, Any], candidates: list[str]) -> Any:
    for key in candidates:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def apply_record_overrides(records: list[dict[str, Any]], overrides: dict[str, Any], key_candidates: list[str]) -> list[dict[str, Any]]:
    if not overrides:
        return records
    out: list[dict[str, Any]] = []
    for rec in records:
        key = norm_key(rec, key_candidates)
        patch = overrides.get(str(key), {}) if key is not None else {}
        if isinstance(patch, dict):
            rec = {**rec, **patch}
        out.append(rec)
    return out


def parse_thresholds(rows: list[list[Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    section = "General"
    for idx, row in enumerate(rows, start=1):
        cells = [clean_scalar(x) for x in row]
        first = cells[0] if cells else None
        if isinstance(first, str) and re.match(r"^\d+\.\s", first):
            section = first
            continue
        if first is None:
            continue
        if idx <= 3:
            continue
        if isinstance(first, str) and first.lower() in {"risk level", "overhead type", "project type", "item", "type", "material"}:
            continue
        if len(cells) >= 2 and cells[1] is not None:
            result.append({
                "section": section,
                "item": first,
                "value": cells[1],
                "value_2": cells[2] if len(cells) > 2 else None,
                "notes": cells[3] if len(cells) > 3 else None,
                "_source_row": idx,
            })
    return result


def build_rates(datasets: dict[str, list[dict[str, Any]]], overrides: dict[str, Any]) -> list[dict[str, Any]]:
    rates: list[dict[str, Any]] = []

    for r in datasets.get("tender_material_rates", []):
        code = r.get("Code")
        if not code or str(code).startswith("Column_"):
            continue
        rates.append({
            "rate_id": str(code), "source": "Tender Pricing Workbook", "category": "Material",
            "description": r.get("Material Description"), "unit": r.get("Unit"),
            "rate": r.get("Avg Price (EGP) 3-mo avg") or r.get("Avg Price (EGP)\n3-mo avg") or r.get("Avg Price (EGP)"),
            "low": r.get("Low"), "high": r.get("High"), "confidence": r.get("Confidence"),
            "notes": r.get("Source / Notes")
        })

    for ds_name, cat in [("labor_reference_rates", "Labor"), ("equipment_reference_rates", "Equipment")]:
        for r in datasets.get(ds_name, []):
            code = r.get("Code")
            if not code:
                continue
            desc = r.get("Trade") or r.get("Equipment")
            rates.append({
                "rate_id": str(code), "source": "Tender Pricing Workbook", "category": cat,
                "description": desc, "unit": r.get("Unit"),
                "rate": r.get("Avg / Used (EGP)"), "low": r.get("Low (EGP)"), "high": r.get("High (EGP)"),
                "confidence": None, "notes": r.get("Source / Notes")
            })

    for r in datasets.get("concrete_mix_rates", []):
        grade = r.get("Grade")
        if not grade:
            continue
        rate = norm_key(r, ["TOTAL COST per m3 (EGP)", "TOTAL COST per m3 (EGP)__2", "TOTAL COST per m3 (EGP) "])
        if rate is None:
            for k, v in r.items():
                if "TOTAL COST" in k.upper():
                    rate = v
                    break
        rates.append({
            "rate_id": f"CONC-{grade}", "source": "Tender Pricing Workbook", "category": "Concrete Mix",
            "description": r.get("Description"), "unit": "m3", "rate": rate,
            "low": None, "high": None, "confidence": "Computed", "notes": "Computed from mix calculator baseline"
        })

    for r in datasets.get("resource_master", []):
        code = r.get("Resource Code")
        if not code:
            continue
        rates.append({
            "rate_id": str(code), "source": "Activity Library Workbook", "category": f"Resource Category {r.get('Resource Category')}",
            "description": r.get("Resource Description"), "unit": r.get("UOM"), "rate": r.get("Rate"),
            "low": None, "high": None, "confidence": "Corporate workbook", "notes": "Resource Unique List"
        })

    for r in datasets.get("manpower_rates", []):
        code = r.get("Manpower Main Code")
        if not code:
            continue
        rates.append({
            "rate_id": str(code), "source": "Activity Library Workbook", "category": "Manpower",
            "description": r.get("Organization Position"), "unit": "month", "rate": r.get("Total"),
            "low": None, "high": None, "confidence": "Corporate workbook", "notes": "Fully loaded manpower monthly rate"
        })

    for r in datasets.get("crew_rates", []):
        code = r.get("Resource Main code__2") or r.get("Resource Main code")
        crew = r.get("Crew Type__2") or r.get("Crew Type")
        if not code or not crew:
            continue
        rate = r.get("Crew rate/Hr")
        if rate is None:
            continue
        rates.append({
            "rate_id": str(code), "source": "Activity Library Workbook", "category": "Crew",
            "description": crew, "unit": r.get("UOM") or "MH", "rate": rate,
            "low": None, "high": None, "confidence": "Corporate workbook", "notes": "Crew hourly rate"
        })

    rate_overrides = overrides.get("rates", {}) if isinstance(overrides, dict) else {}
    rates = apply_record_overrides(rates, rate_overrides, ["rate_id"])
    return rates


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert every XLSX/XLSM in data/ into SAMCO governed JSON datasets.")
    parser.add_argument("--data-dir", default=str(DATA))
    parser.add_argument("--strict", action="store_true", help="Fail when a configured required column is missing")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    schema = load_json(SCHEMA_PATH, {})
    overrides = load_json(OVERRIDES_PATH, {})
    MASTER.mkdir(parents=True, exist_ok=True)
    WORKBOOKS.mkdir(parents=True, exist_ok=True)

    excel_files = sorted([p for p in data_dir.iterdir() if p.suffix.lower() in {".xlsx", ".xlsm"} and not p.name.startswith("~$")])
    warnings: list[str] = []
    errors: list[str] = []
    datasets: dict[str, list[dict[str, Any]]] = {}
    workbook_meta: list[dict[str, Any]] = []

    for path in excel_files:
        cfg = match_workbook_config(path.name, schema)
        role = cfg.get("role") if cfg else "unmapped_workbook"
        reader = XLSXReader(path)
        try:
            sheets = reader.read()
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        sheet_by_name = {s.name.strip(): s for s in sheets}
        raw_payload = {
            "source_file": path.name,
            "sha256": file_sha256(path),
            "generated_at": utc_now(),
            "role": role,
            "sheets": [
                {"name": s.name, "rows": s.rows, "formulas": s.formulas}
                for s in sheets
            ],
        }
        write_json(WORKBOOKS / f"{slugify(path.stem)}.json", raw_payload)
        workbook_meta.append({"file": path.name, "role": role, "sha256": raw_payload["sha256"], "sheet_count": len(sheets)})

        if not cfg:
            warnings.append(f"No schema mapping for workbook: {path.name}; raw JSON still generated")
            continue

        for sheet_name, scfg in cfg.get("sheets", {}).items():
            sheet = sheet_by_name.get(sheet_name)
            if not sheet:
                warnings.append(f"{path.name}: missing configured sheet '{sheet_name}'")
                continue
            dataset_name = scfg["dataset"]
            if dataset_name == "commercial_assumptions_raw":
                records = parse_thresholds(sheet.rows)
                header = []
            else:
                header, records = rows_to_records(sheet.rows, int(scfg.get("header_row", 1)))
            required = scfg.get("required", [])
            missing = [c for c in required if c not in header] if header else []
            if missing:
                msg = f"{path.name}/{sheet_name}: required columns missing: {missing}"
                (errors if args.strict else warnings).append(msg)
            for r in records:
                r["_source_workbook"] = path.name
                r["_source_sheet"] = sheet_name
            datasets.setdefault(dataset_name, []).extend(records)

        for sheet_name, sections in cfg.get("sections", {}).items():
            sheet = sheet_by_name.get(sheet_name)
            if not sheet:
                warnings.append(f"{path.name}: missing section sheet '{sheet_name}'")
                continue
            for section in sections:
                _, records = rows_to_records(
                    sheet.rows,
                    int(section["header_row"]),
                    int(section["start_row"]),
                    int(section["end_row"]),
                )
                for r in records:
                    r["_source_workbook"] = path.name
                    r["_source_sheet"] = sheet_name
                datasets.setdefault(section["name"], []).extend(records)

    identity = schema.get("identity", {})
    prefix = identity.get("activity_prefix", "SAM-CTO-")
    digits = int(identity.get("digits", 9))
    activity_overrides = overrides.get("activities", {}) if isinstance(overrides, dict) else {}
    activities = datasets.get("activity_master", [])
    for rec in activities:
        legacy = str(rec.get("Activity Code") or rec.get("Old Activity Code") or rec.get("_source_row"))
        generated = deterministic_samco_id(legacy, prefix, digits)
        override = activity_overrides.get(legacy, {}) if isinstance(activity_overrides, dict) else {}
        rec["SAMCO Master ID"] = override.get("SAMCO Master ID", generated) if isinstance(override, dict) else generated
        if isinstance(override, dict):
            rec.update({k: v for k, v in override.items() if k != "SAMCO Master ID"})

    additions = overrides.get("additions", {}) if isinstance(overrides, dict) else {}
    deletions = overrides.get("deletions", {}) if isinstance(overrides, dict) else {}
    for rec in additions.get("activities", []) if isinstance(additions, dict) else []:
        if not isinstance(rec, dict):
            continue
        rec = dict(rec)
        if not rec.get("SAMCO Master ID"):
            seed = str(rec.get("Activity Code") or rec.get("Activity description") or json.dumps(rec, sort_keys=True))
            rec["SAMCO Master ID"] = deterministic_samco_id(seed, prefix, digits)
        rec["_source_workbook"] = "Admin Override"
        rec["_source_sheet"] = "Admin Additions"
        activities.append(rec)
    activity_deletes = {str(x) for x in (deletions.get("activities", []) if isinstance(deletions, dict) else [])}
    activities = [r for r in activities if str(r.get("Activity Code")) not in activity_deletes and str(r.get("SAMCO Master ID")) not in activity_deletes]
    datasets["activity_master"] = activities

    resource_overrides = overrides.get("resources", {}) if isinstance(overrides, dict) else {}
    resources = apply_record_overrides(datasets.get("resource_master", []), resource_overrides, ["Resource Code"])
    for rec in additions.get("resources", []) if isinstance(additions, dict) else []:
        if isinstance(rec, dict): resources.append(dict(rec))
    resource_deletes = {str(x) for x in (deletions.get("resources", []) if isinstance(deletions, dict) else [])}
    resources = [r for r in resources if str(r.get("Resource Code")) not in resource_deletes]
    datasets["resource_master"] = resources

    rates = build_rates(datasets, overrides)
    for rec in additions.get("rates", []) if isinstance(additions, dict) else []:
        if isinstance(rec, dict): rates.append(dict(rec))
    rate_deletes = {str(x) for x in (deletions.get("rates", []) if isinstance(deletions, dict) else [])}
    rates = [r for r in rates if str(r.get("rate_id")) not in rate_deletes]

    assumptions = datasets.get("commercial_assumptions_raw", [])
    assumptions = apply_record_overrides(assumptions, overrides.get("assumptions", {}) if isinstance(overrides, dict) else {}, ["item"])
    for rec in additions.get("assumptions", []) if isinstance(additions, dict) else []:
        if isinstance(rec, dict): assumptions.append(dict(rec))
    assumption_deletes = {str(x) for x in (deletions.get("assumptions", []) if isinstance(deletions, dict) else [])}
    assumptions = [r for r in assumptions if str(r.get("item")) not in assumption_deletes]

    optional_history = list((data_dir / "optional" / "historical").glob("*.json")) if (data_dir / "optional" / "historical").exists() else []
    optional_live = list((data_dir / "optional" / "live").glob("*.json")) if (data_dir / "optional" / "live").exists() else []
    mode = "hybrid_predictive" if (optional_history or optional_live) else "baseline_only"

    write_json(MASTER / "activity_master.json", activities)
    write_json(MASTER / "resource_master.json", datasets.get("resource_master", []))
    write_json(MASTER / "rates.json", rates)
    write_json(MASTER / "commercial_assumptions.json", assumptions)

    for name, records in datasets.items():
        write_json(MASTER / f"{slugify(name)}.json", records)

    bundle = {
        "schema_version": schema.get("schema_version"),
        "generated_at": utc_now(),
        "mode": mode,
        "availability": {
            "excel_baseline": bool(excel_files),
            "historical_data": bool(optional_history),
            "live_project_data": bool(optional_live),
            "fallback_active": not bool(optional_history or optional_live),
        },
        "counts": {
            "activities": len(activities),
            "resources": len(datasets.get("resource_master", [])),
            "rates": len(rates),
            "assumptions": len(assumptions),
            "workbooks": len(workbook_meta),
        },
        "datasets": {
            "activities": activities,
            "resources": datasets.get("resource_master", []),
            "rates": rates,
            "commercial_assumptions": assumptions,
        },
    }
    write_json(MASTER / "fixed_data.bundle.json", bundle)
    manifest = {
        "generated_at": utc_now(),
        "mode": mode,
        "fallback_policy": schema.get("fallback_policy", {}),
        "workbooks": workbook_meta,
        "datasets": {k: len(v) for k, v in sorted(datasets.items())},
        "master_counts": bundle["counts"],
        "optional_sources": {
            "historical": [p.name for p in optional_history],
            "live": [p.name for p in optional_live],
        },
        "warnings": warnings,
        "errors": errors,
    }
    write_json(GENERATED / "catalog_manifest.json", manifest)
    write_json(GENERATED / "schema_report.json", {
        "generated_at": utc_now(),
        "schema": schema.get("schema_version"),
        "warnings": warnings,
        "errors": errors,
        "status": "error" if errors else ("warning" if warnings else "ok"),
    })

    print(f"Generated from {len(excel_files)} workbook(s).")
    print(f"Mode: {mode}")
    print(f"Activities: {len(activities)} | Resources: {len(datasets.get('resource_master', []))} | Rates: {len(rates)}")
    if warnings:
        print(f"Warnings: {len(warnings)} (see data/generated/schema_report.json)")
    if errors:
        print(f"Errors: {len(errors)}")
    return 1 if (args.strict and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
