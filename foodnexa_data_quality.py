"""FOODNEXA Data Quality Engine V2.

Measures dataset documentation, traceability, analytical coverage and basic
technical coherence. It does NOT assess food safety or legal compliance.
Missing/unperformed tests are never converted to zero or treated as passing.
"""
from __future__ import annotations

import json
import math
import pandas as pd

# Metadata are separated from test results: optional tests do not become
# mandatory simply because their columns exist in a CSV export.
IDENTITY_FIELDS = ["batch_id", "product_name", "product_category"]
TRACEABILITY_FIELDS = ["sample_reference", "supplier", "sampling_date", "analysis_date", "laboratory", "analyst"]
METHOD_FIELDS = ["analysis_units", "analysis_methods", "applicable_limits_reference"]

ANALYSIS_GROUPS = {
    "Physico-chimique": [
        "temperature_celsius", "storage_days", "ph", "humidity_percent",
        "moisture_percent", "dry_matter_percent", "ash_percent", "protein_percent",
        "fat_percent", "titratable_acidity", "density", "conductivity",
        "viscosity", "brix", "salt_percent", "particle_size",
    ],
    "Microbiologique": [
        "total_viable_count", "enterobacteriaceae_count", "coliform_count",
        "e_coli_count", "yeast_mould_count", "staphylococcus_aureus_count",
        "bacillus_cereus_count", "listeria_monocytogenes_count", "salmonella_detected",
    ],
    "Contaminants": ["pesticide_residue", "lead", "cadmium", "mercury", "arsenic", "aflatoxin", "mycotoxin"],
    "Processus": ["processing_temperature_celsius", "processing_time_minutes", "cooling_temperature_celsius", "cooling_time_minutes", "cold_chain_broken", "hygiene_controlled", "pasteurized"],
    "Sensoriel": ["sensory_status"],
    "Emballage": ["net_weight", "seal_integrity_score", "vacuum_level"],
}

NUMERIC_RANGES = {
    "ph": (0, 14),
    "temperature_celsius": (-100, 150),
    "storage_days": (0, None),
    "humidity_percent": (0, 100), "moisture_percent": (0, 100),
    "dry_matter_percent": (0, 100), "ash_percent": (0, 100),
    "protein_percent": (0, 100), "fat_percent": (0, 100), "salt_percent": (0, 100),
    "total_viable_count": (0, None), "enterobacteriaceae_count": (0, None),
    "coliform_count": (0, None), "e_coli_count": (0, None),
    "yeast_mould_count": (0, None), "staphylococcus_aureus_count": (0, None),
    "bacillus_cereus_count": (0, None), "listeria_monocytogenes_count": (0, None),
    "processing_time_minutes": (0, None), "cooling_time_minutes": (0, None),
    "processing_temperature_celsius": (-100, 200), "cooling_temperature_celsius": (-100, 150),
    "seal_integrity_score": (0, 100),
}

MISSING_TEXT = {"", "nan", "none", "null", "na", "n/a", "non renseigné", "non renseigne", "non analysé", "non analysée", "non analyse", "non analysee", "non évalué", "non evalué", "non évaluée", "non evaluee"}


def _is_present(value):
    """Check presence without treating structured metadata as missing."""
    if value is None:
        return False
    if isinstance(value, (dict, list, tuple, set)):
        return len(value) > 0
    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return False
    except (TypeError, ValueError):
        pass
    return str(value).strip().casefold() not in MISSING_TEXT


def _available_fields(df, fields):
    return [f for f in fields if f in df.columns]


def _coverage(df, fields):
    fields = _available_fields(df, fields)
    if df.empty or not fields:
        return {"available": 0, "possible": len(df) * len(fields), "percent": 0.0, "fields": fields}
    count = sum(int(df[f].map(_is_present).sum()) for f in fields)
    possible = len(df) * len(fields)
    return {"available": count, "possible": possible, "percent": round(count / possible * 100, 1) if possible else 0.0, "fields": fields}


