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
        return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    return str(value).strip()


def _column(df, names):
    if df.empty:
        return None
    lookup = {str(c).strip().casefold(): c for c in df.columns}
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
        "faible": "Faible", "low": "Faible",
        "modéré": "Modéré", "modere": "Modéré",
        "moderate": "Modéré", "medium": "Modéré",
        "élevé": "Élevé", "eleve": "Élevé", "high": "Élevé",
    }
    return mapping.get(raw)


def _safe_duplicates(df):
    if df.empty:
        return 0
    seen, duplicates = set(), 0
    for row in df.itertuples(index=False, name=None):
        try:
            normalized = tuple(
                json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)
                if isinstance(v, (dict, list, tuple))
                else (None if _missing(v) else str(v))
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
    for key in ("quality_score", "overall_score", "score", "quality_percentage"):
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
                "Ligne": item.get("Ligne", item.get("row", "—")),
                "Champ": item.get("Champ", item.get("field", "—")),
                "Anomalie": item.get(
                    "Problème",
                    item.get("issue", item.get("message", item.get("type", "À vérifier")))
                ),
                "Niveau": item.get(
                    "Niveau",
                    item.get("priority", item.get("severity", "À vérifier"))
                ),
            })
        else:
            output.append({"Ligne": "—", "Champ": "—", "Anomalie": str(item), "Niveau": "À vérifier"})
    return output


