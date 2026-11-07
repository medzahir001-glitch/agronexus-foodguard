"""FOODNEXA Data Quality & Validation Engine.

Explainable validation of research records. This module evaluates dataset
identity, traceability, documentation, technical plausibility and analytical
coverage. It does NOT determine food safety, legal compliance or product release.
Unperformed/missing tests remain NOT TESTED; they are never converted to zero.
"""
from __future__ import annotations

import pandas as pd

IDENTITY_FIELDS = ["batch_id", "product_name", "product_category"]
TRACEABILITY_FIELDS = ["sample_reference", "supplier", "sampling_date", "analysis_date", "laboratory", "analyst"]
METHOD_FIELDS = ["analysis_units", "analysis_methods", "applicable_limits_reference"]

ANALYSIS_GROUPS = {
    "Physico-chimique": [
        "temperature_celsius", "storage_days", "ph", "humidity_percent",
        "dry_matter_percent", "ash_percent", "protein_percent", "fat_percent",
        "titratable_acidity", "density", "conductivity", "viscosity", "brix",
        "salt_percent", "particle_size",
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

# Broad plausibility ranges only; these are NOT legal or product specifications.
NUMERIC_RANGES = {
    "ph": (0, 14), "temperature_celsius": (-100, 150), "storage_days": (0, None),
    "humidity_percent": (0, 100), "dry_matter_percent": (0, 100),
    "ash_percent": (0, 100), "protein_percent": (0, 100), "fat_percent": (0, 100),
    "salt_percent": (0, 100), "seal_integrity_score": (0, 100),
    "total_viable_count": (0, None), "enterobacteriaceae_count": (0, None),
    "coliform_count": (0, None), "e_coli_count": (0, None),
    "yeast_mould_count": (0, None), "staphylococcus_aureus_count": (0, None),
    "bacillus_cereus_count": (0, None), "listeria_monocytogenes_count": (0, None),
    "processing_time_minutes": (0, None), "cooling_time_minutes": (0, None),
    "processing_temperature_celsius": (-100, 200), "cooling_temperature_celsius": (-100, 150),
    "net_weight": (0, None), "vacuum_level": (0, None), "brix": (0, 100),
}

MISSING_TEXT = {"", "nan", "none", "null", "na", "n/a", "non renseigné", "non renseigne",
                "non analysé", "non analysée", "non analyse", "non analysee",
                "non évalué", "non evalué", "non évaluée", "non evaluee"}


def _present(value):
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return str(value).strip().casefold() not in MISSING_TEXT


def _coverage(df, fields):
    available_fields = [field for field in fields if field in df.columns]
    possible = len(df) * len(available_fields)
    available = sum(int(df[field].map(_present).sum()) for field in available_fields)
    return {"available": available, "possible": possible,
            "percent": round(available / possible * 100, 1) if possible else 0.0,
            "fields": available_fields}


def _add_issue(issues, row_number, field, problem, severity="À vérifier"):
    issues.append({"Ligne": row_number, "Champ": field, "Problème": problem, "Niveau": severity})


def _validate_numeric(df, issues):
    for field, (low, high) in NUMERIC_RANGES.items():
        if field not in df.columns:
            continue
        raw = df[field]
        present = raw.map(_present)
        numeric = pd.to_numeric(raw, errors="coerce")
        for pos in range(len(df)):
            if present.iloc[pos] and pd.isna(numeric.iloc[pos]):
                _add_issue(issues, pos + 1, field, "Valeur renseignée mais non numérique", "Erreur")
            elif pd.notna(numeric.iloc[pos]):
                value = numeric.iloc[pos]
                if value < low or (high is not None and value > high):
                    bound = f"{low} à {high}" if high is not None else f"supérieure ou égale à {low}"
                    _add_issue(issues, pos + 1, field, f"Valeur hors plage de plausibilité technique ({bound})", "Erreur")


def _validate_dates(df, issues):
    for field in ("sampling_date", "analysis_date"):
        if field not in df.columns:
            continue
        parsed = pd.to_datetime(df[field], errors="coerce", dayfirst=True)
        raw_present = df[field].map(_present)
        for pos in range(len(df)):
            if raw_present.iloc[pos] and pd.isna(parsed.iloc[pos]):
                _add_issue(issues, pos + 1, field, "Format de date non reconnu", "Erreur")
    if {"sampling_date", "analysis_date"}.issubset(df.columns):
        sampling = pd.to_datetime(df["sampling_date"], errors="coerce", dayfirst=True)
        analysis = pd.to_datetime(df["analysis_date"], errors="coerce", dayfirst=True)
        for pos in range(len(df)):
            if pd.notna(sampling.iloc[pos]) and pd.notna(analysis.iloc[pos]) and analysis.iloc[pos] < sampling.iloc[pos]:
                _add_issue(issues, pos + 1, "analysis_date", "La date d'analyse précède la date de prélèvement", "Erreur")


def _validate_categories(df, issues):
    allowed = {
        "salmonella_detected": {"détectée", "detectee", "non détectée", "non detectee", "oui", "non", "true", "false"},
        "sensory_status": {"conforme", "non conforme"},
        "expert_risk_label": {"faible", "modéré", "modere", "élevé", "eleve"},
        "nonconformity_detected": {"oui", "non", "true", "false"},
    }
    for field, choices in allowed.items():
        if field not in df.columns:
            continue
        for pos, value in enumerate(df[field].tolist()):
            if _present(value) and str(value).strip().casefold() not in choices:
                _add_issue(issues, pos + 1, field, "Valeur catégorielle inattendue; vérifier la nomenclature", "À vérifier")


def _validate_logic(df, issues):
    # These checks identify contradictions; they do not infer regulatory failure.
    if "pasteurized" in df.columns and "processing_temperature_celsius" in df.columns:
        pasteurized = df["pasteurized"].astype(str).str.strip().str.casefold()
        temp = pd.to_numeric(df["processing_temperature_celsius"], errors="coerce")
        for pos in range(len(df)):
            if pasteurized.iloc[pos] in {"oui", "true"} and pd.notna(temp.iloc[pos]) and temp.iloc[pos] <= 0:
                _add_issue(issues, pos + 1, "processing_temperature_celsius", "Vérifier la cohérence entre pasteurisation déclarée et température de traitement", "À vérifier")
    if "sampling_date" in df.columns and "analysis_date" in df.columns:
        # The chronological rule is implemented in _validate_dates.
        pass


def _duplicate_metrics(df):
    exact = int(df.duplicated(keep="first").sum()) if not df.empty else 0
    sample_duplicates = 0
    if "sample_reference" in df.columns:
        refs = df["sample_reference"].astype(str).str.strip()
        valid = refs[~refs.str.casefold().isin(MISSING_TEXT)]
        sample_duplicates = int(valid.duplicated(keep="first").sum())
    return exact, sample_duplicates


def generate_quality_report(df):
    """Return a backward-compatible, explainable data-quality report."""
    data = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(df or [])
    rows, columns = len(data), len(data.columns)
    if data.empty:
        return {"rows": rows, "columns": columns, "quality_score": 0.0, "duplicates": 0,
                "coverage": {}, "issues": [], "issue_count": 0, "score_components": {},
                "validation_status": "Aucune donnée", "validation_errors": 0,
                "validation_warnings": 0, "sample_reference_duplicates": 0,
                "message": "Aucune observation à évaluer.",
                "interpretation": "Score de qualité documentaire et technique uniquement; pas un score de sécurité sanitaire."}

    identity = _coverage(data, IDENTITY_FIELDS)
    trace = _coverage(data, TRACEABILITY_FIELDS)
    methods = _coverage(data, METHOD_FIELDS)
    groups = {name: _coverage(data, fields) for name, fields in ANALYSIS_GROUPS.items()}
    # Average only across domains represented in the dataset schema. Missing tests
    # are untested, not failures; an absent whole domain is not silently invented.
    represented = [item["percent"] for item in groups.values() if item["fields"]]
    analytical = round(sum(represented) / len(represented), 1) if represented else 0.0

    issues = []
    _validate_numeric(data, issues)
    _validate_dates(data, issues)
    _validate_categories(data, issues)
    _validate_logic(data, issues)
    exact_duplicates, sample_duplicates = _duplicate_metrics(data)
    if exact_duplicates:
        _add_issue(issues, "—", "Enregistrement", f"{exact_duplicates} doublon(s) exact(s) détecté(s)", "À vérifier")
    if sample_duplicates:
        _add_issue(issues, "—", "sample_reference", f"{sample_duplicates} référence(s) d'échantillon répétée(s); vérifier s'il s'agit d'une ressaisie ou d'une répétition analytique", "À vérifier")

    error_count = sum(1 for item in issues if item["Niveau"] == "Erreur")
    warning_count = len(issues) - error_count
    coherence = max(0.0, 100.0 - min(100.0, error_count / max(rows, 1) * 20.0))
    score = (identity["percent"] * .30 + trace["percent"] * .20 + methods["percent"] * .10 + analytical * .30 + coherence * .10)
    if exact_duplicates:
        score *= max(0.0, 1 - min(exact_duplicates / rows, 1) * .10)

    status = "Erreurs à corriger" if error_count else "À compléter / vérifier" if warning_count else "Aucune anomalie détectée"
    return {
        "rows": rows, "columns": columns, "quality_score": round(score, 1),
        "duplicates": exact_duplicates, "sample_reference_duplicates": sample_duplicates,
        "coverage": {"Identité produit": identity, "Traçabilité": trace,
                     "Méthodes et unités": methods, "Analyses par domaine": groups},
        "score_components": {
            "Identité produit (30%)": round(identity["percent"], 1),
            "Traçabilité (20%)": round(trace["percent"], 1),
            "Méthodes/unités (10%)": round(methods["percent"], 1),
            "Couverture analytique (30%)": analytical,
            "Cohérence technique (10%)": round(coherence, 1),
        },
        "issues": issues, "issue_count": len(issues),
        "validation_status": status, "validation_errors": error_count,
        "validation_warnings": warning_count,
        "message": "Les analyses non renseignées restent non testées; elles ne sont jamais considérées comme zéro ou conformes.",
        "interpretation": "Score de qualité documentaire et technique du dataset uniquement; ce n'est ni un score de sécurité sanitaire ni une décision de conformité réglementaire.",
        "limitations": "Les plages contrôlées sont des plages générales de plausibilité, pas des seuils réglementaires. Les limites doivent être définies selon le produit, la méthode, l'unité et la réglementation applicable.",
    }
