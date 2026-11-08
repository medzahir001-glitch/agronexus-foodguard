"""FOODNEXA Scientific Data Cleaning Engine V1.

Non-destructive preprocessing for research observations.
- Never writes to Supabase or overwrites the source dataset.
- Never converts missing or untested results to zero.
- Flags implausible values and statistical outliers; never deletes rows automatically.
- Converts units only when an explicit, recognized unit is supplied.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import pandas as pd


NESTED_JSON_COLUMNS = [
    "physicochemical_results", "microbiological_results", "contaminant_results",
    "process_data", "sensory_results", "packaging_results",
]

NUMERIC_COLUMNS = [
    "temperature_celsius", "storage_days", "ph", "humidity_percent",
    "moisture_percent", "dry_matter_percent", "ash_percent", "protein_percent",
    "fat_percent", "titratable_acidity", "density", "conductivity", "viscosity",
    "brix", "salt_percent", "particle_size", "total_viable_count",
    "enterobacteriaceae_count", "coliform_count", "e_coli_count",
    "yeast_mould_count", "staphylococcus_aureus_count", "bacillus_count",
    "lead", "cadmium", "mercury", "arsenic", "aflatoxin", "mycotoxin",
    "pesticide_residue",
]

# Broad technical plausibility screening ranges, not legal/product specifications.
PLAUSIBILITY = {
    "temperature_celsius": (-80, 100), "storage_days": (0, 36500), "ph": (0, 14),
    "humidity_percent": (0, 100), "moisture_percent": (0, 100),
    "dry_matter_percent": (0, 100), "ash_percent": (0, 100),
    "protein_percent": (0, 100), "fat_percent": (0, 100),
    "salt_percent": (0, 100), "brix": (0, 100), "particle_size": (0, 1_000_000),
    "total_viable_count": (0, 1e15), "enterobacteriaceae_count": (0, 1e15),
    "coliform_count": (0, 1e15), "e_coli_count": (0, 1e15),
    "yeast_mould_count": (0, 1e15), "staphylococcus_aureus_count": (0, 1e15),
    "bacillus_count": (0, 1e15), "lead": (0, 1e9), "cadmium": (0, 1e9),
    "mercury": (0, 1e9), "arsenic": (0, 1e9), "aflatoxin": (0, 1e9),
    "mycotoxin": (0, 1e9), "pesticide_residue": (0, 1e9),
}


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in {"", "nan", "none", "null", "<na>"}
    try:
        result = pd.isna(value)
        return bool(result) if not hasattr(result, "__len__") else False
    except (TypeError, ValueError):
        return False


def _parse_mapping(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def _flatten_nested(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy(deep=True).reset_index(drop=True)
    for column in NESTED_JSON_COLUMNS:
        if column not in data.columns:
            continue
        mappings = [_parse_mapping(v) for v in data[column].tolist()]
        keys = []
        for item in mappings:
            for key in item:
                key = str(key).strip()
                if key and key not in keys:
                    keys.append(key)
        for key in keys:
            if key not in data.columns:
                data[key] = [item.get(key, pd.NA) for item in mappings]
            else:
                values = data[key].tolist()
                for i, item in enumerate(mappings):
                    if i < len(values) and _missing(values[i]) and key in item:
                        values[i] = item[key]
                data[key] = pd.Series(values, dtype="object")
    return data


def _unit_map(value: Any) -> dict:
    return _parse_mapping(value)


def _convert_explicit_unit(field: str, value: float, unit: Any):
    """Return (converted value, canonical unit, note); otherwise preserve as entered."""
    u = str(unit).strip().casefold().replace("°", "").replace(" ", "") if not _missing(unit) else ""
    if field == "temperature_celsius" and u in {"f", "fahrenheit", "degf"}:
        return (value - 32) * 5 / 9, "°C", "Converted °F to °C using the explicitly recorded unit."
    if field == "temperature_celsius" and u in {"c", "celsius", "degc"}:
        return value, "°C", "Explicit Celsius unit confirmed."
    if field in {"lead", "cadmium", "mercury", "arsenic", "aflatoxin", "mycotoxin", "pesticide_residue"}:
        if u in {"ug/kg", "µg/kg", "mcg/kg"}:
            return value / 1000, "mg/kg", "Converted µg/kg to mg/kg using the explicitly recorded unit."
        if u == "mg/kg":
            return value, "mg/kg", "Explicit mg/kg unit confirmed."
    # Do not infer a unit or convert CFU/g to CFU/mL, etc.
    return value, (str(unit).strip() if not _missing(unit) else "Not specified"), "No conversion: unit missing or no safe conversion rule."


def clean_research_dataset(frame: pd.DataFrame):
    """Create a cleaned working copy, row-level audit log, and summary."""
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    raw = frame.copy(deep=True)
    data = _flatten_nested(raw)
    audit = []
    row_flags = [[] for _ in range(len(data))]

    # Trim text values without changing the source frame.
    for column in data.columns:
        if data[column].dtype == "object":
            values = data[column].tolist()
            cleaned = []
            for i, value in enumerate(values):
                if isinstance(value, str):
                    new_value = value.strip()
                    if new_value != value:
                        audit.append({"row": i + 1, "batch_id": data.iloc[i].get("batch_id", ""), "field": column, "action": "Trim whitespace", "original": value, "processed": new_value, "status": "Cleaned"})
                    cleaned.append(pd.NA if new_value.casefold() in {"", "nan", "none", "null"} else new_value)
                else:
                    cleaned.append(value)
            data[column] = pd.Series(cleaned, dtype="object")

    # Explicit-unit lookup; JSON object keys are expected to match field names.
    units_by_row = [_unit_map(v) for v in data.get("analysis_units", pd.Series([{}] * len(data))).tolist()]

    for field in NUMERIC_COLUMNS:
        if field not in data.columns:
            continue
        original_values = data[field].tolist()
        processed_values = []
        for i, original in enumerate(original_values):
            if _missing(original):
                processed_values.append(pd.NA)
                continue
            try:
                number = float(str(original).replace(",", ".").strip())
                if not math.isfinite(number):
                    raise ValueError("Non-finite number")
            except (TypeError, ValueError, OverflowError):
                processed_values.append(pd.NA)
                row_flags[i].append(f"{field}: valeur non numérique")
                audit.append({"row": i + 1, "batch_id": data.iloc[i].get("batch_id", ""), "field": field, "action": "Invalid numeric value flagged", "original": str(original), "processed": "Missing in cleaned copy", "status": "Review required"})
                continue

            unit = units_by_row[i].get(field) if i < len(units_by_row) else None
            converted, canonical_unit, note = _convert_explicit_unit(field, number, unit)
            if converted != number or (not _missing(unit) and canonical_unit != str(unit).strip()):
                audit.append({"row": i + 1, "batch_id": data.iloc[i].get("batch_id", ""), "field": field, "action": "Explicit unit normalization", "original": f"{number} {unit}", "processed": f"{converted:.8g} {canonical_unit}", "status": "Converted"})
            elif not _missing(unit) and field == "temperature_celsius":
                audit.append({"row": i + 1, "batch_id": data.iloc[i].get("batch_id", ""), "field": field, "action": "Unit review", "original": f"{number} {unit}", "processed": f"{converted:.8g} {canonical_unit}", "status": "Reviewed"})
            low_high = PLAUSIBILITY.get(field)
            if low_high and not (low_high[0] <= converted <= low_high[1]):
                row_flags[i].append(f"{field}: hors plage de plausibilité technique")
                audit.append({"row": i + 1, "batch_id": data.iloc[i].get("batch_id", ""), "field": field, "action": "Plausibility range flag", "original": str(original), "processed": str(converted), "status": "Review required"})
            processed_values.append(converted)
        data[field] = pd.Series(processed_values, dtype="object")

    # IQR screening: flags only, no automatic deletion or winsorization.
    for field in NUMERIC_COLUMNS:
        if field not in data.columns:
            continue
        numeric = pd.to_numeric(data[field], errors="coerce").dropna()
        if len(numeric) < 4:
            continue
        q1, q3 = numeric.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        for idx, value in pd.to_numeric(data[field], errors="coerce").items():
            if pd.notna(value) and (value < lower or value > upper):
                row_flags[idx].append(f"{field}: statistical outlier (IQR)")
                audit.append({"row": idx + 1, "batch_id": data.iloc[idx].get("batch_id", ""), "field": field, "action": "IQR outlier flag", "original": str(value), "processed": str(value), "status": "Review required; retained"})

    # Exact duplicate rows are identified, not removed.
    try:
        duplicate_mask = data.astype("string").fillna("<MISSING>").duplicated(keep="first")
    except (TypeError, ValueError):
        duplicate_mask = pd.Series(False, index=data.index)
    for idx in data.index[duplicate_mask]:
        row_flags[idx].append("Exact duplicate observation")
        audit.append({"row": idx + 1, "batch_id": data.iloc[idx].get("batch_id", ""), "field": "__row__", "action": "Exact duplicate detection", "original": "Duplicate row", "processed": "Retained", "status": "Review required"})

    data["cleaning_flags"] = ["; ".join(flags) if flags else "Aucun signalement" for flags in row_flags]
    data["cleaning_status"] = ["À vérifier" if flags else "Prétraitement sans alerte" for flags in row_flags]

    # A transparent audit entry for missing values: count only, never impute.
    missing_count = int(data.isna().sum().sum())
    summary = {
        "rows_input": int(len(raw)),
        "rows_output": int(len(data)),
        "columns_output": int(len(data.columns)),
        "numeric_fields_processed": int(sum(1 for c in NUMERIC_COLUMNS if c in data.columns)),
        "rows_flagged": int(sum(bool(flags) for flags in row_flags)),
        "audit_events": int(len(audit)),
        "missing_cells_retained": missing_count,
        "duplicate_rows_flagged": int(duplicate_mask.sum()),
        "source_preserved": True,
        "automatic_row_deletion": False,
        "automatic_missing_value_imputation": False,
    }
    audit_df = pd.DataFrame(audit, columns=["row", "batch_id", "field", "action", "original", "processed", "status"])
    return data, audit_df, summary
