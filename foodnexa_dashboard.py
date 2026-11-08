
"""
FOODNEXA - Enterprise Dashboard V1
Food Safety / Risk Intelligence

Independent dashboard module.
Original CSV and Supabase data are read only.
"""

import streamlit as st
import pandas as pd
import numpy as np


# =========================================================
# CONFIGURATION
# =========================================================

NAVY = "#102B46"
BLUE = "#087E9B"
GREEN = "#16A078"
ORANGE = "#E69A32"
RED = "#D9534F"
GREY = "#718096"


# =========================================================
# DATA HELPERS
# =========================================================

def _prepare_df(data):
    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, list):
        return pd.DataFrame(data)

    if isinstance(data, dict):
        return pd.DataFrame(data)

    return pd.DataFrame()


def _find_column(df, candidates):
    if df.empty:
        return None

    normalized = {
        str(col).strip().lower().replace(" ", "_"): col
        for col in df.columns
    }

    for candidate in candidates:
        key = candidate.lower().replace(" ", "_")
        if key in normalized:
            return normalized[key]

    return None


def _numeric_column(df, candidates):
    col = _find_column(df, candidates)

    if col is None:
        return pd.Series(dtype=float)

    return pd.to_numeric(df[col], errors="coerce")


def _count_unique(df, candidates):
    col = _find_column(df, candidates)

    if col is None or df.empty:
        return 0

    return int(df[col].nunique())


def _format_number(value):
    try:
        return f"{int(value):,}".replace(",", " ")
    except Exception:
        return "0"


def _risk_category(value):
    if pd.isna(value):
        return "Non classé"

    if isinstance(value, str):
        text = value.strip().lower()

        if any(word in text for word in ["élev", "high", "critique", "critical"]):
            return "Élevé"

        if any(word in text for word in ["modér", "medium", "moderate", "moyen"]):
            return "Modéré"

        if any(word in text for word in ["faible", "low", "bas"]):
            return "Faible"

        return "Non classé"

    try:
        score = float(value)

        if score >= 70:
            return "Élevé"
        elif score >= 35:
            return "Modéré"
        else:
            return "Faible"

    except Exception:
        return "Non classé"


# =========================================================
# KPI COMPONENT
# =========================================================

