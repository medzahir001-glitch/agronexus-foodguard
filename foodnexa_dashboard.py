
import html
import json
import math
from datetime import date, timedelta

import pandas as pd
import streamlit as st


# ============================================================
# FOODNEXA - INTERACTIVE DASHBOARD V2
# Dynamic filters, KPIs, charts, tables and CSV export.
# Compatible with existing app.py render_dashboard() call.
# Source data is never modified or deleted.
# ============================================================


# -----------------------------
# DATA HELPERS
# -----------------------------

def _df(value):
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    try:
        return pd.DataFrame(value)
    except Exception:
        return pd.DataFrame()


def _missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in {
            "", "nan", "none", "null", "n/a"
        }
    try:
        result = pd.isna(value)
        if getattr(result, "ndim", 0) == 0:
            return bool(result)
    except (TypeError, ValueError):
        pass
    return False


def _text(value):
    if _missing(value):
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
            sort_keys=True
        )
    return str(value).strip()


def _column(df, names):
    if df.empty:
        return None

    lookup = {
        str(c).strip().casefold(): c
        for c in df.columns
    }

    for name in names:
        if name.casefold() in lookup:
            return lookup[name.casefold()]

    return None


def _number_series(df, names):
    col = _column(df, names)

    if col is None:
        return pd.Series(dtype="float64")

    return pd.to_numeric(
        df[col],
        errors="coerce"
    ).dropna()


def _risk_label(value):
    raw = _text(value).casefold()

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

    return mapping.get(raw)


def _safe_duplicates(df):
    if df.empty:
        return 0

    seen = set()
    duplicates = 0

    for row in df.itertuples(index=False, name=None):
        try:
            normalized = tuple(
                json.dumps(
                    v,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str
                )
                if isinstance(v, (dict, list, tuple))
                else (
                    None if _missing(v) else str(v)
                )
                for v in row
            )

            if normalized in seen:
                duplicates += 1
            else:
                seen.add(normalized)

        except Exception:
            continue

    return duplicates


def _quality_score(report):
    if not isinstance(report, dict):
        return None

    for key in (
        "quality_score",
        "overall_score",
        "score",
        "quality_percentage"
    ):
        try:
            value = float(report.get(key))

            if math.isfinite(value):
                return value

        except (TypeError, ValueError):
            pass

    return None


def _engine_issues(report):
    if not isinstance(report, dict):
        return []

    raw = report.get("issues", [])

    if not isinstance(raw, list):
        return []

    output = []

    for item in raw[:40]:

        if isinstance(item, dict):
            output.append({
                "Ligne": item.get(
                    "Ligne",
                    item.get("row", "—")
                ),
                "Champ": item.get(
                    "Champ",
                    item.get("field", "—")
                ),
                "Anomalie": item.get(
                    "Problème",
                    item.get(
                        "issue",
                        item.get(
                            "message",
                            item.get("type", "À vérifier")
                        )
                    )
                ),
                "Niveau": item.get(
                    "Niveau",
                    item.get(
                        "priority",
                        item.get("severity", "À vérifier")
                    )
                ),
            })

        else:
            output.append({
                "Ligne": "—",
                "Champ": "—",
                "Anomalie": str(item),
                "Niveau": "À vérifier"
            })

    return output


# -----------------------------
# DATE HELPERS
# -----------------------------

def _date_column(df):
    return _column(
        df,
        [
            "analysis_date",
            "created_at",
            "sampling_date",
            "date",
            "analysis_datetime"
        ]
    )


def _parsed_dates(df):
    col = _date_column(df)

    if col is None:
        return pd.Series(
            pd.NaT,
            index=df.index,
            dtype="datetime64[ns, UTC]"
        )

    return pd.to_datetime(
        df[col],
        errors="coerce",
        utc=True
    )


def _date_bounds(history, research):
    all_dates = []

    for frame in (history, research):

        if frame.empty:
            continue

        parsed = _parsed_dates(frame).dropna()

        if not parsed.empty:
            all_dates.extend(
                parsed.dt.date.tolist()
            )

    if not all_dates:
        today = date.today()
        return today, today

    return min(all_dates), max(all_dates)


