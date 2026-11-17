import html
import json
import math
import textwrap
import pandas as pd
import streamlit as st


# ============================================================
# FOODNEXA — ENTERPRISE FOOD SAFETY DASHBOARD
# Compatible with app.py render_dashboard(...) signature.
# Read-only rendering: this module does not modify source data.
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
        return value.strip().casefold() in {"", "nan", "none", "null", "n/a", "nat"}
    if isinstance(value, (dict, list, tuple, set)):
        return len(value) == 0
    try:
        result = pd.isna(value)
        if getattr(result, "ndim", 0) == 0:
            return bool(result)
    except (TypeError, ValueError):
        pass
    return False


def _text(value, default="—"):
    if _missing(value):
        return default
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)
    return str(value).strip()


def _column(frame, names):
    if frame.empty:
        return None
    lookup = {str(col).strip().casefold(): col for col in frame.columns}
    for name in names:
        if name.casefold() in lookup:
            return lookup[name.casefold()]
    return None


def _value(row, names, default="—"):
    for name in names:
        if name in row.index and not _missing(row[name]):
            return _text(row[name], default)
    return default


def _risk_label(value):
    raw = _text(value, "").casefold()
    mapping = {
        "faible": "Faible", "low": "Faible",
        "modéré": "Modéré", "modere": "Modéré",
        "moderate": "Modéré", "medium": "Modéré",
        "élevé": "Élevé", "eleve": "Élevé", "high": "Élevé",
    }
    return mapping.get(raw, _text(value, "—"))


def _quality_score(report):
    if not isinstance(report, dict):
        return None
    for key in ("quality_score", "overall_score", "score", "quality_percentage"):
        try:
            value = float(report.get(key))
            if math.isfinite(value):
                if 0 <= value <= 1:
                    value *= 100
                return max(0.0, min(100.0, value))
        except (TypeError, ValueError):
            continue
    return None


def _safe_duplicates(frame):
    if frame.empty:
        return 0
    seen = set()
    duplicates = 0
    for row in frame.itertuples(index=False, name=None):
        normalized = tuple(
            json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
            if isinstance(value, (dict, list, tuple))
            else (None if _missing(value) else str(value))
            for value in row
        )
        if normalized in seen:
            duplicates += 1
        else:
            seen.add(normalized)
    return duplicates


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
                    item.get("issue", item.get("message", item.get("type", "À vérifier"))),
                ),
                "Niveau": item.get(
                    "Niveau",
                    item.get("priority", item.get("severity", "À vérifier")),
                ),
            })
        else:
            output.append({"Ligne": "—", "Champ": "—", "Anomalie": str(item), "Niveau": "À vérifier"})
    return output


def _status_class(value):
    raw = _text(value, "").casefold()
    if any(token in raw for token in ("élevé", "eleve", "high", "risk")):
        return "danger"
    if any(token in raw for token in ("modéré", "modere", "moderate", "medium")):
        return "warning"
    if any(token in raw for token in ("faible", "low", "conforme", "success")):
        return "success"
    if "research" in raw or "observation" in raw:
        return "info"
    return "neutral"


def _pill(value):
    safe = html.escape(_text(value))
    return f'<span class="fnx-pill fnx-pill-{_status_class(value)}">{safe}</span>'


def _kpi_card(label, value, detail, icon, accent="green"):
    accents = {
        "green": ("#16834A", "#E5F7EC"),
        "red": ("#D92D20", "#FDECEC"),
        "teal": ("#187A70", "#E5F5F2"),
    }
    color, soft = accents.get(accent, accents["green"])
    return f"""
    <article class="fnx-kpi-card" style="--kpi-accent:{color};--kpi-soft:{soft}">
      <div class="fnx-kpi-copy">
        <div class="fnx-kpi-label">{html.escape(label)}</div>
        <div class="fnx-kpi-value">{html.escape(str(value))}</div>
        <div class="fnx-kpi-detail">{html.escape(detail)}</div>
      </div>
      <div class="fnx-kpi-icon">{html.escape(icon)}</div>
    </article>
    """