def _kpi_card(label, value, subtitle, color=BLUE):
    st.markdown(
        f"""
        <div style="
            background:#FFFFFF;
            border:1px solid #E4EAF0;
            border-left:4px solid {color};
            border-radius:10px;
            padding:17px 19px;
            min-height:112px;
            box-shadow:0 2px 8px rgba(16,43,70,0.04);
        ">
            <div style="
                color:#64748B;
                font-size:12px;
                font-weight:600;
                margin-bottom:9px;
            ">{label}</div>

            <div style="
                color:{NAVY};
                font-size:27px;
                font-weight:750;
                line-height:1.2;
            ">{value}</div>

            <div style="
                color:#94A3B8;
                font-size:11px;
                margin-top:7px;
            ">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# DATA QUALITY ANALYSIS
# =========================================================

def _quality_issues(df):
    issues = []

    if df.empty:
        return issues

    total = len(df)

    identity_candidates = [
        "batch_id", "sample_reference", "sample_ref",
        "product_name", "product_category"
    ]

    for candidate in identity_candidates:
        col = _find_column(df, [candidate])

        if col is not None:
            missing = int(
                df[col].isna().sum()
                + df[col].astype(str).str.strip().eq("").sum()
            )

            if missing:
                issues.append({
                    "Issue": f"Valeurs manquantes : {col}",
                    "Occurrences": min(missing, total),
                    "Priority": "À vérifier"
                })

    duplicate_count = int(df.duplicated().sum())

    if duplicate_count:
        issues.append({
            "Issue": "Doublons exacts",
            "Occurrences": duplicate_count,
            "Priority": "À vérifier"
        })

    numeric_candidates = [
        "temperature_celsius",
        "temperature",
        "storage_days",
        "ph",
        "tvc",
        "total_viable_count"
    ]

    for candidate in numeric_candidates:
        col = _find_column(df, [candidate])

        if col is not None:
            values = pd.to_numeric(df[col], errors="coerce")
            invalid = int((df[col].notna() & values.isna()).sum())

            if invalid:
                issues.append({
                    "Issue": f"Valeurs non numériques : {col}",
                    "Occurrences": invalid,
                    "Priority": "Technique"
                })

    return issues


# =========================================================
# RECENT ACTIVITY
# =========================================================

def _recent_activity(history, research):
    frames = []

    for df, activity_type in [
        (history, "Analyse de risque"),
        (research, "Observation recherche")
    ]:
        if df.empty:
            continue

        temp = df.copy()

        date_col = _find_column(
            temp,
            ["created_at", "timestamp", "date", "analysis_date", "sampling_date"]
        )

        batch_col = _find_column(
            temp,
            ["batch_id", "sample_reference", "sample_ref"]
        )

        product_col = _find_column(
            temp,
            ["product_name", "product"]
        )

        temp["_activity_type"] = activity_type
        temp["_activity_date"] = (
            pd.to_datetime(temp[date_col], errors="coerce", utc=True)
            if date_col else pd.NaT
        )

        temp["_batch"] = (
            temp[batch_col].astype(str)
            if batch_col else "Non renseigné"
        )

        temp["_product"] = (
            temp[product_col].astype(str)
            if product_col else "Non renseigné"
        )

        frames.append(
            temp[["_activity_date", "_activity_type", "_batch", "_product"]]
        )

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)

    result = result.sort_values(
        "_activity_date",
        ascending=False,
        na_position="last"
    )

    result = result.head(8)

    result.columns = [
        "Date",
        "Type d'activité",
        "Lot / Échantillon",
        "Produit"
    ]

    return result


# =========================================================
# MAIN DASHBOARD
# =========================================================

def render_dashboard(
    history_data=None,
    research_data=None,
    quality_report=None,
    pipeline_status=None
):

    history = _prepare_df(history_data)
    research = _prepare_df(research_data)

    pipeline_status = pipeline_status or {}

    st.markdown(
        f"""
        <div style="margin-bottom:22px;">
            <div style="
                color:{NAVY};
                font-size:27px;
                font-weight:800;
                letter-spacing:-0.5px;
            ">FOODNEXA | Enterprise Dashboard</div>

            <div style="
                color:#718096;
                font-size:13px;
                margin-top:5px;
            ">
                Food Safety • Risk Intelligence • Research Data Analytics
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # DATA COUNTS
    # -----------------------------------------------------

    history_count = len(history)
    research_count = len(research)

    risk_col = _find_column(
        history,
        ["risk_score", "final_risk_score", "risk", "score"]
    )

    risk_label_col = _find_column(
        history,
        ["risk_level", "risk_category", "risk_label", "risk_status"]
    )

    risk_values = (
        pd.to_numeric(history[risk_col], errors="coerce")
        if risk_col else pd.Series(dtype=float)
    )

    if risk_label_col:
        risk_labels = history[risk_label_col].apply(_risk_category)
    elif risk_col:
        risk_labels = risk_values.apply(_risk_category)
    else:
        risk_labels = pd.Series(dtype=str)

    high_risk = int((risk_labels == "Élevé").sum())
    moderate_risk = int((risk_labels == "Modéré").sum())
    low_risk = int((risk_labels == "Faible").sum())

    average_risk = (
        float(risk_values.mean())
        if not risk_values.dropna().empty else None
    )

    # -----------------------------------------------------
    # EXECUTIVE KPIs
    # -----------------------------------------------------

    st.markdown("### Executive Overview")

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        _kpi_card(
            "Risk Assessments",
            _format_number(history_count),
            "Analyses enregistrées",
            BLUE
        )

    with k2:
        _kpi_card(
            "Research Observations",
            _format_number(research_count),
            "Données de recherche",
            GREEN
        )

    with k3:
        _kpi_card(
            "High Risk",
            _format_number(high_risk),
            "Analyses classées élevées",
            RED
        )

    with k4:
        _kpi_card(
            "Moderate Risk",
            _format_number(moderate_risk),
            "Analyses classées modérées",
            ORANGE
        )

    with k5:
        risk_display = (
            f"{average_risk:.1f}/100"
            if average_risk is not None else "N/D"
        )

        _kpi_card(
            "Average Risk Score",
            risk_display,
            "Sur les scores disponibles",
            NAVY
        )

    st.markdown("---")

    # -----------------------------------------------------
    # RISK INTELLIGENCE
    # -----------------------------------------------------

    st.markdown("### Risk Intelligence")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("**Distribution des niveaux de risque**")

        if len(risk_labels):
            distribution = (
                risk_labels.value_counts()
                .reindex(["Faible", "Modéré", "Élevé", "Non classé"])
                .fillna(0)
                .astype(int)
            )

            distribution = distribution[distribution > 0]

            st.bar_chart(distribution, height=260)

        else:
            st.info(
                "Aucune classification de risque disponible "
                "dans les données chargées."
            )

    with right:
        st.markdown("**Évolution des scores de risque**")

        if risk_col and not history.empty:
            date_col = _find_column(
                history,
                ["created_at", "timestamp", "date", "analysis_date"]
            )

            batch_col = _find_column(
                history,
                ["batch_id"]
            )

            trend = pd.DataFrame({
                "Score": risk_values
            })

            if date_col:
                trend["Date"] = pd.to_datetime(
                    history[date_col], errors="coerce"
                )
                trend = trend.dropna(subset=["Date"])
                trend = trend.sort_values("Date")
                trend = trend.set_index("Date")
                st.line_chart(trend[["Score"]], height=260)

            elif batch_col:
                trend["Lot"] = history[batch_col].astype(str).values
                trend = trend.dropna(subset=["Score"])
                trend = trend.set_index("Lot")
                st.line_chart(trend[["Score"]], height=260)

            else:
                st.info("Aucune date ou référence de lot disponible.")

        else:
            st.info("Aucun score numérique disponible.")

    st.markdown("---")

    # -----------------------------------------------------
    # RESEARCH DATA OVERVIEW
    # -----------------------------------------------------

    st.markdown("### Research Dataset Overview")

    r1, r2, r3 = st.columns(3)

    with r1:
        product_count = _count_unique(
            research,
            ["product_name", "product"]
        )
        _kpi_card(
            "Produits étudiés",
            _format_number(product_count),
            "Produits distincts",
            BLUE
        )

    with r2:
        category_count = _count_unique(
            research,
            ["product_category", "category"]
        )
        _kpi_card(
            "Catégories alimentaires",
            _format_number(category_count),
            "Catégories représentées",
            GREEN
        )

    with r3:
        batch_count = _count_unique(
            research,
            ["batch_id", "sample_reference", "sample_ref"]
        )
        _kpi_card(
            "Lots / Échantillons",
            _format_number(batch_count),
            "Identifiants distincts",
            ORANGE
        )

    if research.empty:
        st.info(
            "Le Research Dataset ne contient aucune observation "
            "dans les données actuellement transmises au Dashboard."
        )

    st.markdown("---")

    # -----------------------------------------------------
    # DATA QUALITY ISSUES
    # -----------------------------------------------------

    st.markdown("### Data Quality Monitoring")

    issues = _quality_issues(research)

    if quality_report is not None:
        st.caption(
            "Les indicateurs détaillés du moteur Data Quality "
            "peuvent être transmis séparément."
        )

    if issues:
        issue_df = pd.DataFrame(issues)
        st.dataframe(
            issue_df,
            hide_index=True,
            width="stretch"
        )
    else:
        if research.empty:
            st.info("Aucune donnée disponible pour effectuer le contrôle.")
        else:
            st.success(
                "Aucun problème détecté par les contrôles simples "
                "intégrés au Dashboard."
            )

    st.caption(
        "Ces contrôles sont indicatifs et ne remplacent pas "
        "le rapport complet du Data Quality Engine V2."
    )

    st.markdown("---")

    # -----------------------------------------------------
    # RECENT ACTIVITY
    # -----------------------------------------------------

    st.markdown("### Recent Activity")

    activity = _recent_activity(history, research)

    if not activity.empty:
        st.dataframe(
            activity,
            hide_index=True,
            width="stretch"
        )
    else:
        st.info("Aucune activité récente disponible.")

    st.markdown("---")

    # -----------------------------------------------------
    # PIPELINE STATUS
    # -----------------------------------------------------

    st.markdown("### FOODNEXA Data Pipeline")

    default_status = {
        "Risk Assessment Engine": history_count > 0,
        "Research Dataset": research_count > 0,
        "Data Quality Engine": research_count > 0,
        "Scientific Data Cleaning": False,
        "Research Analytics": research_count > 0,
        "Supabase": None
    }

    default_status.update(pipeline_status)

    pipeline_items = list(default_status.items())

    columns = st.columns(3)

    for index, (name, status) in enumerate(pipeline_items):
        with columns[index % 3]:

            if status is True:
                label = "Données disponibles"
                color = GREEN
                icon = "●"

            elif status is False:
                label = "Non disponible / non confirmé"
                color = ORANGE
                icon = "○"

            else:
                label = "Statut non vérifié"
                color = GREY
                icon = "○"

            st.markdown(
                f"""
                <div style="
                    border:1px solid #E4EAF0;
                    border-radius:9px;
                    background:white;
                    padding:13px;
                    margin-bottom:10px;
                ">
                    <div style="
                        font-size:13px;
                        font-weight:700;
                        color:{NAVY};
                    ">{name}</div>

                    <div style="
                        color:{color};
                        font-size:11px;
                        margin-top:7px;
                    ">
                        {icon} {label}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown(
        """
        <div style="
            margin-top:22px;
            padding:12px;
            border-top:1px solid #E4EAF0;
            color:#718096;
            font-size:11px;
            text-align:center;
        ">
            FOODNEXA — Experimental Food Safety & Risk Intelligence Platform
            <br>
            Decision-support prototype • Not a substitute for accredited laboratory testing
        </div>
        """,
        unsafe_allow_html=True
    )