def _json_safe(value):
    """Convert nested cells to deterministic, hashable representations."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        normalized = [_json_safe(v) for v in value]
        return sorted(normalized, key=lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True, default=str))
    if hasattr(value, "item") and callable(getattr(value, "item", None)):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return value


def _duplicate_count(df):
    """Count exact duplicate rows, safely supporting dict/list metadata cells."""
    if df.empty:
        return 0
    safe = df.copy()
    for column in safe.columns:
        if safe[column].dtype == "object":
            safe[column] = safe[column].map(
                lambda value: json.dumps(
                    _json_safe(value), ensure_ascii=False, sort_keys=True, default=str,
                    separators=(",", ":")
                ) if isinstance(value, (dict, list, tuple, set)) else value
            )
    return int(safe.duplicated(keep="first").sum())


def _numeric_issues(df):
    issues = []
    for field, (low, high) in NUMERIC_RANGES.items():
        if field not in df.columns:
            continue
        raw = df[field]
        present = raw.map(_is_present)
        numeric = pd.to_numeric(raw, errors="coerce")
        invalid_text = present & numeric.isna()
        for idx in df.index[invalid_text]:
            issues.append({"Ligne": int(df.index.get_loc(idx)) + 1, "Champ": field, "Problème": "Valeur non numérique"})
        invalid_range = numeric.notna() & ((numeric < low) | ((numeric > high) if high is not None else False))
        for idx in df.index[invalid_range]:
            issues.append({"Ligne": int(df.index.get_loc(idx)) + 1, "Champ": field, "Problème": f"Valeur hors plage technique ({low} à {high if high is not None else 'sans maximum'})"})
    return issues


def generate_quality_report(df):
    """Return an explainable, non-regulatory dataset quality report."""
    data = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(df or [])
    rows, columns = len(data), len(data.columns)
    if data.empty:
        return {"rows": rows, "columns": columns, "quality_score": 0.0, "duplicates": 0,
                "coverage": {}, "issues": [], "issue_count": 0,
                "score_components": {}, "message": "Aucune observation à évaluer."}

    identity = _coverage(data, IDENTITY_FIELDS)
    trace = _coverage(data, TRACEABILITY_FIELDS)
    methods = _coverage(data, METHOD_FIELDS)
    groups = {name: _coverage(data, fields) for name, fields in ANALYSIS_GROUPS.items()}
    group_coverage = [v["percent"] for v in groups.values() if v["fields"]]
    analytical = round(sum(group_coverage) / len(group_coverage), 1) if group_coverage else 0.0

    # Weighted completeness: identity 30%, traceability 20%, method metadata
    # 10%, analytical coverage 30%, basic coherence 10%.
    issues = _numeric_issues(data)
    duplicates = _duplicate_count(data)
    identity_score = identity["percent"]
    trace_score = trace["percent"]
    method_score = methods["percent"]
    coherence_score = max(0.0, 100.0 - min(100.0, len(issues) / max(rows, 1) * 20.0))
    score = (identity_score * .30 + trace_score * .20 + method_score * .10 + analytical * .30 + coherence_score * .10)
    if duplicates:
        score *= max(0.0, 1 - min(duplicates / rows, 1) * .10)

    # Duplicates are flagged as review candidates; repeated batch IDs alone are allowed.
    if duplicates:
        issues.append({"Ligne": "—", "Champ": "Enregistrement", "Problème": f"{duplicates} doublon(s) exact(s) détecté(s)"})
    return {
        "rows": rows, "columns": columns, "quality_score": round(score, 1),
        "duplicates": duplicates,
        "coverage": {"Identité produit": identity, "Traçabilité": trace,
                     "Méthodes et unités": methods, "Analyses par domaine": groups},
        "score_components": {
            "Identité produit (30%)": round(identity_score, 1),
            "Traçabilité (20%)": round(trace_score, 1),
            "Méthodes/unités (10%)": round(method_score, 1),
            "Couverture analytique (30%)": analytical,
            "Cohérence technique (10%)": round(coherence_score, 1),
        },
        "issues": issues, "issue_count": len(issues),
        "message": "Les champs analytiques non renseignés sont considérés comme non documentés/non testés, jamais comme zéro ou conformes.",
        "interpretation": "Score de qualité documentaire et technique du dataset uniquement; ce n'est ni un score de sécurité sanitaire ni une décision de conformité réglementaire.",
    }
