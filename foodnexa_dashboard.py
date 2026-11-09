
import json
import math
import re
import pandas as pd
import streamlit as st


# =====================================================
# FOODNEXA DASHBOARD - ENTERPRISE EDITION V2
# =====================================================

def _prepare_df(data):
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.DataFrame):
        return data.copy()
    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def _is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().casefold() in {
            "", "nan", "none", "null", "nat"
        }

    if isinstance(value, (dict, list, tuple)):
        return len(value) == 0

    try:
        result = pd.isna(value)
        if isinstance(result, bool):
            return result
    except (TypeError, ValueError):
        pass

    return False


def _safe_string(value):
    if _is_missing(value):
        return ""

    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str
        )

    return str(value).strip()


def _normalize_name(value):
    value = str(value).strip().casefold()
    return re.sub(r"[^a-z0-9]", "", value)


def _expand_nested_data(df):
    """
    Expand JSONB dictionaries into temporary columns.
    Original dataframe is not modified.
    """

    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()

    expanded = df.copy()

    def flatten_object(obj, prefix=""):
        result = {}

        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{prefix}_{key}" if prefix else str(key)

                if isinstance(value, dict):
                    result.update(flatten_object(value, new_key))
                else:
                    result[new_key] = value

        return result

    nested_columns = {}

    for column in df.columns:
        values = df[column]

        if not values.map(lambda x: isinstance(x, dict)).any():
            continue

        flattened_rows = []

        for value in values:
            if isinstance(value, dict):
                flattened_rows.append(flatten_object(value))
            else:
                flattened_rows.append({})

        nested = pd.DataFrame(flattened_rows, index=df.index)

        for nested_column in nested.columns:
            new_name = f"{column}_{nested_column}"

            if new_name not in expanded.columns:
                nested_columns[new_name] = nested[nested_column]

    for name, values in nested_columns.items():
        expanded[name] = values

    return expanded


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    normalized = {
        _normalize_name(column): column
        for column in df.columns
    }

    for candidate in candidates:
        key = _normalize_name(candidate)

        if key in normalized:
            return normalized[key]

    return None


def _find_matching_columns(df, candidates):
    if df is None or df.empty:
        return []

    normalized = {
        _normalize_name(column): column
        for column in df.columns
    }

    found = []

    for candidate in candidates:
        key = _normalize_name(candidate)

        for normalized_name, original_name in normalized.items():
            if (
                normalized_name == key
                or normalized_name.endswith(key)
            ):
                if original_name not in found:
                    found.append(original_name)

    return found


def _numeric_column(df, candidates):
    column = _find_column(df, candidates)

    if column is None:
        return pd.Series(dtype="float64")

    values = df[column].map(
        lambda value: (
            value if isinstance(value, (int, float))
            and not isinstance(value, bool)
            else value if isinstance(value, str)
            else None
        )
    )

    return pd.to_numeric(
        values,
        errors="coerce"
    ).dropna()


def _count_unique(df, candidates):
    column = _find_column(df, candidates)

    if column is None:
        return 0

    values = df[column].map(_safe_string)
    values = values[values != ""]

    return int(values.nunique())


def _risk_category(value):
    text = _safe_string(value).casefold()

    mapping = {
        "faible": "Faible",
        "low": "Faible",
        "modéré": "Modéré",
        "modere": "Modéré",
        "moderate": "Modéré",
        "medium": "Modéré",
        "élevé": "Élevé",
        "eleve": "Élevé",
        "high": "Élevé",
    }

    return mapping.get(text)


