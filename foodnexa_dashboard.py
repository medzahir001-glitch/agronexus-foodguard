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
          <div class="fnx-kpi-label">{html.escape(str(icon))} {html.escape(str(label))}</div>
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
          --fnx-navy:#124B27; --fnx-blue:#1D6536; --fnx-teal:#258A4A;
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
          padding:1.35rem 2rem 2rem !important;
        }
        [data-testid="stMainBlockContainer"] {
          width:100% !important; max-width:none !important;
        }
        [data-testid="stSidebar"] {
          min-width:250px !important; max-width:250px !important;
        }
        [data-testid="stSidebar"] {
          background:#124B27 !important;
          border-right:1px solid #DDE8DE !important;
        }
        [data-testid="stSidebar"] * {color:#FFFFFF !important;}
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
          background:rgba(255,255,255,.07); border-radius:8px;
          padding:7px 10px; margin:2px 0;
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
          color:#14532D !important; font-size:2.05rem !important;
          font-weight:850 !important; letter-spacing:-1.1px !important;
          margin-bottom:.15rem !important;
        }
        [data-testid="stAppViewContainer"] .main h2 {
          color:#174B2A !important; font-size:1.02rem !important;
          font-weight:800 !important;
        }
        [data-testid="stAppViewContainer"] .main h3 {
          color:#236B3A !important; font-size:0.88rem !important;
          font-weight:750 !important;
        }
        [data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] p {
          color:#526357 !important;
        }
        .fnx-kpi {
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-radius:12px; padding:13px 15px; min-height:96px;
          box-shadow:0 4px 14px rgba(20,65,35,.07); margin-bottom:12px;
        }
        .fnx-kpi-label {font-size:.70rem; color:#536357; font-weight:700;}
        .fnx-kpi-value {font-size:1.42rem; line-height:1.25; color:#14532D; font-weight:850;}
        .fnx-kpi-detail {font-size:.66rem; color:#718075; margin-top:3px;}
        .fnx-section {
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-radius:12px; padding:12px 14px; margin:6px 0 11px;
          box-shadow:0 2px 10px rgba(20,65,35,.045);
        }
        .fnx-section-title {font-size:.94rem; color:#174B2A; font-weight:800; margin-bottom:8px;}
        div[data-testid="stDataFrame"] {
          background:#FFFFFF !important; border:1px solid var(--fnx-border) !important;
          border-radius:10px !important; overflow:hidden !important;
        }
        div[data-testid="stDataFrame"] * {color:#203648 !important;}
        [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"],
        [data-testid="stPyplotChart"] {background:#FFFFFF !important;}
        div[data-testid="stMetric"] {
          background:#FFFFFF !important; border:1px solid var(--fnx-border) !important;
          border-left:4px solid #2F8F46 !important; border-radius:12px !important;
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
          background:#E8F3E8; color:#14532D;
          border-bottom:3px solid #238442;
        }
        .fnx-kpi {padding:12px 14px; min-height:88px;}
        .fnx-kpi-value {font-size:1.7rem;}
                .fnx-pill {
          display:inline-block; padding:4px 9px; border-radius:30px;
          background:#EAF5E9; color:#1B6633; font-size:.72rem; font-weight:750;
        }
        hr {border-color:#E1E9E1 !important; margin:.75rem 0 !important;}
        div[data-testid="stDataFrame"] {box-shadow:0 2px 9px rgba(20,65,35,.045);}
        @media (max-width: 900px) {
          .block-container {padding-left:1rem !important; padding-right:1rem !important;}
          [data-testid="stSidebar"] {min-width:0 !important; max-width:none !important;}
          [data-testid="stAppViewContainer"] .main h1 {font-size:1.9rem !important;}
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
        st.bar_chart(pd.DataFrame({"Value": values}, index=labels), color="#238442")
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
            ha="center", va="center", fontsize=17, fontweight="bold",
            color="#173B24")
    ax.legend(
        [f"{label} ({value})" for label, value in zip(actual_labels, actual_values)],
        loc="lower center", bbox_to_anchor=(0.5, -0.16),
        ncol=max(1, min(2, len(actual_labels))), frameon=False,
        fontsize=8, labelcolor="#26352A",
    )
    ax.set_aspect("equal")
    fig.tight_layout(pad=0.6)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _render_category_bars(series):
    """Render compact green horizontal category bars."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.bar_chart(series.sort_values(ascending=True).tail(7), color="#238442")
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
    ax.tick_params(axis="y", labelsize=8, length=0, colors="#26352A")
    ax.tick_params(axis="x", labelsize=7, colors="#657468")
    ax.grid(axis="x", color="#E8EEE8", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.bar_label(bars, padding=3, fontsize=8, color="#26352A")
    fig.tight_layout(pad=0.8)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_dashboard(history_data=None, research_data=None, quality_report=None, pipeline_status=None):
    """Render a compact, green-and-white enterprise dashboard.

    The first screen contains the main KPIs and operational overview.
    Detailed quality and activity information is grouped into tabs to
    reduce vertical scrolling without hiding or deleting any information.
    """
    _install_dashboard_style()

    history = _df(history_data)
    research = _df(research_data)

    risk_col = _column(history, ["risk_level"])
    risk_score_col = _column(history, ["risk_score"])
    levels = history[risk_col].map(_risk_label) if risk_col else pd.Series(dtype="object")
    high = int((levels == "Élevé").sum())
    moderate = int((levels == "Modéré").sum())
    low = int((levels == "Faible").sum())
    scores = _number_series(history, ["risk_score"])
    average = f"{scores.mean():.1f}/100" if not scores.empty else "N/D"
    score = _quality_score(quality_report)
    score_text = f"{score:.1f}%" if score is not None else "N/D"

    # Compact page heading
    head_left, head_right = st.columns([3, 1])
    with head_left:
        st.title("FOODNEXA Dashboard")
        st.caption("FOOD SAFETY  •  RISK INTELLIGENCE  •  RESEARCH DATA")
    with head_right:
        st.markdown(
            '<div class="fnx-status-chip">● SYSTEM OVERVIEW</div>',
            unsafe_allow_html=True,
        )

    # Four KPI cards, all on one row on desktop
    kpis = st.columns(4, gap="medium")
    with kpis[0]:
        _card("Total Risk Assessments", len(history), "Évaluations enregistrées", "green", "✓")
    with kpis[1]:
        _card("Research Observations", len(research), "Observations scientifiques", "green", "▤")
    with kpis[2]:
        _card("High Risk", high, "Évaluations à risque élevé", "red", "!")
    with kpis[3]:
        _card("Dataset Quality", score_text, "Qualité documentaire", "navy", "◉")

    # Main content is grouped into tabs: no long stack of sections.
    tab_overview, tab_quality, tab_activity = st.tabs([
        "  Overview  ", "  Data Quality  ", "  Activity & Pipeline  "
    ])

    with tab_overview:
        left, right = st.columns([1.05, 1], gap="large")
        with left:
            st.subheader("Risk Intelligence")
            risk_a, risk_b = st.columns(2)
            risk_a.metric("Moderate Risk", moderate)
            risk_b.metric("Average Risk Score", average)
            st.markdown("**Risk Distribution**")
            if not history.empty and risk_col:
                _render_donut(
                    ["Low Risk", "High Risk", "Moderate Risk"],
                    [low, high, moderate],
                )
            else:
                st.info("Aucune évaluation de risque disponible.")
            st.markdown("**Risk score evolution**")
            if not history.empty and risk_score_col:
                batch_col = _column(history, ["batch_id"])
                values = pd.to_numeric(history[risk_score_col], errors="coerce")
                if batch_col:
                    chart = pd.DataFrame({
                        "Lot": history[batch_col].map(_text),
                        "Risk Score": values,
                    })
                    chart = chart[(chart["Lot"] != "") & chart["Risk Score"].notna()].tail(15)
                    if not chart.empty:
                        chart["Assessment"] = [f"#{i+1}" for i in range(len(chart))]
                        st.line_chart(
                            chart.set_index("Assessment")[["Risk Score"]],
                            color="#238442",
                            height=190,
                        )
                    else:
                        st.caption("Aucun Risk Score numérique disponible.")
                else:
                    st.caption("Identifiants des lots indisponibles.")
            else:
                st.caption("Les données d'évolution ne sont pas encore disponibles.")

        with right:
            st.subheader("Research Dataset")
            m1, m2, m3 = st.columns(3)
            m1.metric("Observations", len(research))
            m2.metric("Products", _unique_count(research, ["product_name"]))
            m3.metric("Batches", _unique_count(research, ["batch_id"]))
            category_col = _column(research, ["product_category"])
            if category_col and not research.empty:
                categories = research[category_col].map(_text).replace("", pd.NA).dropna().value_counts()
                if not categories.empty:
                    st.markdown("**Observations by product category**")
                    _render_category_bars(categories)
            elif research.empty:
                st.info("Le Research Dataset ne contient pas encore d'observations.")
            else:
                st.caption("La catégorie produit n'est pas renseignée.")

            st.markdown("**Latest records**")
            recent = []
            if not history.empty:
                for _, row in history.tail(5).iterrows():
                    recent.append({
                        "Date": _text(row.get("analysis_date", "")),
                        "Lot": _text(row.get("batch_id", "")),
                        "Product": _text(row.get("product_name", "")),
                        "Result": _text(row.get("risk_level", "")),
                    })
            if recent:
                st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)
            else:
                st.caption("Aucune activité récente à afficher.")

    with tab_quality:
        quality_issues = _engine_issues(quality_report)
        if not research.empty:
            for field, label in [("batch_id", "Identifiant du lot"), ("product_name", "Nom du produit")]:
                col = _column(research, [field])
                missing_count = len(research) if col is None else int(research[col].map(_missing).sum())
                if missing_count:
                    quality_issues.append({
                        "Ligne": "—", "Champ": field,
                        "Anomalie": f"{label} manquant",
                        "Niveau": "À vérifier",
                    })

        duplicate_count = _safe_duplicates(research)
        q1, q2, q3 = st.columns(3)
        with q1:
            _card("Quality Score", score_text, "Indicateur documentaire", "green", "✓")
        with q2:
            _card("Quality Issues", len(quality_issues), "Signaux à examiner", "amber", "!")
        with q3:
            _card("Exact Duplicates", duplicate_count, "Détection non destructive", "blue", "↔")

        coverage = {}
        if isinstance(quality_report, dict):
            coverage = quality_report.get("coverage", {}) or {}
        trace = coverage.get("Traçabilité") if isinstance(coverage, dict) else None

        if isinstance(trace, dict):
            st.markdown("**Traceability**")
            t1, t2 = st.columns([1, 3])
            with t1:
                st.metric("Completeness", f'{trace.get("percent", 0):.1f}%')
            with t2:
                percent = float(trace.get("percent", 0) or 0)
                st.progress(min(max(percent / 100, 0), 1))
                st.caption(
                    f'{trace.get("available", 0)} champs renseignés sur '
                    f'{trace.get("possible", 0)} valeurs attendues.'
                )

        domain_coverage = coverage.get("Analyses par domaine", {}) if isinstance(coverage, dict) else {}
        if isinstance(domain_coverage, dict) and domain_coverage:
            st.markdown("**Scientific analysis coverage**")
            rows = []
            for domain, detail in domain_coverage.items():
                if isinstance(detail, dict):
                    rows.append({
                        "Domaine": domain,
                        "Valeurs renseignées": detail.get("available", 0),
                        "Valeurs attendues": detail.get("possible", 0),
                        "Couverture (%)": detail.get("percent", 0),
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if quality_issues:
            st.warning(f"{len(quality_issues)} signalement(s) à examiner.")
            st.dataframe(
                pd.DataFrame(quality_issues).drop_duplicates(),
                use_container_width=True,
                hide_index=True,
            )
        elif research.empty:
            st.info("En attente de données pour le contrôle qualité.")
        else:
            st.success("Aucune anomalie détectée par les contrôles affichés.")

        st.caption(
            "Les indicateurs décrivent la qualité documentaire et technique du dataset. "
            "Ils ne constituent pas une décision de conformité réglementaire."
        )

    with tab_activity:
        activity_col, pipeline_col = st.columns([1.2, 1], gap="large")
        with activity_col:
            st.subheader("Recent Activity")
            _render_activity(history, research)
        with pipeline_col:
            st.subheader("FOODNEXA System Pipeline")
            pipeline = {
                "Risk Assessment Engine": True,
                "Research Dataset": not research.empty,
                "Data Quality Engine": quality_report is not None,
                "Scientific Data Cleaning": None,
                "Research Analytics": not research.empty,
                "Supabase": None,
            }
            if isinstance(pipeline_status, dict):
                pipeline.update(pipeline_status)
            for name, status in pipeline.items():
                if status is True:
                    st.success(f"{name} — Disponible")
                elif status is False:
                    st.warning(f"{name} — Données absentes / indisponible")
                else:
                    st.info(f"{name} — Statut non confirmé")

    st.caption(
        "FOODNEXA est un prototype expérimental de Food Safety Risk Intelligence. "
        "Les indicateurs soutiennent la recherche exploratoire et ne remplacent "
        "pas les analyses de laboratoire, les modèles validés, l'expertise "
        "scientifique ou les exigences réglementaires applicables."
    )