def _filter_dates(df, start_date, end_date):
    if df.empty:
        return df.copy()

    parsed = _parsed_dates(df)

    if parsed.isna().all():
        return df.copy()

    start = pd.Timestamp(start_date, tz="UTC")
    end = (
        pd.Timestamp(end_date, tz="UTC")
        + pd.Timedelta(days=1)
        - pd.Timedelta(microseconds=1)
    )

    mask = (
        parsed.isna()
        | (
            (parsed >= start)
            & (parsed <= end)
        )
    )

    return df.loc[mask].copy()


def _filter_product(df, selected_product):
    if df.empty or selected_product == "Tous":
        return df.copy()

    col = _column(
        df,
        ["product_name", "product_category"]
    )

    if col is None:
        return df.copy()

    mask = (
        df[col]
        .map(_text)
        .str.casefold()
        == selected_product.casefold()
    )

    return df.loc[mask].copy()


def _filter_risk(df, selected_risk):
    if df.empty or selected_risk == "Tous":
        return df.copy()

    col = _column(df, ["risk_level"])

    if col is None:
        return df.copy()

    mask = (
        df[col]
        .map(_risk_label)
        == selected_risk
    )

    return df.loc[mask].copy()


# -----------------------------
# VISUAL STYLE
# -----------------------------