def _make_hashable(value):
    if isinstance(value, dict):
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            default=str
        )

    if isinstance(value, (list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return str(value)


def _count_duplicates_safely(df):
    if df is None or df.empty:
        return 0

    seen = set()
    duplicate_count = 0

    for row in df.itertuples(index=False, name=None):
        try:
            normalized_row = tuple(
                _make_hashable(value)
                for value in row
            )

            if normalized_row in seen:
                duplicate_count += 1
            else:
                seen.add(normalized_row)

        except Exception:
            continue

    return duplicate_count


# =====================================================
# DATA QUALITY ENGINE V2 - FIELD DEFINITIONS
# =====================================================

TRACEABILITY_FIELDS = {
    "Identifiant du lot": [
        "batch_id", "lot_id", "batch"
    ],
    "Nom du produit": [
        "product_name", "product"
    ],
    "Catégorie du produit": [
        "product_category", "category"
    ],
    "Référence de l'échantillon": [
        "sample_reference", "sample_ref"
    ],
    "Fournisseur": [
        "supplier", "supplier_name"
    ],
    "Date de prélèvement": [
        "sampling_date", "sample_date"
    ],
    "Date d'analyse": [
        "analysis_date"
    ],
    "Laboratoire": [
        "laboratory", "lab_name"
    ],
    "Analyste": [
        "analyst", "analyst_name"
    ],
}


ANALYTICAL_DOMAINS = {
    "Physico-chimique": [
        "temperature_celsius",
        "temperature",
        "storage_days",
        "ph",
        "humidity",
        "moisture",
        "dry_matter",
        "ash",
        "protein",
        "fat",
        "titratable_acidity",
        "density",
        "conductivity",
        "viscosity",
        "brix",
        "salt",
        "particle_size",
    ],

    "Microbiologique": [
        "total_viable_count",
        "tvc",
        "enterobacteriaceae_count",
        "enterobacteriaceae",
        "coliform_count",
        "coliform",
        "e_coli",
        "ecoli",
        "yeast_mould",
        "yeast_mold",
        "staphylococcus",
        "staph",
        "bacillus",
        "listeria",
        "salmonella",
        "salmonella_status",
    ],

    "Contaminants": [
        "pesticides",
        "lead",
        "pb",
        "cadmium",
        "cd",
        "mercury",
        "hg",
        "arsenic",
        "as",
        "aflatoxins",
        "mycotoxins",
    ],

    "Processus": [
        "pasteurized",
        "pasteurization",
        "cold_chain_broken",
        "hygiene_controlled",
        "processing_temperature",
        "processing_time",
        "production_date",
        "storage_temperature",
    ],

    "Sensoriel": [
        "sensory",
        "sensory_evaluation",
        "organoleptic",
        "appearance",
        "odor",
        "odour",
        "taste",
        "texture",
        "color",
        "colour",
    ],

    "Emballage": [
        "packaging",
        "packaging_integrity",
        "packaging_condition",
        "package_integrity",
        "packaging_type",
        "labeling",
        "labelling",
    ],
}


NOT_TESTED_VALUES = {
    "not tested",
    "not_tested",
    "non teste",
    "non testé",
    "non realise",
    "non réalisé",
    "not performed",
    "pending",
    "en attente",
    "non analyse",
    "non analysé",
}

NOT_APPLICABLE_VALUES = {
    "not applicable",
    "not_applicable",
    "n/a",
    "na",
    "non applicable",
    "sans objet",
}


def _classify_test_value(value):
    """
    Classify analytical data without interpreting missing
    measurements as compliant or as zero.
    """

    if _is_missing(value):
        return "Non testé"

    text = _safe_string(value).casefold().strip()

    if text in NOT_TESTED_VALUES:
        return "Non testé"

    if text in NOT_APPLICABLE_VALUES:
        return "Non applicable"

    return "Renseigné"


def _get_domain_columns(df, aliases):
    columns = []

    for alias in aliases:
        matches = _find_matching_columns(df, [alias])

        for column in matches:
            if column not in columns:
                columns.append(column)

    return columns


def _domain_quality_report(df):
    results = []

    for domain, aliases in ANALYTICAL_DOMAINS.items():

        columns = _get_domain_columns(df, aliases)

        if not columns:
            results.append({
                "Domaine": domain,
                "Tests disponibles": 0,
                "Renseignés": 0,
                "Non testés": 0,
                "Non applicables": 0,
                "Couverture": None,
                "Statut": "Champs non disponibles",
            })
            continue

        total = 0
        reported = 0
        not_tested = 0
        not_applicable = 0

        for column in columns:
            for value in df[column].tolist():

                total += 1
                status = _classify_test_value(value)

                if status == "Renseigné":
                    reported += 1
                elif status == "Non testé":
                    not_tested += 1
                else:
                    not_applicable += 1

        applicable = reported + not_tested

        coverage = (
            reported / applicable * 100
            if applicable > 0
            else None
        )

        results.append({
            "Domaine": domain,
            "Tests disponibles": total,
            "Renseignés": reported,
            "Non testés": not_tested,
            "Non applicables": not_applicable,
            "Couverture": (
                round(coverage, 1)
                if coverage is not None
                else None
            ),
            "Statut": (
                "Données disponibles"
                if reported > 0
                else "À compléter"
            ),
        })

    return pd.DataFrame(results)


def _traceability_report(df):
    results = []

    if df is None or df.empty:
        return pd.DataFrame(), 0.0

    total_fields = 0
    completed_fields = 0

    for label, aliases in TRACEABILITY_FIELDS.items():

        column = _find_column(df, aliases)

        if column is None:
            completed = 0
            total = len(df)
        else:
            completed = int(
                (~df[column].map(_is_missing)).sum()
            )
            total = len(df)

        total_fields += total
        completed_fields += completed

        completion = (
            completed / total * 100
            if total > 0
            else 0
        )

        results.append({
            "Information de traçabilité": label,
            "Renseignée": completed,
            "Manquante": total - completed,
            "Complétude": round(completion, 1),
        })

    overall = (
        completed_fields / total_fields * 100
        if total_fields > 0
        else 0
    )

    return pd.DataFrame(results), overall


def _technical_validation_report(df):
    issues = []

    if df is None or df.empty:
        return issues

    numeric_rules = {
        "temperature_celsius": {
            "label": "Température",
            "min": -100,
            "max": 150,
        },
        "storage_days": {
            "label": "Durée de stockage",
            "min": 0,
            "max": 10000,
        },
        "ph": {
            "label": "pH",
            "min": 0,
            "max": 14,
        },
        "humidity": {
            "label": "Humidité",
            "min": 0,
            "max": 100,
        },
        "moisture": {
            "label": "Teneur en eau",
            "min": 0,
            "max": 100,
        },
    }

    for field, rule in numeric_rules.items():

        column = _find_column(df, [field])

        if column is None:
            continue

        original = df[column]

        present = ~original.map(_is_missing)

        converted = pd.to_numeric(
            original,
            errors="coerce"
        )

        invalid_format = present & converted.isna()

        if invalid_format.any():
            issues.append({
                "Anomalie": (
                    f"Format numérique invalide : {rule['label']}"
                ),
                "Priorité": "Contrôle technique",
                "Nombre": int(invalid_format.sum()),
            })

        outside = (
            converted.notna()
            & (
                (converted < rule["min"])
                | (converted > rule["max"])
            )
        )

        if outside.any():
            issues.append({
                "Anomalie": (
                    f"Valeur hors plage de plausibilité : {rule['label']}"
                ),
                "Priorité": "À examiner",
                "Nombre": int(outside.sum()),
            })

    date_fields = [
        "sampling_date",
        "analysis_date",
        "production_date",
    ]

    for field in date_fields:

        column = _find_column(df, [field])

        if column is None:
            continue

        original = df[column]
        present = ~original.map(_is_missing)

        converted = pd.to_datetime(
            original,
            errors="coerce",
            utc=True
        )

        invalid = present & converted.isna()

        if invalid.any():
            issues.append({
                "Anomalie": f"Date invalide : {field}",
                "Priorité": "Contrôle technique",
                "Nombre": int(invalid.sum()),
            })

    sampling_column = _find_column(
        df,
        ["sampling_date", "sample_date"]
    )

    analysis_column = _find_column(
        df,
        ["analysis_date"]
    )

    if sampling_column and analysis_column:

        sampling = pd.to_datetime(
            df[sampling_column],
            errors="coerce",
            utc=True
        )

        analysis = pd.to_datetime(
            df[analysis_column],
            errors="coerce",
            utc=True
        )

        reversed_dates = (
            sampling.notna()
            & analysis.notna()
            & (analysis < sampling)
        )

        if reversed_dates.any():
            issues.append({
                "Anomalie": "Date d'analyse antérieure au prélèvement",
                "Priorité": "À examiner",
                "Nombre": int(reversed_dates.sum()),
            })

    return issues


def _quality_issues(df):
    issues = []

    if df is None or df.empty:
        return issues

    identity_fields = [
        ("batch_id", "Identifiant du lot"),
        ("product_name", "Nom du produit"),
    ]

    for field, label in identity_fields:

        column = _find_column(df, [field])

        if column is None:
            issues.append({
                "Anomalie": f"Colonne absente : {label}",
                "Priorité": "À vérifier",
                "Nombre": len(df),
            })
            continue

        missing_count = int(
            df[column].map(_is_missing).sum()
        )

        if missing_count:
            issues.append({
                "Anomalie": f"{label} manquant",
                "Priorité": "À vérifier",
                "Nombre": missing_count,
            })

    duplicate_count = _count_duplicates_safely(df)

    if duplicate_count:
        issues.append({
            "Anomalie": "Doublons exacts détectés",
            "Priorité": "À examiner",
            "Nombre": duplicate_count,
        })

    issues.extend(_technical_validation_report(df))

    return issues


# =====================================================
# RECENT ACTIVITY
# =====================================================

def _recent_activity(history, research):

    records = []

    if history is not None and not history.empty:

        for _, row in history.tail(10).iterrows():

            records.append({
                "Date": _safe_string(
                    row.get("analysis_date", "")
                ),
                "Type": "Évaluation du risque",
                "Lot": _safe_string(
                    row.get("batch_id", "")
                ),
                "Produit": _safe_string(
                    row.get("product_name", "")
                ),
                "Résultat": (
                    _safe_string(row.get("risk_level", ""))
                    + " — "
                    + _safe_string(row.get("risk_score", ""))
                ),
            })

    if research is not None and not research.empty:

        for _, row in research.tail(10).iterrows():

            records.append({
                "Date": _safe_string(
                    row.get(
                        "analysis_date",
                        row.get("created_at", "")
                    )
                ),
                "Type": "Observation de recherche",
                "Lot": _safe_string(
                    row.get("batch_id", "")
                ),
                "Produit": _safe_string(
                    row.get("product_name", "")
                ),
                "Résultat": "Observation enregistrée",
            })

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(records)

    result["_sort_date"] = pd.to_datetime(
        result["Date"],
        errors="coerce",
        utc=True
    )

    result = result.sort_values(
        "_sort_date",
        ascending=False,
        na_position="last"
    )

    result = result.drop(columns=["_sort_date"])

    return result.head(10).reset_index(drop=True)


# =====================================================
# RISK SCORE EVOLUTION
# =====================================================

def _render_risk_evolution(history, risk_score_column):

    if history.empty or risk_score_column is None:
        st.info(
            "Les données d'évolution ne sont pas encore disponibles."
        )
        return

    batch_column = _find_column(
        history,
        ["batch_id"]
    )

    if batch_column is None:
        st.info(
            "Identifiants des lots indisponibles."
        )
        return

    batch_values = history[batch_column].map(_safe_string)

    risk_values = pd.to_numeric(
        history[risk_score_column],
        errors="coerce"
    )

    chart_data = pd.DataFrame({
        "Lot": batch_values,
        "Risk Score": risk_values,
    })

    chart_data = chart_data[
        (chart_data["Lot"] != "")
        & chart_data["Risk Score"].notna()
    ]

    if chart_data.empty:
        st.info(
            "Aucun Risk Score numérique disponible."
        )
        return

    chart_data = chart_data.tail(30).reset_index(drop=True)

    chart_data["Lot affiché"] = [
        f"{lot} ({index + 1})"
        for index, lot in enumerate(chart_data["Lot"])
    ]

    chart_data = chart_data.set_index("Lot affiché")

    st.line_chart(
        chart_data[["Risk Score"]]
    )


# =====================================================
# QUALITY REPORT DISPLAY
# =====================================================

def _extract_quality_score(quality_report):

    if not isinstance(quality_report, dict):
        return None

    possible_keys = [
        "quality_score",
        "overall_score",
        "score",
        "quality_percentage",
    ]

    for key in possible_keys:

        value = quality_report.get(key)

        try:
            score = float(value)

            if math.isfinite(score):
                return score

        except (TypeError, ValueError):
            continue

    return None


def _extract_engine_issues(quality_report):

    if not isinstance(quality_report, dict):
        return []

    possible_keys = [
        "issues",
        "errors",
        "warnings",
        "alerts",
    ]

    results = []

    for key in possible_keys:

        values = quality_report.get(key)

        if not isinstance(values, list):
            continue

        for issue in values[:30]:

            if isinstance(issue, dict):

                results.append({
                    "Anomalie": _safe_string(
                        issue.get(
                            "issue",
                            issue.get(
                                "message",
                                issue.get(
                                    "type",
                                    issue.get(
                                        "description",
                                        "Anomalie détectée"
                                    )
                                )
                            )
                        )
                    ),
                    "Priorité": _safe_string(
                        issue.get(
                            "priority",
                            issue.get(
                                "severity",
                                issue.get("level", "À vérifier")
                            )
                        )
                    ),
                    "Nombre": _safe_string(
                        issue.get(
                            "count",
                            issue.get("row", "—")
                        )
                    ),
                })

            else:

                results.append({
                    "Anomalie": _safe_string(issue),
                    "Priorité": "À vérifier",
                    "Nombre": "—",
                })

    return results


# =====================================================
# MAIN DASHBOARD
# =====================================================

def render_dashboard(
    history_data=None,
    research_data=None,
    quality_report=None,
    pipeline_status=None
):

    history = _prepare_df(history_data)
    research_original = _prepare_df(research_data)

    # Temporary expanded view for JSONB/nested research fields.
    research = _expand_nested_data(research_original)

    st.title("FOODNEXA Intelligence Dashboard")

    st.caption(
        "Food Safety • Risk Intelligence • Research Data Monitoring"
    )

    st.markdown(
        "Vue consolidée des évaluations expérimentales, "
        "des observations scientifiques et de la qualité des données."
    )

    st.divider()

    # -------------------------------------------------
    # 1. KPI CALCULATIONS
    # -------------------------------------------------

    total_assessments = len(history)
    total_research = len(research)

    risk_column = _find_column(
        history,
        ["risk_level"]
    )

    risk_score_column = _find_column(
        history,
        ["risk_score"]
    )

    risk_levels = pd.Series(dtype="object")

    if risk_column is not None:
        risk_levels = history[risk_column].map(
            _risk_category
        )

    high_risk = int((risk_levels == "Élevé").sum())
    moderate_risk = int((risk_levels == "Modéré").sum())
    low_risk = int((risk_levels == "Faible").sum())

    risk_scores = _numeric_column(
        history,
        ["risk_score"]
    )

    average_risk = (
        float(risk_scores.mean())
        if not risk_scores.empty
        else None
    )

    quality_score = _extract_quality_score(quality_report)

    # -------------------------------------------------
    # 2. EXECUTIVE OVERVIEW
    # -------------------------------------------------

    st.subheader("Executive Overview")

    k1, k2, k3 = st.columns(3)

    with k1:
        st.metric("Risk Assessments", total_assessments)

    with k2:
        st.metric("Research Observations", total_research)

    with k3:
        st.metric(
            "Dataset Quality Score",
            (
                f"{quality_score:.1f}%"
                if quality_score is not None
                else "N/D"
            ),
            help="Score documentaire calculé par le Data Quality Engine."
        )

    k4, k5, k6 = st.columns(3)

    with k4:
        st.metric("High Risk", high_risk)

    with k5:
        st.metric("Moderate Risk", moderate_risk)

    with k6:
        st.metric(
            "Average Risk Score",
            (
                f"{average_risk:.1f}/100"
                if average_risk is not None
                else "N/D"
            )
        )

    st.divider()

    # -------------------------------------------------
    # 3. RISK INTELLIGENCE
    # -------------------------------------------------

    st.subheader("Risk Intelligence Monitoring")

    risk_left, risk_right = st.columns(2)

    with risk_left:

        st.markdown("**Risk Level Distribution**")

        if total_assessments and risk_column is not None:

            distribution = pd.DataFrame({
                "Risk Level": [
                    "Faible",
                    "Modéré",
                    "Élevé",
                ],
                "Observations": [
                    low_risk,
                    moderate_risk,
                    high_risk,
                ],
            })

            st.bar_chart(
                distribution.set_index("Risk Level"),
                horizontal=True
            )

        else:
            st.info(
                "Aucune évaluation de risque disponible."
            )

    with risk_right:

        st.markdown("**Risk Score Evolution**")

        _render_risk_evolution(
            history,
            risk_score_column
        )

    st.divider()

    # -------------------------------------------------
    # 4. RESEARCH DATA OVERVIEW
    # -------------------------------------------------

    st.subheader("Research Dataset Overview")

    r1, r2, r3 = st.columns(3)

    with r1:
        st.metric("Observations", total_research)

    with r2:
        st.metric(
            "Produits distincts",
            _count_unique(research, ["product_name"])
        )

    with r3:
        st.metric(
            "Lots distincts",
            _count_unique(research, ["batch_id"])
        )

    if not research.empty:

        category_column = _find_column(
            research,
            ["product_category"]
        )

        if category_column is not None:

            categories = (
                research[category_column]
                .map(_safe_string)
                .replace("", pd.NA)
                .dropna()
                .value_counts()
            )

            if not categories.empty:

                st.markdown(
                    "**Observations par catégorie de produit**"
                )

                category_df = categories.rename_axis(
                    "Catégorie"
                ).reset_index(name="Observations")

                st.bar_chart(
                    category_df.set_index("Catégorie"),
                    horizontal=True
                )

    else:
        st.info(
            "Le Research Dataset ne contient pas encore d'observations."
        )

    st.divider()

    # -------------------------------------------------
    # 5. DATA QUALITY MONITORING V2
    # -------------------------------------------------

    st.subheader("Data Quality Monitoring V2")

    if research.empty:

        st.info(
            "En attente de données pour le contrôle qualité."
        )

    else:

        # 5.1 Traceability

        st.markdown("#### 1. Traceability Completeness")

        traceability_df, traceability_score = (
            _traceability_report(research)
        )

        t1, t2, t3 = st.columns(3)

        with t1:
            st.metric(
                "Traceability Score",
                f"{traceability_score:.1f}%"
            )

        with t2:
            traceability_missing = int(
                traceability_df["Manquante"].sum()
            )
            st.metric(
                "Missing Traceability Fields",
                traceability_missing
            )

        with t3:
            st.metric(
                "Tracked Information Fields",
                len(TRACEABILITY_FIELDS)
            )

        st.progress(
            min(max(traceability_score / 100, 0.0), 1.0)
        )

        with st.expander(
            "Afficher le détail de la traçabilité",
            expanded=False
        ):
            st.dataframe(
                traceability_df,
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # 5.2 Analytical coverage

        st.markdown("#### 2. Analytical Coverage by Scientific Domain")

        domain_df = _domain_quality_report(research)

        available_domain_scores = domain_df[
            domain_df["Couverture"].notna()
        ]

        if not available_domain_scores.empty:

            average_coverage = float(
                available_domain_scores["Couverture"].mean()
            )

            st.metric(
                "Average Analytical Coverage",
                f"{average_coverage:.1f}%"
            )

            chart_domain = available_domain_scores[
                ["Domaine", "Couverture"]
            ].set_index("Domaine")

            st.bar_chart(
                chart_domain,
                horizontal=True
            )

        else:

            st.info(
                "Aucun champ analytique reconnu dans les observations."
            )

        st.dataframe(
            domain_df,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "La couverture représente les résultats renseignés parmi "
            "les tests applicables. Elle ne représente pas un taux de conformité."
        )

        st.divider()

        # 5.3 Test status

        st.markdown("#### 3. Analytical Test Status")

        status_counts = {
            "Renseigné": 0,
            "Non testé": 0,
            "Non applicable": 0,
        }

        all_domain_columns = []

        for aliases in ANALYTICAL_DOMAINS.values():
            for column in _get_domain_columns(research, aliases):
                if column not in all_domain_columns:
                    all_domain_columns.append(column)

        for column in all_domain_columns:

            for value in research[column].tolist():

                status = _classify_test_value(value)
                status_counts[status] += 1

        s1, s2, s3 = st.columns(3)

        with s1:
            st.metric(
                "Renseignés",
                status_counts["Renseigné"]
            )

        with s2:
            st.metric(
                "Non testés",
                status_counts["Non testé"]
            )

        with s3:
            st.metric(
                "Non applicables",
                status_counts["Non applicable"]
            )

        status_df = pd.DataFrame({
            "Statut": list(status_counts.keys()),
            "Nombre": list(status_counts.values()),
        })

        if status_df["Nombre"].sum() > 0:
            st.bar_chart(
                status_df.set_index("Statut"),
                horizontal=True
            )

        st.caption(
            "Une valeur vide est classée comme non testée dans les "
            "champs analytiques. Les informations de traçabilité "
            "vides restent classées comme manquantes."
        )

        st.divider()

        # 5.4 Technical validation

        st.markdown("#### 4. Technical Validation")

        technical_issues = _technical_validation_report(research)

        if technical_issues:

            st.warning(
                f"{len(technical_issues)} type(s) d'anomalie technique "
                "à examiner."
            )

            st.dataframe(
                pd.DataFrame(technical_issues),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "Aucune anomalie technique détectée par les règles "
                "de plausibilité disponibles."
            )

        st.divider()

        # 5.5 Global issue register

        st.markdown("#### 5. Data Quality Issue Register")

        issues = _quality_issues(research)
        issues.extend(_extract_engine_issues(quality_report))

        if issues:

            issue_df = pd.DataFrame(issues)

            issue_df = issue_df.drop_duplicates(
                subset=["Anomalie", "Priorité", "Nombre"]
            )

            st.warning(
                f"{len(issue_df)} signalement(s) à examiner."
            )

            st.dataframe(
                issue_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "Aucune anomalie détectée par les contrôles disponibles."
            )

    st.caption(
        "Les indicateurs de qualité sont des outils de surveillance "
        "documentaire et technique. Ils ne constituent pas une décision "
        "de conformité réglementaire ou de sécurité sanitaire."
    )

    st.divider()

    # -------------------------------------------------
    # 6. RECENT ACTIVITY
    # -------------------------------------------------

    st.subheader("Recent Activity")

    activity = _recent_activity(
        history,
        research_original
    )

    if activity.empty:

        st.info(
            "Aucune activité enregistrée pour le moment."
        )

    else:

        st.dataframe(
            activity,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    # -------------------------------------------------
    # 7. SYSTEM PIPELINE STATUS
    # -------------------------------------------------

    st.subheader("FOODNEXA System Pipeline")

    default_pipeline = {
        "Risk Assessment Engine": True,
        "Research Dataset": not research.empty,
        "Data Quality Engine": quality_report is not None,
        "Scientific Data Cleaning": None,
        "Research Analytics": not research.empty,
        "Supabase": None,
    }

    if isinstance(pipeline_status, dict):
        default_pipeline.update(pipeline_status)

    pipeline_items = list(default_pipeline.items())

    for start in range(0, len(pipeline_items), 3):

        group = pipeline_items[start:start + 3]
        columns = st.columns(3)

        for column, (name, status) in zip(columns, group):

            with column:

                if status is True:

                    st.success(
                        f"**{name}**\n\nDisponible / données présentes"
                    )

                elif status is False:

                    st.warning(
                        f"**{name}**\n\nNon disponible / données absentes"
                    )

                else:

                    st.info(
                        f"**{name}**\n\nStatut non confirmé"
                    )

    st.divider()

    # -------------------------------------------------
    # 8. SCIENTIFIC DISCLAIMER
    # -------------------------------------------------

    st.caption(
        "FOODNEXA is an experimental Food Safety Risk Intelligence "
        "prototype. Dashboard indicators support research and "
        "exploratory monitoring. They do not replace laboratory "
        "analysis, validated predictive models, expert assessment "
        "or applicable regulatory requirements."
    )
