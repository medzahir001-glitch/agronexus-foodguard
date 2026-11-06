import numpy as np
import pandas as pd

RISK_ORDER = {"Faible": 0, "Modéré": 1, "Élevé": 2}

# Optional measurements supported by FOODNEXA Research Data.
# Results are analysed only when present; units and product-specific limits
# must be checked before comparing observations.
ANALYSIS_GROUPS = {
    "physicochemical": [
        "temperature_celsius", "storage_days", "ph",
        "humidity_percent", "moisture_percent", "dry_matter_percent",
        "ash_percent", "protein_percent", "fat_percent",
        "titratable_acidity", "density", "conductivity",
        "viscosity", "brix", "salt_percent", "particle_size"
    ],
    "microbiological": [
        "total_viable_count", "enterobacteriaceae_count",
        "coliform_count", "e_coli_count", "yeast_mould_count",
        "staphylococcus_aureus_count", "bacillus_cereus_count",
        "listeria_monocytogenes_count"
    ],
    "contaminants": [
        "pesticide_residue", "lead", "cadmium", "mercury",
        "arsenic", "aflatoxin", "mycotoxin"
    ],
    "process": [
        "processing_temperature_celsius", "processing_time_minutes",
        "cooling_temperature_celsius", "cooling_time_minutes"
    ],
    "packaging": [
        "net_weight", "seal_integrity_score", "vacuum_level"
    ],
}

IDENTIFIER_COLUMNS = [
    "batch_id", "product_name", "product_category", "company_name",
    "sampling_date", "analysis_date", "laboratory", "method_reference"
]

def _as_numeric(data, columns):
    for column in columns:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data

def prepare_research_data(df):
    """Return a safe analytics copy; never modify the caller's DataFrame."""
    if df is None:
        return pd.DataFrame()
    data = df.copy()
    numeric_columns = sorted({c for group in ANALYSIS_GROUPS.values() for c in group})
    data = _as_numeric(data, numeric_columns)
    if "expert_risk_label" in data.columns:
        data["risk_numeric"] = (
            data["expert_risk_label"].astype("string").str.strip().map(RISK_ORDER)
        )
    return data

def _present_numeric_columns(data, columns=None):
    candidates = columns or sorted({c for group in ANALYSIS_GROUPS.values() for c in group})
    return [
        c for c in candidates
        if c in data.columns and pd.to_numeric(data[c], errors="coerce").notna().any()
    ]

def calculate_basic_statistics(df):
    data = prepare_research_data(df)
    if data.empty:
        return {}
    stats = {"observations": int(len(data))}
    for column in _present_numeric_columns(data):
        values = pd.to_numeric(data[column], errors="coerce").dropna()
        if values.empty:
            continue
        stats[f"{column}_count"] = int(values.count())
        stats[f"{column}_mean"] = round(float(values.mean()), 4)
        stats[f"{column}_median"] = round(float(values.median()), 4)
        stats[f"{column}_min"] = round(float(values.min()), 4)
        stats[f"{column}_max"] = round(float(values.max()), 4)
        stats[f"{column}_missing"] = int(data[column].isna().sum())
    return stats

def calculate_risk_distribution(df):
    data = prepare_research_data(df)
    columns = ["Risk Level", "Nombre"]
    if "expert_risk_label" not in data.columns:
        return pd.DataFrame(columns=columns)
    labels = data["expert_risk_label"].astype("string").str.strip()
    result = labels.value_counts().reindex(["Faible", "Modéré", "Élevé"], fill_value=0)
    return result.rename_axis("Risk Level").reset_index(name="Nombre")

def calculate_risk_percentages(df):
    distribution = calculate_risk_distribution(df)
    total = int(distribution["Nombre"].sum()) if not distribution.empty else 0
    distribution["Pourcentage"] = (
        (distribution["Nombre"] / total * 100).round(1) if total else 0.0
    )
    return distribution

def calculate_factor_means_by_risk(df):
    data = prepare_research_data(df)
    if "expert_risk_label" not in data.columns:
        return pd.DataFrame()
    factors = _present_numeric_columns(data)
    if not factors:
        return pd.DataFrame()
    return (
        data.groupby("expert_risk_label", dropna=True)[factors]
        .mean()
        .reindex(["Faible", "Modéré", "Élevé"])
        .round(4)
    )