def _install_dashboard_style():

    st.markdown(
        """
        <style>

        :root {
            --fnx-green:#14532D;
            --fnx-green2:#238442;
            --fnx-light:#E8F5E9;
            --fnx-bg:#F5F7F5;
            --fnx-border:#DDE8DE;
            --fnx-ink:#17251B;
            --fnx-muted:#66756A;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .main,
        .block-container {
            background:#F5F7F5 !important;
        }

        .block-container {
            width:100% !important;
            max-width:none !important;
            padding:1.35rem 2rem 2rem !important;
        }

        [data-testid="stSidebar"] {
            min-width:250px !important;
            max-width:250px !important;
        }

        [data-testid="stAppViewContainer"] .main h1 {
            color:#14532D !important;
            font-size:2rem !important;
            font-weight:850 !important;
        }

        [data-testid="stAppViewContainer"] .main h2 {
            color:#174B2A !important;
            font-size:1.05rem !important;
            font-weight:800 !important;
        }

        .fnx-kpi {
            background:#FFFFFF;
            border:1px solid #DDE8DE;
            border-top:4px solid #238442;
            border-radius:12px;
            padding:13px 15px;
            min-height:92px;
            box-shadow:0 4px 14px rgba(20,65,35,.07);
            margin-bottom:10px;
        }

        .fnx-kpi-label {
            font-size:.70rem;
            color:#536357;
            font-weight:700;
        }

        .fnx-kpi-value {
            font-size:1.65rem;
            line-height:1.3;
            color:#14532D;
            font-weight:850;
        }

        .fnx-kpi-detail {
            font-size:.66rem;
            color:#718075;
            margin-top:3px;
        }

        .fnx-section-title {
            color:#174B2A;
            font-size:.95rem;
            font-weight:800;
            margin:12px 0 8px;
            padding-bottom:6px;
            border-bottom:1px solid #DDE8DE;
        }

        .fnx-filter-box {
            background:#FFFFFF;
            border:1px solid #DDE8DE;
            border-radius:12px;
            padding:12px 14px;
            margin:8px 0 14px;
        }

        div[data-testid="stDataFrame"] {
            background:#FFFFFF !important;
            border:1px solid #DDE8DE !important;
            border-radius:10px !important;
            overflow:hidden !important;
        }

        div[data-testid="stMetric"] {
            background:#FFFFFF !important;
            border:1px solid #DDE8DE !important;
            border-left:4px solid #238442 !important;
            border-radius:10px !important;
        }

        [data-testid="stVegaLiteChart"],
        [data-testid="stPyplotChart"] {
            background:#FFFFFF !important;
        }

        [data-testid="stDownloadButton"] button {
            background:#14532D !important;
            color:#FFFFFF !important;
            border:0 !important;
            border-radius:8px !important;
            font-weight:700 !important;
        }

        [data-testid="stDownloadButton"] button p {
            color:#FFFFFF !important;
        }

        @media (max-width:900px) {
            .block-container {
                padding-left:1rem !important;
                padding-right:1rem !important;
            }
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# -----------------------------
# KPI CARDS
# -----------------------------

def _card(label, value, detail="", accent="green", icon=""):

    palette = {
        "green": "#238442",
        "red": "#C62828",
        "amber": "#D99121",
        "navy": "#14532D",
    }

    color = palette.get(accent, palette["green"])

    st.markdown(
        f"""
        <div class="fnx-kpi"
             style="border-top:4px solid {color}">
            <div class="fnx-kpi-label">
                {html.escape(str(icon))}
                {html.escape(str(label))}
            </div>
            <div class="fnx-kpi-value">
                {html.escape(str(value))}
            </div>
            <div class="fnx-kpi-detail">
                {html.escape(str(detail))}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------
# CIRCULAR CHARTS
# -----------------------------

def _render_donut(labels, values):

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.error(
            "Matplotlib n'est pas installé. "
            "Ajoutez matplotlib dans requirements.txt."
        )
        return

    total = sum(values)

    if total <= 0:
        st.info("Aucune donnée disponible.")
        return

    colors = [
        "#238442",
        "#C62828",
        "#D9E8D9"
    ]

    actual = [
        (label, value, color)
        for label, value, color
        in zip(labels, values, colors)
        if value > 0
    ]

    fig, ax = plt.subplots(
        figsize=(4.5, 3.1),
        dpi=130
    )

    fig.patch.set_facecolor("white")

    wedges, _ = ax.pie(
        [x[1] for x in actual],
        colors=[x[2] for x in actual],
        startangle=90,
        counterclock=False,
        wedgeprops={
            "width":0.32,
            "edgecolor":"white",
            "linewidth":2
        }
    )

    ax.text(
        0,
        0,
        str(total),
        ha="center",
        va="center",
        fontsize=19,
        fontweight="bold",
        color="#14532D"
    )

    ax.legend(
        wedges,
        [
            f"{x[0]} ({x[1]})"
            for x in actual
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
        fontsize=8
    )

    ax.set_aspect("equal")
    fig.tight_layout()

    st.pyplot(
        fig,
        use_container_width=True
    )

    plt.close(fig)


def _render_category_donut(series):

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.error("Matplotlib n'est pas installé.")
        return

    series = (
        series[series > 0]
        .sort_values(ascending=False)
        .head(7)
    )

    if series.empty:
        st.info("Aucune catégorie renseignée.")
        return

    palette = [
        "#14532D",
        "#238442",
        "#3D9146",
        "#5DA957",
        "#79B96C",
        "#9BCB8D",
        "#C5DFC0"
    ]

    fig, ax = plt.subplots(
        figsize=(4.8, 3.4),
        dpi=140
    )

    fig.patch.set_facecolor("white")

    wedges, _ = ax.pie(
        series.values,
        colors=palette[:len(series)],
        startangle=90,
        counterclock=False,
        wedgeprops={
            "width":0.34,
            "edgecolor":"white",
            "linewidth":2
        }
    )

    ax.text(
        0,
        0,
        f"{int(series.sum())}\nObservations",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#14532D"
    )

    ax.legend(
        wedges,
        [
            f"{str(label)[:20]} ({int(value)})"
            for label, value in zip(
                series.index,
                series.values
            )
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
        fontsize=7.5
    )

    ax.set_aspect("equal")
    fig.tight_layout()

    st.pyplot(
        fig,
        use_container_width=True
    )

    plt.close(fig)


# -----------------------------
# INTERACTIVE FILTERS
# -----------------------------

def _render_filters(history, research):

    st.markdown(
        '<div class="fnx-section-title">Dashboard Filters</div>',
        unsafe_allow_html=True
    )

    min_date, max_date = _date_bounds(
        history,
        research
    )

    products = set()

    for frame in (history, research):

        col = _column(
            frame,
            ["product_name", "product_category"]
        )

        if col is not None:
            products.update(
                value
                for value in frame[col].map(_text).tolist()
                if value
            )

    product_options = ["Tous"] + sorted(products)

    c1, c2, c3 = st.columns(
        [1.5, 1.2, 1.1],
        gap="medium"
    )

    with c1:

        date_range = st.date_input(
            "Période d'analyse",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="fnx_dashboard_date_range"
        )

    with c2:

        selected_product = st.selectbox(
            "Produit / Catégorie",
            product_options,
            index=0,
            key="fnx_dashboard_product"
        )

    with c3:

        selected_risk = st.selectbox(
            "Niveau de risque",
            ["Tous", "Faible", "Modéré", "Élevé"],
            index=0,
            key="fnx_dashboard_risk"
        )

    if isinstance(date_range, (tuple, list)):

        if len(date_range) == 2:
            start_date, end_date = date_range
        elif len(date_range) == 1:
            start_date = end_date = date_range[0]
        else:
            start_date, end_date = min_date, max_date

    else:
        start_date = end_date = date_range

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    filtered_history = _filter_dates(
        history,
        start_date,
        end_date
    )

    filtered_research = _filter_dates(
        research,
        start_date,
        end_date
    )

    filtered_history = _filter_product(
        filtered_history,
        selected_product
    )

    filtered_research = _filter_product(
        filtered_research,
        selected_product
    )

    filtered_history = _filter_risk(
        filtered_history,
        selected_risk
    )

    return (
        filtered_history,
        filtered_research,
        start_date,
        end_date
    )


# -----------------------------
# MAIN DASHBOARD
# -----------------------------

def render_dashboard(
    history_data=None,
    research_data=None,
    quality_report=None,
    pipeline_status=None
):

    _install_dashboard_style()

    history = _df(history_data)
    research = _df(research_data)

    st.title("FOODNEXA Dashboard")

    st.caption(
        "Interactive Food Safety Risk Intelligence "
        "and Research Monitoring"
    )

    # Filters
    (
        filtered_history,
        filtered_research,
        start_date,
        end_date
    ) = _render_filters(
        history,
        research
    )

    # Risk indicators
    risk_col = _column(
        filtered_history,
        ["risk_level"]
    )

    levels = (
        filtered_history[risk_col].map(_risk_label)
        if risk_col
        else pd.Series(dtype="object")
    )

    low = int((levels == "Faible").sum())
    moderate = int((levels == "Modéré").sum())
    high = int((levels == "Élevé").sum())

    total_analyses = len(filtered_history)
    total_research = len(filtered_research)

    scores = _number_series(
        filtered_history,
        ["risk_score"]
    )

    average_risk = (
        f"{scores.mean():.1f}/100"
        if not scores.empty
        else "N/D"
    )

    global_quality = _quality_score(
        quality_report
    )

    quality_text = (
        f"{global_quality:.1f}%"
        if global_quality is not None
        else "N/D"
    )

    # KPI cards
    st.markdown(
        '<div class="fnx-section-title">Key Performance Indicators</div>',
        unsafe_allow_html=True
    )

    kpis = st.columns(4, gap="medium")

    with kpis[0]:
        _card(
            "Total Analyses",
            total_analyses,
            "Filtered risk assessments",
            "green",
            "✓"
        )

    with kpis[1]:
        _card(
            "Research Observations",
            total_research,
            "Filtered research records",
            "green",
            "▤"
        )

    with kpis[2]:
        _card(
            "High Risk",
            high,
            "Filtered high-risk records",
            "red",
            "!"
        )

    with kpis[3]:
        _card(
            "Average Risk Score",
            average_risk,
            "Filtered assessments",
            "navy",
            "◉"
        )

    if selected_product if False else False:
        pass

    st.caption(
        f"Filtered period: {start_date} → {end_date} | "
        f"Analyses: {total_analyses} | "
        f"Research records: {total_research}"
    )

    # Charts
    st.markdown(
        '<div class="fnx-section-title">Interactive Analytics</div>',
        unsafe_allow_html=True
    )

    left, right = st.columns(
        [1, 1],
        gap="large"
    )

    with left:

        st.markdown("**Risk Distribution**")

        if total_analyses > 0:

            _render_donut(
                [
                    "Low Risk",
                    "Moderate Risk",
                    "High Risk"
                ],
                [
                    low,
                    moderate,
                    high
                ]
            )

        else:
            st.info(
                "Aucune analyse de risque pour les filtres choisis."
            )

    with right:

        st.markdown("**Product Category Distribution**")

        category_col = _column(
            filtered_research,
            ["product_category", "product_name"]
        )

        if category_col and not filtered_research.empty:

            categories = (
                filtered_research[category_col]
                .map(_text)
                .replace("", pd.NA)
                .dropna()
                .value_counts()
            )

            if not categories.empty:
                _render_category_donut(categories)
            else:
                st.info("Aucune catégorie renseignée.")

        else:
            st.info(
                "Aucune observation de recherche "
                "pour les filtres choisis."
            )

    # Activity
    st.markdown(
        '<div class="fnx-section-title">Recent Activity</div>',
        unsafe_allow_html=True
    )

    activity = []

    if not filtered_history.empty:

        for _, row in filtered_history.tail(10).iterrows():

            activity.append({
                "Date": _text(
                    row.get(
                        "analysis_date",
                        row.get("created_at", "")
                    )
                ),
                "Type": "Risk Assessment",
                "Sample ID": _text(row.get("batch_id", "")),
                "Product": _text(row.get("product_name", "")),
                "Result": _text(row.get("risk_level", "")),
            })

    if not filtered_research.empty:

        for _, row in filtered_research.tail(10).iterrows():

            activity.append({
                "Date": _text(
                    row.get(
                        "analysis_date",
                        row.get("created_at", "")
                    )
                ),
                "Type": "Research Observation",
                "Sample ID": _text(row.get("batch_id", "")),
                "Product": _text(row.get("product_name", "")),
                "Result": "Observation recorded",
            })

    if activity:

        activity_df = pd.DataFrame(activity)

        st.dataframe(
            activity_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Aucune activité disponible.")

    # Analysis history
    st.markdown(
        '<div class="fnx-section-title">Analysis History</div>',
        unsafe_allow_html=True
    )

    if not filtered_history.empty:

        history_display = filtered_history.copy()

        display_cols = [
            c for c in [
                "analysis_date",
                "batch_id",
                "product_name",
                "risk_score",
                "risk_level"
            ]
            if c in history_display.columns
        ]

        if display_cols:

            st.dataframe(
                history_display[display_cols].tail(100),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.dataframe(
                history_display.tail(100),
                use_container_width=True,
                hide_index=True
            )

    else:
        st.info(
            "Aucun résultat d'analyse pour les filtres sélectionnés."
        )

    # Research dataset
    st.markdown(
        '<div class="fnx-section-title">Research Dataset</div>',
        unsafe_allow_html=True
    )

    if not filtered_research.empty:

        st.dataframe(
            filtered_research.tail(100),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "Aucune observation de recherche pour les filtres sélectionnés."
        )

    # CSV exports
    st.markdown(
        '<div class="fnx-section-title">Export Filtered Data</div>',
        unsafe_allow_html=True
    )

    export1, export2 = st.columns(2)

    with export1:

        csv_history = filtered_history.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "Download Risk Assessments CSV",
            data=csv_history,
            file_name="foodnexa_filtered_risk_assessments.csv",
            mime="text/csv",
            key="fnx_export_history"
        )

    with export2:

        csv_research = filtered_research.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "Download Research Dataset CSV",
            data=csv_research,
            file_name="foodnexa_filtered_research.csv",
            mime="text/csv",
            key="fnx_export_research"
        )

    # Quality and system status
    with st.expander(
        "Data Quality & System Status",
        expanded=False
    ):

        q1, q2, q3 = st.columns(3)

        q1.metric(
            "Global Data Quality",
            quality_text
        )

        q2.metric(
            "Research Observations",
            len(research)
        )

        q3.metric(
            "Exact Duplicates",
            _safe_duplicates(research)
        )

        st.caption(
            "Data Quality Score is calculated on the full "
            "dataset supplied by the application, not on "
            "the currently filtered subset."
        )

        issues = _engine_issues(
            quality_report
        )

        if issues:

            st.markdown("**Quality issues to review**")

            st.dataframe(
                pd.DataFrame(issues),
                use_container_width=True,
                hide_index=True
            )

        elif research.empty:

            st.info(
                "En attente de données pour le contrôle qualité."
            )

        else:

            st.success(
                "Aucune anomalie signalée par le rapport qualité."
            )

        if isinstance(pipeline_status, dict):

            st.markdown("**FOODNEXA System Pipeline**")

            for name, status in pipeline_status.items():

                if status is True:
                    st.success(
                        f"{name} — Disponible"
                    )

                elif status is False:
                    st.warning(
                        f"{name} — Indisponible"
                    )

                else:
                    st.info(
                        f"{name} — Statut non confirmé"
                    )

    st.caption(
        "FOODNEXA est un prototype expérimental de "
        "Food Safety Risk Intelligence. "
        "Les indicateurs ne remplacent pas les analyses "
        "de laboratoire, l'expertise scientifique "
        "ou les exigences réglementaires applicables."
    )
