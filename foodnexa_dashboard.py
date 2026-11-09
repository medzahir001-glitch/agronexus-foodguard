
import json
import math
import pandas as pd
import streamlit as st


# =====================================================
# FOODNEXA DASHBOARD - ENTERPRISE EDITION
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
            "", "nan", "none", "null"
        }

    if isinstance(value, (dict, list, tuple)):
        return len(value) == 0

    try:
        result = pd.isna(value)
        if isinstance(result, (bool, type(pd.NA))):
            return bool(result)
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


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    normalized = {
        str(column).strip().casefold(): column
        for column in df.columns
    }

    for candidate in candidates:
        found = normalized.get(candidate.casefold())
        if found is not None:
            return found

    return None


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


def _kpi_card(label, value, help_text=None):
    st.metric(
        label=label,
        value=value,
        help=help_text
    )


# =====================================================
# SAFE VALUE NORMALIZATION
# =====================================================

def _make_hashable(value):
    """Convert nested values into stable representations."""

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

    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return str(value)


# =====================================================
# SAFE DUPLICATE DETECTION
# =====================================================

def _count_duplicates_safely(df):
    """
    Count exact duplicate rows without using pandas duplicated().
    Supports dictionaries, lists and JSONB values.
    """

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
# DATA QUALITY MONITORING
# =====================================================

def _quality_issues(df):
    issues = []

    if df is None or df.empty:
        return issues

    identity_fields = [
        ("batch_id", "Identifiant du lot"),
        ("product_name", "Nom du produit"),
    ]

    for field, label in identity_fields:

        if field not in df.columns:
            issues.append({
                "Issue": f"Colonne absente : {label}",
                "Priority": "À vérifier",
                "Count": len(df),
            })
            continue

        missing_count = int(
            df[field].map(_is_missing).sum()
        )

        if missing_count:
            issues.append({
                "Issue": f"{label} manquant",
                "Priority": "À vérifier",
                "Count": missing_count,
            })

    duplicate_count = _count_duplicates_safely(df)

    if duplicate_count:
        issues.append({
            "Issue": "Doublons exacts détectés",
            "Priority": "À vérifier",
            "Count": duplicate_count,
        })

    numeric_fields = [
        "temperature_celsius",
        "storage_days",
        "ph",
        "total_viable_count",
        "enterobacteriaceae_count",
        "coliform_count",
    ]

    for field in numeric_fields:

        if field not in df.columns:
            continue

        original = df[field]

        present = ~original.map(_is_missing)

        converted = pd.to_numeric(
            original,
            errors="coerce"
        )

        invalid = present & converted.isna()

        invalid_count = int(invalid.sum())

        if invalid_count:
            issues.append({
                "Issue": f"Valeurs numériques invalides : {field}",
                "Priority": "Contrôle technique",
                "Count": invalid_count,
            })

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
# RISK SCORE EVOLUTION - SAFE VERSION
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

    # Read columns separately to avoid pandas selection
    # problems when source data contains nested JSON values.
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

    chart_data = chart_data.tail(30)

    # Make labels unique for chart display.
    chart_data = chart_data.reset_index(drop=True)

    chart_data["Lot affiché"] = [
        f"{lot} ({index + 1})"
        for index, lot in enumerate(chart_data["Lot"])
    ]

    chart_data = chart_data.set_index("Lot affiché")

    st.line_chart(
        chart_data[["Risk Score"]]
    )


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
    research = _prepare_df(research_data)

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

    quality_score = None

    if isinstance(quality_report, dict):

        try:
            raw_quality_score = quality_report.get(
                "quality_score"
            )

            if raw_quality_score is not None:
                quality_score = float(raw_quality_score)

            if (
                quality_score is not None
                and not math.isfinite(quality_score)
            ):
                quality_score = None

        except (TypeError, ValueError):
            quality_score = None

    # -------------------------------------------------
    # 2. KPI CARDS
    # -------------------------------------------------

    st.subheader("Executive Overview")

    k1, k2, k3 = st.columns(3)

    with k1:
        _kpi_card(
            "Risk Assessments",
            total_assessments
        )

    with k2:
        _kpi_card(
            "Research Observations",
            total_research
        )

    with k3:
        _kpi_card(
            "Dataset Quality Score",
            (
                f"{quality_score:.1f}%"
                if quality_score is not None
                else "N/D"
            ),
            "Score documentaire calculé par le Data Quality Engine."
        )

    k4, k5, k6 = st.columns(3)

    with k4:
        _kpi_card(
            "High Risk",
            high_risk
        )

    with k5:
        _kpi_card(
            "Moderate Risk",
            moderate_risk
        )

    with k6:
        _kpi_card(
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
        st.metric(
            "Observations",
            total_research
        )

    with r2:
        st.metric(
            "Produits distincts",
            _count_unique(
                research,
                ["product_name"]
            )
        )

    with r3:
        st.metric(
            "Lots distincts",
            _count_unique(
                research,
                ["batch_id"]
            )
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
    # 5. DATA QUALITY MONITORING
    # -------------------------------------------------

    st.subheader("Data Quality Monitoring")

    issues = _quality_issues(research)

    if isinstance(quality_report, dict):

        report_issues = quality_report.get(
            "issues",
            []
        )

        if isinstance(report_issues, list):

            for issue in report_issues[:20]:

                if isinstance(issue, dict):

                    issues.append({
                        "Issue": _safe_string(
                            issue.get(
                                "issue",
                                issue.get(
                                    "message",
                                    issue.get(
                                        "type",
                                        "Anomalie détectée"
                                    )
                                )
                            )
                        ),
                        "Priority": _safe_string(
                            issue.get(
                                "priority",
                                issue.get(
                                    "severity",
                                    "À vérifier"
                                )
                            )
                        ),
                        "Count": _safe_string(
                            issue.get(
                                "count",
                                issue.get("row", "—")
                            )
                        ),
                    })

                else:

                    issues.append({
                        "Issue": _safe_string(issue),
                        "Priority": "À vérifier",
                        "Count": "—",
                    })

    if issues:

        issue_df = pd.DataFrame(issues)

        issue_df = issue_df.drop_duplicates(
            subset=["Issue", "Priority", "Count"]
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

        if research.empty:
            st.info(
                "En attente de données pour le contrôle qualité."
            )
        else:
            st.success(
                "Aucune anomalie détectée par les contrôles "
                "de base du Dashboard."
            )

    st.caption(
        "Les alertes sont des signaux de contrôle documentaire "
        "et technique. Elles ne constituent pas une décision "
        "de conformité réglementaire."
    )

    st.divider()

    # -------------------------------------------------
    # 6. RECENT ACTIVITY
    # -------------------------------------------------

    st.subheader("Recent Activity")

    activity = _recent_activity(
        history,
        research
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
