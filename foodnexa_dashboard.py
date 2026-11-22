
import html
import json
import math

import pandas as pd
import streamlit as st


# ============================================================
# FOODNEXA - WHITE ENTERPRISE DASHBOARD
# Compatible with app.py render_dashboard(...) call signature.
# Keeps source data read-only.
# ============================================================


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
        return value.strip().casefold() in {"", "nan", "none", "null", "n/a"}
    if isinstance(value, (dict, list, tuple, set)):
        return len(value) == 0
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
        str(column).strip().casefold(): column
        for column in df.columns
    }

    for name in names:
        if name.casefold() in lookup:
            return lookup[name.casefold()]

    return None


def _number_series(df, names):
    col = _column(df, names)

    if col is None:
        return pd.Series(dtype="float64")

    return pd.to_numeric(df[col], errors="coerce").dropna()


def _unique_count(df, names):
    col = _column(df, names)

    if col is None:
        return 0

    values = df[col].map(_text)
    values = values[values != ""]

    return int(values.nunique())


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
                    value,
                    ensure_ascii=False,
                    sort_keys=True,
                    default=str
                )
                if isinstance(value, (dict, list, tuple))
                else (None if _missing(value) else str(value))
                for value in row
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


def _card(label, value, detail="", accent="blue", icon=""):
    palette = {
        "blue": "#0B6F91",
        "green": "#15966F",
        "red": "#D94B4B",
        "amber": "#D99121",
        "navy": "#173B5E",
    }

    color = palette.get(accent, palette["blue"])

    st.markdown(
        f"""
        <div class="fnx-kpi" style="border-top:4px solid {color}">
          <div class="fnx-kpi-label">
            {html.escape(str(icon))} {html.escape(str(label))}
          </div>
          <div class="fnx-kpi-value">
            {html.escape(str(value))}
          </div>
          <div class="fnx-kpi-detail">
            {html.escape(str(detail))}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _install_dashboard_style():
    st.markdown(
        """
        <style>
        :root {
          --fnx-navy:#124B27;
          --fnx-blue:#1D6536;
          --fnx-teal:#258A4A;
          --fnx-green:#2F8F46;
          --fnx-ink:#17251B;
          --fnx-muted:#66756A;
          --fnx-border:#DDE8DE;
          --fnx-bg:#F5F7F5;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        .main,
        .block-container {
          background:#F5F7F5 !important;
        }

        .block-container {
          width:100% !important;
          max-width:none !important;
          padding:1.35rem 2rem 2rem !important;
        }

        [data-testid="stMainBlockContainer"] {
          width:100% !important;
          max-width:none !important;
        }

        [data-testid="stSidebar"] {
          min-width:250px !important;
          max-width:250px !important;
          background:#124B27 !important;
          border-right:1px solid #DDE8DE !important;
        }

        [data-testid="stSidebar"] * {
          color:#FFFFFF !important;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label {
          background:rgba(255,255,255,.07);
          border-radius:8px;
          padding:7px 10px;
          margin:2px 0;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
          background:rgba(255,255,255,.16);
        }

        [data-testid="stAppViewContainer"] .main p,
        [data-testid="stAppViewContainer"] .main li,
        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main span {
          color:var(--fnx-ink);
        }

        [data-testid="stAppViewContainer"] .main h1 {
          color:#14532D !important;
          font-size:2.05rem !important;
          font-weight:850 !important;
          letter-spacing:-1.1px !important;
          margin-bottom:.15rem !important;
        }

        [data-testid="stAppViewContainer"] .main h2 {
          color:#174B2A !important;
          font-size:1.02rem !important;
          font-weight:800 !important;
        }

        [data-testid="stAppViewContainer"] .main h3 {
          color:#236B3A !important;
          font-size:0.88rem !important;
          font-weight:750 !important;
        }

        [data-testid="stAppViewContainer"] .main
        [data-testid="stCaptionContainer"] p {
          color:#526357 !important;
        }

        .fnx-kpi {
          background:#FFFFFF;
          border:1px solid var(--fnx-border);
          border-radius:12px;
          padding:12px 14px;
          min-height:88px;
          box-shadow:0 4px 14px rgba(20,65,35,.07);
          margin-bottom:12px;
        }

        .fnx-kpi-label {
          font-size:.70rem;
          color:#536357;
          font-weight:700;
        }

        .fnx-kpi-value {
          font-size:1.7rem;
          line-height:1.25;
          color:#14532D;
          font-weight:850;
        }

        .fnx-kpi-detail {
          font-size:.66rem;
          color:#718075;
          margin-top:3px;
        }

        .fnx-section {
          background:#FFFFFF;
          border:1px solid var(--fnx-border);
          border-radius:12px;
          padding:12px 14px;
          margin:6px 0 11px;
          box-shadow:0 2px 10px rgba(20,65,35,.045);
        }

        .fnx-section-title {
          color:#174B2A;
          font-size:.94rem;
          font-weight:800;
          margin:5px 0 7px;
          padding-bottom:5px;
          border-bottom:1px solid #DDE8DE;
        }

        .fnx-dashboard-gap {
          height:8px;
        }

        [data-testid="stDataFrame"] {
          font-size:.78rem !important;
          background:#FFFFFF !important;
          border:1px solid var(--fnx-border) !important;
          border-radius:10px !important;
          overflow:hidden !important;
          box-shadow:0 2px 9px rgba(20,65,35,.045);
        }

        [data-testid="stDataFrame"] * {
          color:#203648 !important;
        }

        [data-testid="stVegaLiteChart"],
        [data-testid="stArrowVegaLiteChart"],
        [data-testid="stPyplotChart"] {
          background:#FFFFFF !important;
        }

        div[data-testid="stMetric"] {
          background:#FFFFFF !important;
          border:1px solid var(--fnx-border) !important;
          border-left:4px solid #2F8F46 !important;
          border-radius:12px !important;
          box-shadow:0 2px 9px rgba(20,65,35,.06) !important;
        }

        div[data-testid="stMetric"] * {
          color:var(--fnx-navy) !important;
        }

        .fnx-status-chip {
          display:inline-block;
          text-align:center;
          margin-top:12px;
          padding:8px 12px;
          border-radius:20px;
          background:#E8F3E8;
          color:#14532D;
          font-size:.72rem;
          font-weight:800;
          border:1px solid #C9E2CC;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
          gap:8px;
          border-bottom:1px solid #D6E5D8;
        }

        [data-testid="stTabs"] button[role="tab"] {
          background:#FFFFFF;
          border:1px solid #D6E5D8;
          border-radius:9px 9px 0 0;
          padding:8px 16px;
          color:#174B2A;
          font-weight:750;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
          background:#E8F3E8;
          color:#14532D;
          border-bottom:3px solid #238442;
        }

        .fnx-pill {
          display:inline-block;
          padding:4px 9px;
          border-radius:30px;
          background:#EAF5E9;
          color:#1B6633;
          font-size:.72rem;
          font-weight:750;
        }

        hr {
          border-color:#E1E9E1 !important;
          margin:.75rem 0 !important;
        }

        @media (max-width: 900px) {
          .block-container {
            padding-left:1rem !important;
            padding-right:1rem !important;
          }

          [data-testid="stSidebar"] {
            min-width:0 !important;
            max-width:none !important;
          }

          [data-testid="stAppViewContainer"] .main h1 {
            font-size:1.9rem !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_activity(history, research):
    records = []

    if not history.empty:
        for _, row in history.tail(12).iterrows():
            records.append({
                "Date": _text(row.get("analysis_date", "")),
                "Type": "Évaluation du risque",
                "Lot": _text(row.get("batch_id", "")),
                "Produit": _text(row.get("product_name", "")),
                "Résultat": (
                    f'{_text(row.get("risk_level", ""))} — '
                    f'{_text(row.get("risk_score", ""))}'
                ),
            })

    if not research.empty:
        for _, row in research.tail(12).iterrows():
            records.append({
                "Date": _text(
                    row.get("analysis_date", row.get("created_at", ""))
                ),
                "Type": "Observation de recherche",
                "Lot": _text(row.get("batch_id", "")),
                "Produit": _text(row.get("product_name", "")),
                "Résultat": "Observation enregistrée",
            })

    if not records:
        st.info("Aucune activité enregistrée pour le moment.")
        return

    frame = pd.DataFrame(records)
    frame["_date"] = pd.to_datetime(
        frame["Date"],
        errors="coerce",
        utc=True
    )

    frame = (
        frame.sort_values(
            "_date",
            ascending=False,
            na_position="last"
        )
        .drop(columns="_date")
    )

    st.dataframe(
        frame.head(10),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# COMPACT RISK DONUT
# ============================================================

def _render_donut(labels, values):

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.error("Matplotlib n'est pas installé.")
        return

    total = sum(values)

    if total <= 0:
        st.info("Aucune donnée de risque disponible.")
        return

    colors = [
        "#238442",
        "#D99121",
        "#C62828",
    ]

    actual = [
        (label, value, color)
        for label, value, color in zip(labels, values, colors)
        if value > 0
    ]

    if not actual:
        st.info("Aucune donnée de risque disponible.")
        return

    # Compact figure: avoids oversized dashboard charts.
    fig, ax = plt.subplots(
        figsize=(3.0, 2.25),
        dpi=110
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    wedges, _ = ax.pie(
        [item[1] for item in actual],
        colors=[item[2] for item in actual],
        startangle=90,
        counterclock=False,
        wedgeprops={
            "width": 0.30,
            "edgecolor": "white",
            "linewidth": 1.5
        }
    )

    ax.text(
        0,
        0,
        str(total),
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#14532D"
    )

    ax.legend(
        wedges,
        [
            f"{item[0]} ({item[1]})"
            for item in actual
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=2,
        frameon=False,
        fontsize=7
    )

    ax.set_aspect("equal")

    fig.subplots_adjust(
        left=0.05,
        right=0.95,
        top=0.95,
        bottom=0.25
    )

    # Important: do not stretch the chart to the full column width.
    st.pyplot(
        fig,
        use_container_width=False
    )

    plt.close(fig)


# ============================================================
# COMPACT PRODUCT CATEGORY DONUT
# ============================================================

def _render_category_bars(series):

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.warning(
            "Le graphique circulaire nécessite matplotlib. "
            "Ajoutez matplotlib aux dépendances pour l'afficher."
        )
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
        figsize=(3.2, 2.4),
        dpi=110
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    wedges, _ = ax.pie(
        series.values,
        colors=palette[:len(series)],
        startangle=90,
        counterclock=False,
        wedgeprops={
            "width": 0.32,
            "edgecolor": "white",
            "linewidth": 1.5
        }
    )

    total = int(series.sum())

    ax.text(
        0,
        0,
        f"{total}\nObservations",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#14532D"
    )

    legend_labels = [
        f"{str(label)[:18]} ({int(value)})"
        for label, value in zip(series.index, series.values)
    ]

    ax.legend(
        wedges,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=2 if len(series) > 1 else 1,
        frameon=False,
        fontsize=6.5,
        labelcolor="#26352A",
        handlelength=1.0,
        columnspacing=1.0,
    )

    ax.set_aspect("equal")

    fig.subplots_adjust(
        left=0.05,
        right=0.95,
        top=0.95,
        bottom=0.25
    )

    # Important: do not stretch the chart to the full column width.
    st.pyplot(
        fig,
        use_container_width=False
    )

    plt.close(fig)


# ============================================================
# MAIN DASHBOARD
# ============================================================

def render_dashboard(
    history_data=None,
    research_data=None,
    quality_report=None,
    pipeline_status=None
):
    """FOODNEXA dashboard."""

    _install_dashboard_style()

    history = _df(history_data)
    research = _df(research_data)

    risk_col = _column(
        history,
        ["risk_level"]
    )

    risk_score_col = _column(
        history,
        ["risk_score"]
    )

    levels = (
        history[risk_col].map(_risk_label)
        if risk_col
        else pd.Series(dtype="object")
    )

    low = int((levels == "Faible").sum())
    moderate = int((levels == "Modéré").sum())
    high = int((levels == "Élevé").sum())

    score = _quality_score(quality_report)

    score_text = (
        f"{score:.1f}%"
        if score is not None
        else "N/D"
    )

    scores = _number_series(
        history,
        ["risk_score"]
    )

    average = (
        f"{scores.mean():.1f}/100"
        if not scores.empty
        else "N/D"
    )

    # Dashboard title
    st.title("Dashboard")

    st.caption(
        "Monitoring agro-food quality, food safety risks "
        "and research data"
    )

    # Four KPI cards
    kpis = st.columns(4, gap="medium")

    with kpis[0]:
        _card(
            "Total Analyses",
            len(history),
            "Risk assessments",
            "green",
            "✓"
        )

    with kpis[1]:
        _card(
            "Research Observations",
            len(research),
            "Scientific records",
            "green",
            "▤"
        )

    with kpis[2]:
        _card(
            "High Risk",
            high,
            "Requires attention",
            "red",
            "!"
        )

    with kpis[3]:
        _card(
            "Data Quality",
            score_text,
            "Dataset quality score",
            "navy",
            "◉"
        )

    st.markdown(
        '<div class="fnx-dashboard-gap"></div>',
        unsafe_allow_html=True
    )

    # Main dashboard layout
    left, right = st.columns(
        [0.88, 1.62],
        gap="medium"
    )

    # --------------------------------------------------------
    # LEFT COLUMN: CHARTS
    # --------------------------------------------------------

    with left:

        st.markdown(
            '<div class="fnx-section-title">'
            'Conformity Rate</div>',
            unsafe_allow_html=True
        )

        if not history.empty and risk_col:

            # This is a risk indicator, not a regulatory
            # conformity decision.
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
            st.info("Aucune évaluation disponible.")

        st.markdown(
            '<div class="fnx-section-title">'
            'Product Category Distribution</div>',
            unsafe_allow_html=True
        )

        category_col = _column(
            research,
            [
                "product_category",
                "product_name"
            ]
        )

        if category_col and not research.empty:

            categories = (
                research[category_col]
                .map(_text)
                .replace("", pd.NA)
                .dropna()
                .value_counts()
            )

            if not categories.empty:
                _render_category_bars(categories)
            else:
                st.caption("Aucune catégorie renseignée.")

        else:
            st.caption(
                "Les catégories apparaîtront après "
                "l'enregistrement des observations."
            )

        st.caption(
            "Répartition circulaire des niveaux de risque. "
            "Les catégories ne constituent pas une décision "
            "réglementaire de conformité."
        )

    # --------------------------------------------------------
    # RIGHT COLUMN: ACTIVITY AND HISTORY
    # --------------------------------------------------------

    with right:

        st.markdown(
            '<div class="fnx-section-title">'
            'Recent Activity</div>',
            unsafe_allow_html=True
        )

        activity = []

        if not history.empty:

            for _, row in history.tail(8).iterrows():

                activity.append({
                    "Date": _text(
                        row.get(
                            "analysis_date",
                            row.get("created_at", "")
                        )
                    ),
                    "Sample ID": _text(
                        row.get("batch_id", "")
                    ),
                    "Product": _text(
                        row.get("product_name", "")
                    ),
                    "Result": _text(
                        row.get("risk_level", "")
                    ),
                })

        if not research.empty:

            for _, row in research.tail(8).iterrows():

                activity.append({
                    "Date": _text(
                        row.get(
                            "analysis_date",
                            row.get("created_at", "")
                        )
                    ),
                    "Sample ID": _text(
                        row.get("batch_id", "")
                    ),
                    "Product": _text(
                        row.get("product_name", "")
                    ),
                    "Result": "Research observation",
                })

        if activity:

            activity_df = pd.DataFrame(activity)

            activity_df["_sort"] = pd.to_datetime(
                activity_df["Date"],
                errors="coerce",
                utc=True
            )

            activity_df = (
                activity_df.sort_values(
                    "_sort",
                    ascending=False,
                    na_position="last"
                )
                .drop(columns="_sort")
            )

            st.dataframe(
                activity_df.head(6),
                use_container_width=True,
                hide_index=True,
                height=210
            )

        else:
            st.info("Aucune activité récente.")

        st.markdown(
            '<div class="fnx-section-title">'
            'Analysis History</div>',
            unsafe_allow_html=True
        )

        if not history.empty:

            history_rows = []

            for _, row in history.tail(7).iloc[::-1].iterrows():

                history_rows.append({
                    "Date": _text(
                        row.get("analysis_date", "")
                    ),
                    "Sample ID": _text(
                        row.get("batch_id", "")
                    ),
                    "Product": _text(
                        row.get("product_name", "")
                    ),
                    "Analyst": _text(
                        row.get(
                            "analyst",
                            row.get("analyst_name", "—")
                        )
                    ) or "—",
                    "Result": _text(
                        row.get("risk_level", "")
                    ),
                })

            st.dataframe(
                pd.DataFrame(history_rows),
                use_container_width=True,
                hide_index=True,
                height=245
            )

        else:
            st.info("Aucun historique disponible.")

    # --------------------------------------------------------
    # DATA QUALITY AND SYSTEM STATUS
    # --------------------------------------------------------

    with st.expander(
        "Data Quality & System Status",
        expanded=False
    ):

        q1, q2, q3 = st.columns(3)

        q1.metric(
            "Quality Score",
            score_text
        )

        q2.metric(
            "Research Observations",
            len(research)
        )

        q3.metric(
            "Exact Duplicates",
            _safe_duplicates(research)
        )

        issues = _engine_issues(quality_report)

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

        if isinstance(pipeline_status, dict) and pipeline_status:

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
        "de laboratoire, l'expertise scientifique ou "
        "les exigences réglementaires applicables."
    )