def _table_html(headers, rows, result_column=None):
    header_html = "".join(f"<th>{html.escape(str(item))}</th>" for item in headers)
    row_html = []
    for row in rows:
        cells = []
        for index, key in enumerate(headers):
            value = row.get(key, "—")
            if key == result_column:
                cell = _pill(value)
            else:
                cell = html.escape(_text(value))
            cells.append(f"<td>{cell}</td>")
        row_html.append("<tr>" + "".join(cells) + "</tr>")
    if not row_html:
        row_html = [f'<tr><td class="fnx-empty-row" colspan="{len(headers)}">No records available yet</td></tr>']
    return f"""
    <div class="fnx-table-scroll">
      <table class="fnx-table"><thead><tr>{header_html}</tr></thead>
      <tbody>{''.join(row_html)}</tbody></table>
    </div>
    """


def _make_activity(history, research):
    records = []
    for _, row in history.iterrows():
        records.append({
            "Date": _value(row, ["analysis_date", "created_at", "date"]),
            "Sample ID": _value(row, ["batch_id", "sample_id", "sample_ref"]),
            "Product": _value(row, ["product_name", "product"]),
            "Result": _risk_label(_value(row, ["risk_level", "expert_risk_label"], "—")),
            "_kind": "analysis",
        })
    for _, row in research.iterrows():
        records.append({
            "Date": _value(row, ["analysis_date", "created_at", "sampling_date", "date"]),
            "Sample ID": _value(row, ["batch_id", "sample_id", "sample_ref"]),
            "Product": _value(row, ["product_name", "product"]),
            "Result": "Research observation",
            "_kind": "research",
        })
    if not records:
        return []
    frame = pd.DataFrame(records)
    frame["_sort"] = pd.to_datetime(frame["Date"].replace("—", pd.NA), errors="coerce", utc=True)
    frame = frame.sort_values("_sort", ascending=False, na_position="last")
    return frame.head(6).drop(columns="_sort").to_dict(orient="records")


def _make_history(history):
    rows = []
    if history.empty:
        return rows
    for _, row in history.tail(7).iloc[::-1].iterrows():
        rows.append({
            "Date": _value(row, ["analysis_date", "created_at", "date"]),
            "Sample ID": _value(row, ["batch_id", "sample_id", "sample_ref"]),
            "Product": _value(row, ["product_name", "product"]),
            "Analyst": _value(row, ["analyst", "analyst_name", "operator"]),
            "Result": _risk_label(_value(row, ["risk_level", "expert_risk_label"], "—")),
        })
    return rows


def _donut_html(low, other):
    total = low + other
    if total <= 0:
        percent = 0
        label = "No data"
    else:
        percent = round((low / total) * 100)
        label = f"{percent}%"
    safe_percent = max(0, min(100, percent))
    return f"""
    <div class="fnx-donut-area">
      <div class="fnx-donut" style="--low:{safe_percent}%">
        <div class="fnx-donut-center"><strong>{label}</strong><small>Low risk</small></div>
      </div>
      <div class="fnx-legend">
        <span><i class="fnx-legend-dot green"></i>Low Risk <b>({low})</b></span>
        <span><i class="fnx-legend-dot red"></i>Moderate / High Risk <b>({other})</b></span>
      </div>
    </div>
    """


def _category_chart_html(research):
    category_col = _column(research, ["product_category", "category", "product_name"])
    if category_col is None or research.empty:
        return '<div class="fnx-chart-empty">Categories will appear after research observations are recorded.</div>'
    values = research[category_col].map(lambda value: _text(value, "")).replace("", pd.NA).dropna().value_counts().head(6)
    if values.empty:
        return '<div class="fnx-chart-empty">No product category has been entered yet.</div>'
    max_value = max(1, int(values.max()))
    columns = []
    for label, count in values.items():
        height = max(7, int((int(count) / max_value) * 104))
        short_label = str(label)
        if len(short_label) > 16:
            short_label = short_label[:14] + "…"
        columns.append(f"""
        <div class="fnx-bar-column" title="{html.escape(str(label))}: {int(count)}">
          <b class="fnx-bar-value">{int(count)}</b>
          <div class="fnx-bar-track"><div class="fnx-bar" style="height:{height}px"></div></div>
          <span class="fnx-bar-label">{html.escape(short_label)}</span>
        </div>
        """)
    return f'<div class="fnx-category-chart">{"".join(columns)}</div>'


