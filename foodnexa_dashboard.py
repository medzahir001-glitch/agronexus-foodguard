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
          --fnx-navy:#123451; --fnx-blue:#087D9C; --fnx-teal:#0B8F98;
          --fnx-green:#15966F; --fnx-ink:#182B3A; --fnx-muted:#647789;
          --fnx-border:#DCE7EE; --fnx-bg:#F7FAFC;
        }
        [data-testid="stAppViewContainer"], [data-testid="stMain"],
        [data-testid="stMainBlockContainer"], .main, .block-container {
          background:#FFFFFF !important;
        }
        .block-container {max-width:1280px !important; padding:0.65rem 1.5rem 1.5rem !important;}
        [data-testid="stAppViewContainer"] .main p,
        [data-testid="stAppViewContainer"] .main li,
        [data-testid="stAppViewContainer"] .main label,
        [data-testid="stAppViewContainer"] .main span {
          color:var(--fnx-ink);
        }
        [data-testid="stAppViewContainer"] .main h1 {
          color:var(--fnx-navy) !important; font-size:1.28rem !important;
          font-weight:850 !important;
        }
        [data-testid="stAppViewContainer"] .main h2 {
          color:var(--fnx-blue) !important; font-size:0.98rem !important;
          font-weight:800 !important;
        }
        [data-testid="stAppViewContainer"] .main h3 {
          color:var(--fnx-green) !important; font-size:0.86rem !important;
          font-weight:750 !important;
        }
        .fnx-kpi {
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-radius:10px; padding:10px 12px; min-height:82px;
          box-shadow:0 3px 12px rgba(18,52,81,.06); margin-bottom:12px;
        }
        .fnx-kpi-label {font-size:.72rem; color:#526779; font-weight:700;}
        .fnx-kpi-value {font-size:1.25rem; line-height:1.25; color:var(--fnx-navy); font-weight:850;}
        .fnx-kpi-detail {font-size:.72rem; color:#718395; margin-top:2px;}
        .fnx-section {
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-radius:11px; padding:11px 13px; margin:6px 0 11px;
          box-shadow:0 2px 9px rgba(18,52,81,.035);
        }
        .fnx-section-title {font-size:.88rem; color:var(--fnx-navy); font-weight:800; margin-bottom:8px;}
        div[data-testid="stDataFrame"] {
          background:#FFFFFF !important; border:1px solid var(--fnx-border) !important;
          border-radius:10px !important; overflow:hidden !important;
        }
        div[data-testid="stDataFrame"] * {color:#203648 !important;}
        [data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"],
        [data-testid="stPyplotChart"] {background:#FFFFFF !important;}
        div[data-testid="stMetric"] {
          background:#FFFFFF !important; border:1px solid var(--fnx-border) !important;
          border-left:4px solid var(--fnx-green) !important; border-radius:12px !important;
          box-shadow:0 2px 8px rgba(18,52,81,.05) !important;
        }
        div[data-testid="stMetric"] * {color:var(--fnx-navy) !important;}
        .fnx-pill {
          display:inline-block; padding:4px 9px; border-radius:30px;
          background:#EAF6F4; color:#087B63; font-size:.72rem; font-weight:750;
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


def render_dashboard(history_data=None, research_data=None, quality_report=None, pipeline_status=None):
    _install_dashboard_style()

    history = _df(history_data)
    research = _df(research_data)

    st.title("FOODNEXA Intelligence Dashboard")
    st.caption("FOOD SAFETY  •  RISK INTELLIGENCE  •  RESEARCH DATA MONITORING")
    st.write("Vue consolidée des évaluations expérimentales, des observations scientifiques et de la qualité des données.")
    st.divider()

    # KPIs
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

    st.subheader("Executive Overview")
    row1 = st.columns(3)
    with row1[0]:
        _card("Risk Assessments", len(history), "Évaluations enregistrées", "blue", "🛡️")
    with row1[1]:
        _card("Research Observations", len(research), "Observations scientifiques", "green", "🧪")
    with row1[2]:
        _card("Dataset Quality Score", score_text, "Qualité documentaire et technique", "navy", "◉")
    row2 = st.columns(3)
    with row2[0]:
        _card("High Risk", high, "Évaluations classées élevées", "red", "!")
    with row2[1]:
        _card("Moderate Risk", moderate, "Évaluations modérées", "amber", "◈")
    with row2[2]:
        _card("Average Risk Score", average, "Score expérimental moyen", "blue", "▥")

    st.divider()

    # Risk and dataset
    left, right = st.columns([1.05, 1])
    with left:
        st.subheader("Risk Intelligence Monitoring")
        st.markdown("**Risk Level Distribution**")
        if not history.empty and risk_col:
            chart = pd.DataFrame({
                "Niveau de risque": ["Faible", "Modéré", "Élevé"],
                "Nombre": [low, moderate, high],
            }).set_index("Niveau de risque")
            st.bar_chart(chart, horizontal=True, color="#0B8F98")
        else:
            st.info("Aucune évaluation de risque disponible.")
        st.markdown("**Risk Score Evolution**")
        if not history.empty and risk_score_col:
            batch_col = _column(history, ["batch_id"])
            values = pd.to_numeric(history[risk_score_col], errors="coerce")
            if batch_col:
                chart = pd.DataFrame({
                    "Lot": history[batch_col].map(_text),
                    "Risk Score": values,
                })
                chart = chart[(chart["Lot"] != "") & chart["Risk Score"].notna()].tail(30)
                if not chart.empty:
                    chart["Évaluation"] = [f"#{i+1}" for i in range(len(chart))]
                    st.line_chart(chart.set_index("Évaluation")[["Risk Score"]], color="#087D9C")
                else:
                    st.info("Aucun Risk Score numérique disponible.")
            else:
                st.info("Identifiants des lots indisponibles.")
        else:
            st.info("Les données d'évolution ne sont pas encore disponibles.")

    with right:
        st.subheader("Research Dataset Overview")
        a, b, c = st.columns(3)
        a.metric("Observations", len(research))
        b.metric("Produits distincts", _unique_count(research, ["product_name"]))
        c.metric("Lots distincts", _unique_count(research, ["batch_id"]))
        category_col = _column(research, ["product_category"])
        if category_col and not research.empty:
            categories = research[category_col].map(_text).replace("", pd.NA).dropna().value_counts()
            if not categories.empty:
                st.markdown("**Observations par catégorie de produit**")
                st.bar_chart(categories.rename_axis("Catégorie").to_frame("Observations"), horizontal=True, color="#15966F")
        elif research.empty:
            st.info("Le Research Dataset ne contient pas encore d'observations.")
        else:
            st.caption("La catégorie produit n'est pas renseignée dans les observations disponibles.")

    st.divider()

    # Data quality
    st.subheader("Data Quality Monitoring")
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
        if duplicate_count:
            quality_issues.append({
                "Ligne": "—", "Champ": "Enregistrement",
                "Anomalie": "Doublons exacts détectés",
                "Niveau": "À vérifier",
            })

    trace = None
    coverage = {}
    if isinstance(quality_report, dict):
        coverage = quality_report.get("coverage", {}) or {}
        trace = coverage.get("Traçabilité") if isinstance(coverage, dict) else None

    q1, q2, q3 = st.columns(3)
    with q1:
        _card("Quality Score", score_text, "Indicateur documentaire", "green", "✓")
    with q2:
        _card("Quality Issues", len(quality_issues), "Signaux à examiner", "amber", "!")
    with q3:
        _card("Exact Duplicates", _safe_duplicates(research), "Détection non destructive", "blue", "↔")

    if trace and isinstance(trace, dict):
        st.markdown("**Traçabilité**")
        t1, t2 = st.columns([1, 3])
        with t1:
            st.metric("Complétude", f'{trace.get("percent", 0):.1f}%')
        with t2:
            st.progress(min(max(float(trace.get("percent", 0)) / 100, 0), 1))
            st.caption(f'{trace.get("available", 0)} champs renseignés sur {trace.get("possible", 0)} valeurs attendues.')

    domain_coverage = coverage.get("Analyses par domaine", {}) if isinstance(coverage, dict) else {}
    if isinstance(domain_coverage, dict) and domain_coverage:
        st.markdown("**Couverture analytique par domaine scientifique**")
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
        st.dataframe(pd.DataFrame(quality_issues).drop_duplicates(), use_container_width=True, hide_index=True)
    elif research.empty:
        st.info("En attente de données pour le contrôle qualité.")
    else:
        st.success("Aucune anomalie détectée par les contrôles affichés.")

    st.caption("Les indicateurs décrivent la qualité documentaire et technique du dataset. Ils ne constituent pas une décision de conformité réglementaire ni une preuve d'innocuité alimentaire.")

    st.divider()

    # Activity and pipeline
    activity_col, pipeline_col = st.columns([1.25, 1])
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

    st.divider()
    st.caption(
        "FOODNEXA est un prototype expérimental de Food Safety Risk Intelligence. "
        "Les indicateurs soutiennent la recherche exploratoire et ne remplacent "
        "pas les analyses de laboratoire, les modèles validés, l'expertise "
        "scientifique ou les exigences réglementaires applicables."
    )