def calculate_correlations(df):
    """Exploratory Pearson correlations; not causal evidence or validation."""
    data = prepare_research_data(df)
    if "risk_numeric" not in data.columns:
        return pd.DataFrame(columns=["Variable", "Corrélation avec le risque", "N"])
    rows = []
    for column in _present_numeric_columns(data):
        pair = data[[column, "risk_numeric"]].dropna()
        if len(pair) < 3 or pair[column].nunique() < 2 or pair["risk_numeric"].nunique() < 2:
            continue
        corr = pair[column].corr(pair["risk_numeric"])
        rows.append({
            "Variable": column,
            "Corrélation avec le risque": round(float(corr), 3) if pd.notna(corr) else np.nan,
            "N": int(len(pair))
        })
    result = pd.DataFrame(rows)
    if not result.empty:
        result["_abs"] = result["Corrélation avec le risque"].abs()
        result = result.sort_values("_abs", ascending=False).drop(columns="_abs")
    return result

def _normalise_text(series):
    return series.astype("string").str.strip().str.casefold()

def _positive_rate(df, column, positive_values):
    data = prepare_research_data(df)
    if column not in data.columns:
        return np.nan
    values = _normalise_text(data[column])
    valid = values.notna() & ~values.isin(["", "non analysé", "non analysée", "non évalué", "non évaluée", "na", "n/a", "none"])
    denominator = int(valid.sum())
    if denominator == 0:
        return np.nan
    positives = values[valid].isin({v.casefold() for v in positive_values}).sum()
    return round(float(positives) / denominator * 100, 1)

def calculate_salmonella_rate(df):
    return _positive_rate(df, "salmonella_detected", {"détectée", "detectee", "oui", "positive", "detected", "true"})

def calculate_nonconformity_rate(df):
    return _positive_rate(df, "nonconformity_detected", {"oui", "yes", "non conforme", "non-conforme", "true"})

def calculate_missingness(df):
    """Missingness is reported per field; missing is not interpreted as a pass."""
    data = prepare_research_data(df)
    if data.empty:
        return pd.DataFrame(columns=["Variable", "Valeurs disponibles", "Valeurs manquantes", "Manquantes (%)"])
    columns = [c for c in data.columns if c not in {"risk_numeric"}]
    rows = []
    for column in columns:
        missing = int(data[column].isna().sum())
        rows.append({
            "Variable": column,
            "Valeurs disponibles": int(data[column].notna().sum()),
            "Valeurs manquantes": missing,
            "Manquantes (%)": round(missing / len(data) * 100, 1)
        })
    return pd.DataFrame(rows).sort_values("Manquantes (%)", ascending=False)

def calculate_group_statistics(df):
    """Descriptive summaries by domain, limited to numeric fields actually supplied."""
    data = prepare_research_data(df)
    output = {}
    for group, columns in ANALYSIS_GROUPS.items():
        available = _present_numeric_columns(data, columns)
        if available:
            output[group] = data[available].describe().T[
                ["count", "mean", "50%", "min", "max"]
            ].rename(columns={"50%": "median"}).round(4)
    return output

def calculate_category_summary(df, category_column="product_category"):
    """Summarise counts by product category; does not compare unlike measurements."""
    data = prepare_research_data(df)
    if category_column not in data.columns:
        return pd.DataFrame(columns=["Catégorie", "Observations"])
    return (
        data[category_column].fillna("Non renseignée").astype(str)
        .value_counts().rename_axis("Catégorie").reset_index(name="Observations")
    )

def generate_research_analytics(df):
    data = prepare_research_data(df)
    if data.empty:
        return {"status": "EMPTY", "message": "Aucune observation disponible."}
    return {
        "status": "SUCCESS",
        "observations": int(len(data)),
        "statistics": calculate_basic_statistics(data),
        "risk_distribution": calculate_risk_distribution(data),
        "risk_percentages": calculate_risk_percentages(data),
        "factor_means_by_risk": calculate_factor_means_by_risk(data),
        "correlations": calculate_correlations(data),
        "salmonella_rate": calculate_salmonella_rate(data),
        "nonconformity_rate": calculate_nonconformity_rate(data),
        "missingness": calculate_missingness(data),
        "group_statistics": calculate_group_statistics(data),
        "category_summary": calculate_category_summary(data),
        "analysis_note": (
            "Analyse descriptive et exploratoire uniquement. Les comparaisons "
            "nécessitent des unités, méthodes et critères adaptés au produit. "
            "Une valeur absente ou non analysée n'est pas un résultat négatif."
        )
    }