def _install_dashboard_style():
    st.markdown(
        textwrap.dedent(
            """
        <style>
        :root {
          --fnx-deep:#064B32;
          --fnx-green:#12834B;
          --fnx-green-dark:#0B6840;
          --fnx-mint:#E8F6EE;
          --fnx-paper:#F4F8F7;
          --fnx-ink:#172B24;
          --fnx-muted:#6D7E76;
          --fnx-border:#DCE9E2;
          --fnx-danger:#D92D20;
        }
        [data-testid="stAppViewContainer"], [data-testid="stMain"],
        [data-testid="stMainBlockContainer"], .main {
          background:var(--fnx-paper) !important;
        }
        .block-container, [data-testid="stMainBlockContainer"] {
          max-width:none !important;
          width:100% !important;
          padding:1.0rem 1.15rem 1.5rem !important;
        }
        [data-testid="stSidebar"] {
          background:#FFFFFF !important;
          border-right:1px solid var(--fnx-border) !important;
        }
        [data-testid="stSidebar"] * { color:var(--fnx-ink) !important; }
        [data-testid="stDataFrame"] { background:#FFFFFF !important; }
        .fnx-dashboard-wrap { width:100%; color:var(--fnx-ink); }
        .fnx-page-heading {
          display:flex; align-items:center; gap:12px;
          margin:2px 0 4px; color:var(--fnx-deep);
          font-size:21px; line-height:1.15; font-weight:850;
        }
        .fnx-page-heading-icon {
          width:34px; height:34px; border-radius:10px;
          display:grid; place-items:center; flex:0 0 34px;
          color:#FFFFFF; background:linear-gradient(145deg,#169653,#075C3A);
          font-size:18px; box-shadow:0 4px 10px rgba(6,75,50,.15);
        }
        .fnx-page-subtitle { color:var(--fnx-muted); font-size:11px; margin:0 0 17px 46px; }
        .fnx-kpi-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:0 0 18px; }
        .fnx-kpi-card {
          display:flex; align-items:center; justify-content:space-between; gap:8px;
          min-height:92px; box-sizing:border-box; padding:13px 15px;
          background:#FFFFFF; border:1px solid var(--fnx-border);
          border-top:3px solid var(--kpi-accent); border-radius:14px;
          box-shadow:0 5px 16px rgba(22,72,48,.06);
        }
        .fnx-kpi-copy { min-width:0; }
        .fnx-kpi-label { color:#456257; font-size:11px; font-weight:750; margin-bottom:4px; }
        .fnx-kpi-value { color:var(--fnx-deep); font-size:23px; line-height:1.08; font-weight:850; letter-spacing:-.4px; }
        .fnx-kpi-detail { color:#7A8982; font-size:10px; margin-top:5px; }
        .fnx-kpi-icon {
          width:45px; height:45px; flex:0 0 45px; border-radius:50%;
          display:grid; place-items:center; color:var(--kpi-accent);
          background:var(--kpi-soft); font-size:21px; font-weight:800;
        }
        .fnx-content-grid { display:grid; grid-template-columns:minmax(270px,.82fr) minmax(480px,1.85fr); gap:15px; align-items:start; }
        .fnx-left-stack, .fnx-right-stack { display:flex; flex-direction:column; gap:14px; min-width:0; }
        .fnx-panel {
          background:#FFFFFF; border:1px solid var(--fnx-border); border-radius:14px;
          padding:14px 15px; box-shadow:0 4px 14px rgba(22,72,48,.045); min-width:0;
        }
        .fnx-panel-title { display:flex; align-items:center; gap:8px; color:var(--fnx-deep); font-size:14px; font-weight:850; margin:0 0 12px; padding:0 0 9px; border-bottom:1px solid #E5EEE9; }
        .fnx-panel-title-icon { color:var(--fnx-green); font-size:16px; }
        .fnx-donut-area { display:flex; align-items:center; flex-direction:column; gap:12px; padding:2px 0 1px; }
        .fnx-donut {
          width:174px; height:174px; border-radius:50%; display:grid; place-items:center;
          background:conic-gradient(#14834A 0 var(--low),#D92D20 var(--low) 100%);
          position:relative;
        }
        .fnx-donut:before { content:""; position:absolute; inset:17px; border-radius:50%; background:#FFFFFF; }
        .fnx-donut-center { position:relative; z-index:1; display:flex; flex-direction:column; align-items:center; justify-content:center; }
        .fnx-donut-center strong { color:var(--fnx-deep); font-size:26px; line-height:1.1; font-weight:850; }
        .fnx-donut-center small { color:#87938D; font-size:10px; margin-top:3px; }
        .fnx-legend { display:flex; gap:15px; flex-wrap:wrap; justify-content:center; color:#586B61; font-size:10px; }
        .fnx-legend span { display:inline-flex; align-items:center; gap:5px; }
        .fnx-legend b { color:var(--fnx-ink); }
        .fnx-legend-dot { width:9px; height:9px; border-radius:2px; display:inline-block; }
        .fnx-legend-dot.green { background:#14834A; }
        .fnx-legend-dot.red { background:#D92D20; }
        .fnx-chart-note { color:#87938D; font-size:9px; line-height:1.35; margin-top:8px; }
        .fnx-category-chart { height:157px; display:flex; align-items:flex-end; gap:9px; padding:5px 6px 0; border-bottom:1px solid #DCE9E2; background:repeating-linear-gradient(to top,transparent 0,transparent 37px,#EEF3F0 38px); }
        .fnx-bar-column { flex:1 1 0; min-width:0; height:100%; display:flex; align-items:center; justify-content:flex-end; flex-direction:column; gap:4px; }
        .fnx-bar-value { color:#27483A; font-size:10px; font-weight:800; }
        .fnx-bar-track { height:108px; width:min(100%,46px); display:flex; align-items:flex-end; justify-content:center; }
        .fnx-bar { width:100%; min-height:5px; border-radius:4px 4px 0 0; background:linear-gradient(180deg,#28A45F,#08713D); box-shadow:0 2px 5px rgba(6,75,50,.12); }
        .fnx-bar-label { color:#62766B; font-size:9px; text-align:center; line-height:1.15; min-height:21px; overflow-wrap:anywhere; }
        .fnx-chart-empty { min-height:130px; display:grid; place-items:center; text-align:center; color:#87938D; font-size:11px; padding:10px; }
        .fnx-table-scroll { width:100%; overflow-x:auto; }
        .fnx-table { width:100%; border-collapse:separate; border-spacing:0; font-size:11px; color:var(--fnx-ink); }
        .fnx-table th { background:#EAF5EF; color:#234C3A; font-weight:800; font-size:10px; text-align:left; padding:9px 10px; border-bottom:1px solid #D9E8E0; white-space:nowrap; }
        .fnx-table td { padding:8px 10px; border-bottom:1px solid #E8EFEB; color:#344A40; font-size:10px; white-space:nowrap; }
        .fnx-table tbody tr:nth-child(even) td { background:#FBFDFC; }
        .fnx-table tbody tr:last-child td { border-bottom:0; }
        .fnx-empty-row { color:#8A9891 !important; text-align:center; padding:18px !important; }
        .fnx-pill { display:inline-block; padding:3px 8px; border-radius:20px; font-size:9px; font-weight:800; }
        .fnx-pill-success { background:#DDF6E5; color:#087443; }
        .fnx-pill-danger { background:#FDE6E4; color:#B42318; }
        .fnx-pill-warning { background:#FFF1D6; color:#9A5B00; }
        .fnx-pill-info { background:#E3F2ED; color:#116B52; }
        .fnx-pill-neutral { background:#EEF2EF; color:#5D6B63; }
        .fnx-disclaimer { color:#7A8982; font-size:9px; line-height:1.4; margin:10px 2px 0; }
        @media (max-width:1050px) {
          .fnx-content-grid { grid-template-columns:minmax(240px,.8fr) minmax(0,1.5fr); }
          .fnx-kpi-grid { gap:9px; }
          .fnx-kpi-card { padding:10px; }
          .fnx-kpi-icon { width:36px; height:36px; flex-basis:36px; }
        }
        @media (max-width:820px) {
          .fnx-kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
          .fnx-content-grid { grid-template-columns:1fr; }
        }
        @media (max-width:520px) {
          .fnx-page-heading { font-size:18px; }
          .fnx-kpi-grid { gap:8px; }
          .fnx-kpi-card { min-height:80px; padding:9px; }
          .fnx-kpi-label { font-size:10px; }
          .fnx-kpi-value { font-size:19px; }
          .fnx-kpi-icon { display:none; }
          .fnx-panel { padding:11px; }
          .fnx-donut { width:150px; height:150px; }
          .fnx-table th, .fnx-table td { padding:7px; font-size:9px; }
        }
        </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_dashboard(history_data=None, research_data=None, quality_report=None, pipeline_status=None):
    """Render the live FOODNEXA dashboard using the existing data sources."""
    _install_dashboard_style()

    history = _df(history_data)
    research = _df(research_data)

    risk_col = _column(history, ["risk_level", "expert_risk_label"])
    levels = history[risk_col].map(_risk_label) if risk_col else pd.Series(dtype="object")
    low = int((levels == "Faible").sum())
    moderate = int((levels == "Modéré").sum())
    high = int((levels == "Élevé").sum())

    score = _quality_score(quality_report)
    score_text = f"{score:.1f}%" if score is not None else "N/D"
    activity_rows = _make_activity(history, research)
    history_rows = _make_history(history)

    html_parts = [
        '<div class="fnx-dashboard-wrap">',
        '<div class="fnx-page-heading"><span class="fnx-page-heading-icon">⌂</span><span>Dashboard</span></div>',
        '<div class="fnx-page-subtitle">Monitoring agro-food quality, food safety risks and research data</div>',
        '<div class="fnx-kpi-grid">',
        _kpi_card("Total Analyses", len(history), "Risk assessments", "▥", "green"),
        _kpi_card("Research Observations", len(research), "Scientific records", "▤", "teal"),
        _kpi_card("High Risk", high, "Requires attention", "⚠", "red"),
        _kpi_card("Data Quality", score_text, "Dataset quality score", "✓", "green"),
        '</div>',
        '<div class="fnx-content-grid">',
        '<div class="fnx-left-stack">',
        '<section class="fnx-panel"><h3 class="fnx-panel-title"><span class="fnx-panel-title-icon">◉</span>Risk Distribution</h3>',
        _donut_html(low, moderate + high),
        '<div class="fnx-chart-note">Risk-level distribution only; this is not a regulatory conformity decision.</div></section>',
        '<section class="fnx-panel"><h3 class="fnx-panel-title"><span class="fnx-panel-title-icon">▥</span>Analyses by Product Category</h3>',
        _category_chart_html(research),
        '</section>',
        '</div>',
        '<div class="fnx-right-stack">',
        '<section class="fnx-panel"><h3 class="fnx-panel-title"><span class="fnx-panel-title-icon">▤</span>Recent Activity</h3>',
        _table_html(["Date", "Sample ID", "Product", "Result"], activity_rows, "Result"),
        '</section>',
        '<section class="fnx-panel"><h3 class="fnx-panel-title"><span class="fnx-panel-title-icon">◷</span>Analysis History</h3>',
        _table_html(["Date", "Sample ID", "Product", "Analyst", "Result"], history_rows, "Result"),
        '</section>',
        '</div></div>',
        '<div class="fnx-disclaimer">FOODNEXA is an experimental food-safety risk-intelligence prototype. Its indicators do not replace laboratory analyses, scientific expertise or applicable regulatory requirements.</div>',
        '</div>',
    ]
    # IMPORTANT: Streamlit's Markdown parser treats indented HTML lines as code blocks.
    # The card/table/chart helpers return multi-line HTML with indentation, so normalize
    # the final HTML before rendering to ensure tags are interpreted as HTML, not text.
    dashboard_html = "\n".join(html_parts)
    dashboard_html = "\n".join(line.lstrip() for line in dashboard_html.splitlines())
    st.markdown(dashboard_html, unsafe_allow_html=True)

    with st.expander("Data Quality & System Status", expanded=False):
        quality_score = f"{score:.1f}%" if score is not None else "N/D"
        q1, q2, q3 = st.columns(3)
        q1.metric("Quality Score", quality_score)
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