def _card(label, value, detail="", accent="green", icon=""):
    palette = {
        "green": "#1B5E20",
        "red": "#C62828",
        "amber": "#B7791F",
        "navy": "#1B5E20",
    }
    color = palette.get(accent, palette["green"])
    st.markdown(
        f"""
        <div class="fnx-kpi" style="border-top:3px solid {color}">
          <div class="fnx-kpi-label"><span class="fnx-kpi-icon">{html.escape(str(icon))}</span> {html.escape(str(label))}</div>
          <div class="fnx-kpi-value">{html.escape(str(value))}</div>
          <div class="fnx-kpi-detail">{html.escape(str(detail))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _install_dashboard_style():
    st.markdown(
        """
        <style>
        :root {
          --fnx-navy:#1B5E20; --fnx-green:#2E7D32; --fnx-teal:#66A86B;
          --fnx-green:#2F8F46; --fnx-ink:#17251B; --fnx-muted:#66756A;
          --fnx-border:#DDE8DE; --fnx-bg:#F5F7F5;
        }
        [data-testid="stAppViewContainer"], [data-testid="stMain"],
        [data-testid="stMainBlockContainer"], .main, .block-container {
          background:#F5F7F5 !important;
        }
        /* Use the full available desktop canvas instead of a narrow centered column. */
        .block-container {
          width:100% !important; max-width:none !important;
          padding:0.85rem 1.35rem 1.25rem !important;
        }
        [data-testid="stMainBlockContainer"] {
          width:100% !important; max-width:none !important;
        }
        [data-testid="stSidebar"] {
          min-width:220px !important; max-width:220px !important;
        }
        [data-testid="stSidebar"] {
          background:#FFFFFF !important;
          border-right:1px solid #DDE8DE !important;
        }
        [data-testid="stSidebar"] * {color:#203326 !important;}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
          background:transparent; border-radius:8px;
          padding:5px 8px; margin:1px 0; font-size:.76rem; font-weight:650;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
          background:#E8F5E9;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
          background:#1B5E20 !important; color:#FFFFFF !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) * {
          color:#FFFFFF !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] input {
          display:none !important;
        }
        [data-testid="stAppViewContainer"] .main p,
        [data-testid="stAppViewContainer"] .main li,
        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main span {
          color:var(--fnx-ink);
        }
        [data-testid="stAppViewContainer"] .main h1 {
          color:#14532D !important; font-size:1.35rem !important;
          font-weight:850 !important; letter-spacing:-1.1px !important;
          margin-bottom:.15rem !important;
        }
        [data-testid="stAppViewContainer"] .main h2 {
          color:#174B2A !important; font-size:.90rem !important;
          font-weight:800 !important;
        }
        [data-testid="stAppViewContainer"] .main h3 {
          color:#236B3A !important; font-size:0.80rem !important;
          font-weight:750 !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] p {
          color:#526357 !important;
        }
        .fnx-kpi {
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-radius:12px; padding:8px 10px; min-height:68px;
          box-shadow:0 4px 14px rgba(20,65,35,.07); margin-bottom:12px;
        }
        .fnx-kpi-label {font-size:.72rem; color:#536357; font-weight:700;}
        .fnx-kpi-icon {font-size:.72rem; line-height:1; color:#1B5E20; display:inline-block; margin-right:2px;}
        .fnx-kpi-value {font-size:1.12rem; line-height:1.25; color:#14532D; font-weight:850;}
        .fnx-kpi-detail {font-size:.66rem; color:#718075; margin-top:3px;}
        .fnx-section {
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-radius:12px; padding:12px 14px; margin:6px 0 11px;
          box-shadow:0 2px 10px rgba(20,65,35,.045);
        }
        .fnx-section-title {font-size:.88rem; color:#174B2A; font-weight:800; margin-bottom:8px;}
        div[data-testid="stDataFrame"] {
          background:#FFFFFF !important; border:1px solid var(--fnx-border) !important;
          border-radius:8px !important; overflow:hidden !important;
        }
        div[data-testid="stDataFrame"] * {color:#203326 !important;}
        [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"],
        [data-testid="stPyplotChart"] {background:#FFFFFF !important;}
        div[data-testid="stMetric"] {
          background:#FFFFFF !important; border:1px solid var(--fnx-border) !important;
          border-left:3px solid #2F8F46 !important; border-radius:12px !important;
          box-shadow:0 2px 9px rgba(20,65,35,.06) !important;
        }
        div[data-testid="stMetric"] * {color:var(--fnx-navy) !important;}

        .fnx-status-chip {
          display:inline-block; text-align:center; margin-top:12px;
          padding:8px 12px; border-radius:20px; background:#E8F3E8;
          color:#14532D; font-size:.72rem; font-weight:800;
          border:1px solid #C9E2CC;
        }
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
          gap:8px; border-bottom:1px solid #D6E5D8;
        }
        [data-testid="stTabs"] button[role="tab"] {
          background:#FFFFFF; border:1px solid #D6E5D8;
          border-radius:9px 9px 0 0; padding:8px 16px;
          color:#174B2A; font-weight:750;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
          background:#E8F5E9; color:#14532D;
          border-bottom:3px solid #238442;
        }
        .fnx-kpi {padding:8px 10px; min-height:68px;}
        .fnx-kpi-value {font-size:1.12rem;}
                .fnx-dashboard-gap {height:8px;}
        .fnx-section-title {
          color:#174B2A; font-size:.82rem; font-weight:800;
          margin:5px 0 7px; padding-bottom:5px;
          border-bottom:1px solid #DDE8DE;
        }
        [data-testid="stDataFrame"] {font-size:.68rem !important;}
        .fnx-pill {
          display:inline-block; padding:4px 9px; border-radius:30px;
          background:#EAF5E9; color:#1B6633; font-size:.72rem; font-weight:750;
        }
        hr {border-color:#E1E9E1 !important; margin:.75rem 0 !important;}
        div[data-testid="stDataFrame"] {box-shadow:0 2px 9px rgba(20,65,35,.045);}
        /* FINAL COMPACT TYPOGRAPHY OVERRIDE: this style is injected after app.py CSS */
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stAppViewContainer"] .main p,
        [data-testid="stAppViewContainer"] .main li,
        [data-testid="stAppViewContainer"] .main span,
        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main small,
        [data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"],
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] {
          font-size:.68rem !important; line-height:1.35 !important;
        }
        [data-testid="stAppViewContainer"] .main h1 {font-size:.98rem !important; line-height:1.2 !important;}
        [data-testid="stAppViewContainer"] .main h2 {font-size:.82rem !important; line-height:1.2 !important;}
        [data-testid="stAppViewContainer"] .main h3 {font-size:.74rem !important; line-height:1.2 !important;}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {font-size:.68rem !important;}
        .fnx-kpi-label {font-size:.64rem !important;}
        .fnx-kpi-value {font-size:.90rem !important;}
        .fnx-kpi-detail {font-size:.60rem !important;}
        .fnx-section-title {font-size:.76rem !important;}
        .fnx-status-chip, .fnx-pill {font-size:.64rem !important;}
        [data-testid="stTabs"] button[role="tab"] {font-size:.66rem !important; padding:6px 10px !important;}
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {font-size:.86rem !important;}
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {font-size:.60rem !important;}
        div[data-testid="stDataFrame"] *, div[data-testid="stTable"] * {font-size:.62rem !important;}
        .stButton button, .stFormSubmitButton button, .stDownloadButton button {font-size:.66rem !important;}
        .stTextInput label, .stNumberInput label, .stSelectbox label,
        .stDateInput label, .stTextArea label, .stCheckbox label,
        .stRadio label, .stMultiSelect label, .stSlider label {font-size:.64rem !important;}
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea, [data-baseweb="select"] {font-size:.68rem !important;}
        @media (max-width: 900px) {
          .block-container {padding-left:1rem !important; padding-right:1rem !important;}
          [data-testid="stSidebar"] {min-width:0 !important; max-width:none !important;}
          [data-testid="stAppViewContainer"] .main h1 {font-size:.98rem !important;}
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
                "Résultat": f'{_text(row.get("risk_level", ""))} — {_text(row.get("risk_score", ""))}',
            })
    if not research.empty:
        for _, row in research.tail(12).iterrows():
            records.append({
                "Date": _text(row.get("analysis_date", row.get("created_at", ""))),
                "Type": "Observation de recherche",
                "Lot": _text(row.get("batch_id", "")),
                "Produit": _text(row.get("product_name", "")),
                "Résultat": "Observation enregistrée",
            })
    if not records:
        st.info("Aucune activité enregistrée pour le moment.")
        return
    frame = pd.DataFrame(records)
    frame["_date"] = pd.to_datetime(frame["Date"], errors="coerce", utc=True)
    frame = frame.sort_values("_date", ascending=False, na_position="last").drop(columns="_date")
    st.dataframe(frame.head(10), use_container_width=True, hide_index=True)



def _render_donut(labels, values):
    """Render the reference-style green/red doughnut chart."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.bar_chart(pd.DataFrame({"Value": values}, index=labels), color="#2E7D32")
        return

    total = sum(values)
    if total <= 0:
        st.info("Aucune donnée de conformité disponible.")
        return

    fig, ax = plt.subplots(figsize=(4.2, 2.8), dpi=130)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    colors = ["#14532D", "#B91C1C", "#D9E8D9"]
    actual_labels = [label for label, value in zip(labels, values) if value > 0]
    actual_values = [value for value in values if value > 0]
    actual_colors = [color for color, value in zip(colors, values) if value > 0]
    ax.pie(
        actual_values,
        colors=actual_colors,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.30, "edgecolor": "white", "linewidth": 2},
    )
    ax.text(0, 0, f"{(values[0] / total) * 100:.0f}%",
            ha="center", va="center", fontsize=13, fontweight="bold",
            color="#173B24")
    ax.legend(
        [f"{label} ({value})" for label, value in zip(actual_labels, actual_values)],
        loc="lower center", bbox_to_anchor=(0.5, -0.16),
        ncol=max(1, min(2, len(actual_labels))), frameon=False,
        fontsize=7, labelcolor="#26352A",
    )
    ax.set_aspect("equal")
    fig.tight_layout(pad=0.6)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def _render_category_bars(series):
    """Render compact green horizontal category bars."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.bar_chart(series.sort_values(ascending=True).tail(7), color="#2E7D32")
        return

    series = series.sort_values(ascending=True).tail(7)
    if series.empty:
        return
    fig, ax = plt.subplots(figsize=(6.0, 2.8), dpi=130)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    colors = ["#9BCB8D", "#79B96C", "#5DA957", "#3D9146", "#176B35", "#14532D", "#0F4528"]
    bars = ax.barh(series.index.astype(str), series.values, color=colors[-len(series):], height=0.62)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#DDE8DE")
    ax.tick_params(axis="y", labelsize=7, length=0, colors="#26352A")
    ax.tick_params(axis="x", labelsize=6, colors="#657468")
    ax.grid(axis="x", color="#E8EEE8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.bar_label(bars, padding=2, fontsize=7, color="#26352A")
    fig.tight_layout(pad=0.8)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)



def render_dashboard(history_data=None, research_data=None, quality_report=None, pipeline_status=None):
    """FOODNEXA dashboard arranged like the user's reference image."""
    _install_dashboard_style()

    history = _df(history_data)
    research = _df(research_data)

    risk_col = _column(history, ["risk_level"])
    risk_score_col = _column(history, ["risk_score"])
    levels = history[risk_col].map(_risk_label) if risk_col else pd.Series(dtype="object")

    low = int((levels == "Faible").sum())
    moderate = int((levels == "Modéré").sum())
    high = int((levels == "Élevé").sum())

    score = _quality_score(quality_report)
    score_text = f"{score:.1f}%" if score is not None else "N/D"
    scores = _number_series(history, ["risk_score"])
    average = f"{scores.mean():.1f}/100" if not scores.empty else "N/D"

    # Dashboard title
    st.title("Dashboard")
    st.caption("Monitoring agro-food quality, food safety risks and research data")

    # Four KPI cards on one line
    kpis = st.columns(4, gap="medium")
    with kpis[0]:
        _card("Total Analyses", len(history), "Risk assessments", "green", "✓")
    with kpis[1]:
        _card("Research Observations", len(research), "Scientific records", "green", "▤")
    with kpis[2]:
        _card("High Risk", high, "Requires attention", "red", "!")
    with kpis[3]:
        _card("Data Quality", score_text, "Dataset quality score", "green", "◉")

    st.markdown('<div class="fnx-dashboard-gap"></div>', unsafe_allow_html=True)

    # Main dashboard: left analytics, right activity/history
    left, right = st.columns([0.88, 1.62], gap="medium")

    with left:
        st.markdown('<div class="fnx-section-title">Conformity Rate</div>', unsafe_allow_html=True)
        if not history.empty and risk_col:
            # Low risk is separated from moderate/high risk.
            # This is a risk indicator, not a regulatory conformity decision.
            _render_donut(
                ["Low Risk", "Moderate / High Risk"],
                [low, moderate + high],
            )
        else:
            st.info("Aucune évaluation disponible.")

        st.markdown('<div class="fnx-section-title">Analyses by Product Category</div>', unsafe_allow_html=True)
        category_col = _column(research, ["product_category", "product_name"])
        if category_col and not research.empty:
            categories = (
                research[category_col].map(_text)
                .replace("", pd.NA).dropna().value_counts()
            )
            if not categories.empty:
                _render_category_bars(categories)
            else:
                st.caption("Aucune catégorie renseignée.")
        else:
            st.caption("Les catégories apparaîtront après l'enregistrement des observations.")

        st.caption(
            "Répartition circulaire des niveaux de risque. "
            "Les catégories ne constituent pas une décision réglementaire de conformité."
        )

    with right:
        st.markdown('<div class="fnx-section-title">Recent Activity</div>', unsafe_allow_html=True)
        activity = []
        if not history.empty:
            for _, row in history.tail(8).iterrows():
                activity.append({
                    "Date": _text(row.get("analysis_date", row.get("created_at", ""))),
                    "Sample ID": _text(row.get("batch_id", "")),
                    "Product": _text(row.get("product_name", "")),
                    "Result": _text(row.get("risk_level", "")),
                })
        if not research.empty:
            for _, row in research.tail(8).iterrows():
                activity.append({
                    "Date": _text(row.get("analysis_date", row.get("created_at", ""))),
                    "Sample ID": _text(row.get("batch_id", "")),
                    "Product": _text(row.get("product_name", "")),
                    "Result": "Research observation",
                })
        if activity:
            activity_df = pd.DataFrame(activity)
            activity_df["_sort"] = pd.to_datetime(activity_df["Date"], errors="coerce", utc=True)
            activity_df = activity_df.sort_values("_sort", ascending=False, na_position="last").drop(columns="_sort")
            st.dataframe(activity_df.head(6), use_container_width=True, hide_index=True, height=210)
        else:
            st.info("Aucune activité récente.")

        st.markdown('<div class="fnx-section-title">Analysis History</div>', unsafe_allow_html=True)
        if not history.empty:
            history_rows = []
            for _, row in history.tail(7).iloc[::-1].iterrows():
                history_rows.append({
                    "Date": _text(row.get("analysis_date", "")),
                    "Sample ID": _text(row.get("batch_id", "")),
                    "Product": _text(row.get("product_name", "")),
                    "Analyst": _text(row.get("analyst", row.get("analyst_name", "—"))) or "—",
                    "Result": _text(row.get("risk_level", "")),
                })
            st.dataframe(
                pd.DataFrame(history_rows),
                use_container_width=True,
                hide_index=True,
                height=245,
            )
        else:
            st.info("Aucun historique disponible.")

    # Less frequently used technical details remain accessible without
    # pushing the main dashboard below the fold.
    with st.expander("Data Quality & System Status", expanded=False):
        q1, q2, q3 = st.columns(3)
        q1.metric("Quality Score", score_text)
        q2.metric("Research Observations", len(research))
        q3.metric("Exact Duplicates", _safe_duplicates(research))

        issues = _engine_issues(quality_report)
        if issues:
            st.markdown("**Quality issues to review**")
            st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
        elif research.empty:
            st.info("En attente de données pour le contrôle qualité.")
        else:
            st.success("Aucune anomalie signalée par le rapport qualité.")

        if isinstance(pipeline_status, dict) and pipeline_status:
            st.markdown("**FOODNEXA System Pipeline**")
            for name, status in pipeline_status.items():
                if status is True:
                    st.success(f"{name} — Disponible")
                elif status is False:
                    st.warning(f"{name} — Indisponible")
                else:
                    st.info(f"{name} — Statut non confirmé")

    st.caption(
        "FOODNEXA est un prototype expérimental de Food Safety Risk Intelligence. "
        "Les indicateurs ne remplacent pas les analyses de laboratoire, "
        "l'expertise scientifique ou les exigences réglementaires applicables."
    )
