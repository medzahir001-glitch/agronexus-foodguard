"""FOODNEXA compact enterprise dashboard.

Uses the existing app.py render_dashboard(...) contract and existing data only.
The dashboard is rendered in a dedicated Streamlit component iframe so HTML is
never interpreted by Streamlit's Markdown parser as a code block.
"""

import html
import json
import math
import pandas as pd
import streamlit.components.v1 as components


def _frame(value):
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    try:
        return pd.DataFrame(value)
    except Exception:
        return pd.DataFrame()


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in {"", "nan", "none", "null", "n/a", "nat"}
    try:
        result = pd.isna(value)
        if getattr(result, "ndim", 0) == 0:
            return bool(result)
    except (TypeError, ValueError):
        pass
    return False


def _text(value, default="—"):
    if _is_missing(value):
        return default
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value).strip()


def _esc(value, default="—"):
    return html.escape(_text(value, default), quote=True)


def _find_column(frame, candidates):
    if frame.empty:
        return None
    lookup = {str(column).strip().casefold(): column for column in frame.columns}
    for candidate in candidates:
        found = lookup.get(candidate.casefold())
        if found is not None:
            return found
    return None


def _row_value(row, candidates, default="—"):
    for candidate in candidates:
        if candidate in row.index and not _is_missing(row[candidate]):
            return _text(row[candidate], default)
    return default


def _risk(value):
    raw = _text(value, "").casefold()
    if raw in {"faible", "low", "low risk"}:
        return "Faible"
    if raw in {"modéré", "modere", "moderate", "medium"}:
        return "Modéré"
    if raw in {"élevé", "eleve", "high", "high risk"}:
        return "Élevé"
    return _text(value, "—")


def _status(value):
    raw = _text(value, "").casefold()
    if any(token in raw for token in ("élevé", "eleve", "high", "risk")):
        return "danger"
    if any(token in raw for token in ("modéré", "modere", "moderate", "medium")):
        return "warning"
    if any(token in raw for token in ("faible", "low", "conforme", "success", "available", "disponible")):
        return "success"
    if "research" in raw or "observation" in raw:
        return "info"
    return "neutral"


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


def _duplicates(frame):
    if frame.empty:
        return 0
    try:
        return int(frame.astype("string").fillna("").duplicated().sum())
    except Exception:
        return 0


def _date_text(value):
    text = _text(value)
    if text == "—":
        return text
    try:
        stamp = pd.to_datetime(text, errors="coerce", utc=True)
        if pd.isna(stamp):
            return text[:19]
        return stamp.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return text[:19]


def _activity_rows(history, research, limit=6):
    records = []
    for _, row in history.iterrows():
        date_value = _row_value(row, ["analysis_date", "created_at", "date"])
        records.append({
            "Date": _date_text(date_value),
            "Sample ID": _row_value(row, ["batch_id", "sample_id", "sample_ref"]),
            "Product": _row_value(row, ["product_name", "product"]),
            "Result": _risk(_row_value(row, ["risk_level", "expert_risk_label", "predicted_risk"])),
            "_sort": date_value,
        })
    for _, row in research.iterrows():
        date_value = _row_value(row, ["analysis_date", "created_at", "sampling_date", "date"])
        records.append({
            "Date": _date_text(date_value),
            "Sample ID": _row_value(row, ["batch_id", "sample_id", "sample_ref"]),
            "Product": _row_value(row, ["product_name", "product"]),
            "Result": "Research observation",
            "_sort": date_value,
        })
    if not records:
        return []
    result = pd.DataFrame(records)
    result["_parsed"] = pd.to_datetime(result["_sort"].replace("—", pd.NA), errors="coerce", utc=True)
    result = result.sort_values("_parsed", ascending=False, na_position="last")
    return result.head(limit).drop(columns=["_sort", "_parsed"]).to_dict("records")


def _history_rows(history, limit=4):
    if history.empty:
        return []
    rows = []
    for _, row in history.tail(limit).iloc[::-1].iterrows():
        rows.append({
            "Date": _date_text(_row_value(row, ["analysis_date", "created_at", "date"])),
            "Sample ID": _row_value(row, ["batch_id", "sample_id", "sample_ref"]),
            "Product": _row_value(row, ["product_name", "product"]),
            "Analyst": _row_value(row, ["analyst", "analyst_name", "operator"]),
            "Result": _risk(_row_value(row, ["risk_level", "expert_risk_label", "predicted_risk"])),
        })
    return rows


def _table(headers, rows, result_key="Result"):
    head = "".join(f"<th>{_esc(label)}</th>" for label in headers)
    body = []
    if not rows:
        body.append(f'<tr><td class="empty" colspan="{len(headers)}">No records available yet</td></tr>')
    else:
        for row in rows:
            cells = []
            for label in headers:
                value = row.get(label, "—")
                if label == result_key:
                    cells.append(f'<td><span class="pill {_status(value)}">{_esc(value)}</span></td>')
                else:
                    cells.append(f'<td title="{_esc(value)}">{_esc(value)}</td>')
            body.append("<tr>" + "".join(cells) + "</tr>")
    return '<div class="table-wrap"><table><thead><tr>' + head + '</tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>'


def _category_values(research):
    names = ["Dairy", "Vegetal", "Cereals", "Meat", "Seafood", "Beverages"]
    counts = {name: 0 for name in names}
    col = _find_column(research, ["product_category", "category", "product_name", "product"])
    if col is None or research.empty:
        return counts
    for value in research[col].tolist():
        raw = _text(value, "").casefold()
        if not raw:
            continue
        if any(key in raw for key in ("dairy", "lait", "milk", "fromage", "yaourt")):
            counts["Dairy"] += 1
        elif any(key in raw for key in ("vegetal", "végétal", "plant", "vegetable")):
            counts["Vegetal"] += 1
        elif any(key in raw for key in ("cereal", "céréale", "grain", "farine")):
            counts["Cereals"] += 1
        elif any(key in raw for key in ("meat", "viande", "beef", "poultry", "poulet")):
            counts["Meat"] += 1
        elif any(key in raw for key in ("seafood", "fish", "poisson", "sea food", "crustacé")):
            counts["Seafood"] += 1
        elif any(key in raw for key in ("beverage", "boisson", "drink", "jus")):
            counts["Beverages"] += 1
    return counts


def _category_chart(research):
    counts = _category_values(research)
    maximum = max(counts.values()) if counts else 0
    columns = []
    for label, value in counts.items():
        height = 5 if maximum == 0 else max(5, round((value / maximum) * 76))
        columns.append(
            f'<div class="bar-col"><span class="bar-value">{value}</span>'
            f'<div class="bar-track"><div class="bar" style="height:{height}px"></div></div>'
            f'<span class="bar-label">{_esc(label)}</span></div>'
        )
    return '<div class="category-chart">' + ''.join(columns) + '</div>'


def _quality_issues(report):
    if not isinstance(report, dict):
        return []
    issues = report.get("issues", [])
    if not isinstance(issues, list):
        return []
    output = []
    for item in issues[:12]:
        if isinstance(item, dict):
            output.append(_text(item.get("message", item.get("issue", item.get("Problème", item.get("type", "Review required"))))))
        else:
            output.append(str(item))
    return output


def _document(history, research, quality_report, pipeline_status, low, other, high):
    total_risk = low + other
    low_share = 0 if total_risk == 0 else round(low / total_risk * 100)
    angle = low_share * 3.6
    ring = (
        f"conic-gradient(#13854B 0 {angle}deg, #D92D20 {angle}deg 360deg)"
        if total_risk else "conic-gradient(#D9E2DC 0 360deg)"
    )
    score = _quality_score(quality_report)
    score_label = f"{score:.1f}%" if score is not None else "N/D"
    activity = _table(["Date", "Sample ID", "Product", "Result"], _activity_rows(history, research), "Result")
    history_table = _table(["Date", "Sample ID", "Product", "Analyst", "Result"], _history_rows(history), "Result")
    issues = _quality_issues(quality_report)
    issue_html = "".join(f"<li>{_esc(issue)}</li>" for issue in issues) or '<li>No quality issue was returned by the current report.</li>'
    pipeline = []
    if isinstance(pipeline_status, dict):
        for name, status in pipeline_status.items():
            label = "Available" if status is True else "Unavailable" if status is False else "Not confirmed"
            css = "success" if status is True else "danger" if status is False else "neutral"
            pipeline.append(f'<span class="status {css}">{_esc(name)}: {label}</span>')
    pipeline_html = "".join(pipeline) or '<span class="status neutral">System status not supplied</span>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--deep:#064B32;--green:#13854B;--muted:#6D7E76;--border:#DCE9E2;--ink:#172B24;--paper:#F3F8F5;}}
*{{box-sizing:border-box;}}
html,body{{margin:0;padding:0;width:100%;background:var(--paper);font-family:Inter,Arial,sans-serif;color:var(--ink);}}
body{{overflow-x:hidden;}}
.shell{{width:100%;padding:4px 5px 5px;display:flex;flex-direction:column;gap:8px;}}
.heading{{display:flex;align-items:center;gap:9px;min-height:31px;}}
.heading-icon{{width:29px;height:29px;flex:0 0 29px;border-radius:9px;background:linear-gradient(145deg,#169653,#075C3A);color:white;display:grid;place-items:center;font-size:16px;box-shadow:0 3px 7px #0b684026;}}
.heading-title{{font-size:18px;font-weight:850;color:var(--deep);line-height:1.1;}}
.subtitle{{font-size:9px;color:var(--muted);margin:-2px 0 0 38px;line-height:1.3;}}
.kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;}}
.kpi{{height:70px;background:#fff;border:1px solid var(--border);border-top:3px solid var(--accent);border-radius:11px;padding:8px 10px;display:flex;align-items:center;justify-content:space-between;gap:6px;box-shadow:0 3px 9px #1648300d;min-width:0;}}
.kpi-label{{font-size:9px;font-weight:750;color:#456257;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.kpi-value{{font-size:20px;font-weight:850;line-height:1.1;color:var(--deep);margin-top:3px;}}
.kpi-detail{{font-size:8px;color:#7A8982;margin-top:3px;}}
.kpi-icon{{width:32px;height:32px;flex:0 0 32px;border-radius:50%;display:grid;place-items:center;background:var(--soft);color:var(--accent);font-size:16px;font-weight:800;}}
.content{{display:grid;grid-template-columns:minmax(230px,.82fr) minmax(0,1.68fr);gap:9px;align-items:stretch;}}
.stack{{display:flex;flex-direction:column;gap:8px;min-width:0;}}
.panel{{background:#fff;border:1px solid var(--border);border-radius:11px;padding:9px 10px;box-shadow:0 3px 9px #1648300b;min-width:0;overflow:hidden;}}
.panel.top{{height:190px;}}
.panel.bottom{{height:142px;}}
.panel-title{{display:flex;align-items:center;gap:6px;border-bottom:1px solid #E5EEE9;padding:0 0 6px;margin:0 0 7px;font-size:11px;font-weight:850;color:var(--deep);}}
.panel-icon{{font-size:13px;color:var(--green);}}
.donut-area{{height:137px;display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:0 0 2px;}}
.donut{{width:98px;height:98px;border-radius:50%;background:{ring};display:grid;place-items:center;position:relative;}}
.donut:before{{content:"";position:absolute;inset:12px;border-radius:50%;background:#fff;}}
.donut-center{{position:relative;z-index:1;text-align:center;}}
.donut-center strong{{display:block;font-size:21px;line-height:1.05;color:var(--deep);}}
.donut-center span{{font-size:7.5px;color:#829089;}}
.legend{{display:flex;align-items:center;justify-content:center;gap:9px;flex-wrap:wrap;font-size:8px;color:#586B61;}}
.legend-item{{display:flex;align-items:center;gap:4px;white-space:nowrap;}}
.dot{{width:7px;height:7px;border-radius:2px;display:inline-block;}}
.dot.green{{background:#13854B;}}.dot.red{{background:#D92D20;}}
.chart-note{{font-size:7px;color:#87938D;line-height:1.25;margin-top:4px;}}
.table-wrap{{width:100%;overflow:hidden;}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8.5px;}}
th{{text-align:left;background:#EAF5EF;color:#234C3A;font-size:8.5px;font-weight:800;padding:5px 6px;border:1px solid #D9E8E0;white-space:nowrap;}}
td{{font-size:8.5px;color:#344A40;padding:5px 6px;border:1px solid #E8EFEB;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
tbody tr:nth-child(even) td{{background:#FBFDFC;}}
.pill{{display:inline-block;max-width:100%;border-radius:12px;padding:2px 5px;font-size:7.5px;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle;}}
.pill.success{{background:#DDF6E5;color:#087443;}}.pill.danger{{background:#FDE6E4;color:#B42318;}}.pill.warning{{background:#FFF1D6;color:#9A5B00;}}.pill.info{{background:#E3F2ED;color:#116B52;}}.pill.neutral{{background:#EEF2EF;color:#5D6B63;}}
.empty{{text-align:center;color:#87938D;padding:12px 5px;}}
.category-chart{{height:88px;display:flex;align-items:flex-end;gap:5px;padding:3px 5px 0;border-bottom:1px solid #DCE9E2;background:repeating-linear-gradient(to top,transparent 0,transparent 21px,#EEF3F0 22px);}}
.bar-col{{flex:1 1 0;min-width:0;height:100%;display:flex;align-items:center;justify-content:flex-end;flex-direction:column;gap:2px;}}
.bar-value{{font-size:8px;color:#27483A;font-weight:800;}}
.bar-track{{height:63px;width:min(100%,30px);display:flex;align-items:flex-end;justify-content:center;}}
.bar{{width:100%;min-height:4px;border-radius:3px 3px 0 0;background:linear-gradient(180deg,#28A45F,#08713D);}}
.bar-label{{font-size:7.5px;color:#62766B;text-align:center;line-height:1.08;white-space:nowrap;}}
.disclaimer{{font-size:7px;line-height:1.25;color:#7A8982;padding:0 2px;}}
details{{margin-top:1px;background:#fff;border:1px solid var(--border);border-radius:8px;padding:4px 7px;}}
summary{{font-size:8px;font-weight:750;color:var(--deep);cursor:pointer;}}
.detail-body{{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:6px 2px 3px;font-size:8px;color:#52665B;}}
.detail-body ul{{margin:4px 0 0;padding-left:15px;}}
.status{{display:inline-block;margin:2px 4px 0 0;padding:2px 5px;border-radius:12px;font-size:7.5px;background:#EEF2EF;color:#5D6B63;}}
.status.success{{background:#DDF6E5;color:#087443;}}.status.danger{{background:#FDE6E4;color:#B42318;}}
@media(max-width:900px){{.content{{grid-template-columns:minmax(205px,.75fr) minmax(0,1.25fr);}}.kpi{{padding:7px;}}.kpi-label{{font-size:8px;}}}}
@media(max-width:680px){{.kpis{{grid-template-columns:repeat(2,minmax(0,1fr));}}.content{{grid-template-columns:1fr;}}.panel.top,.panel.bottom{{height:auto;min-height:145px;}}.detail-body{{grid-template-columns:1fr;}}}}
</style>
</head>
<body>
<div class="shell">
  <div>
    <div class="heading"><span class="heading-icon">⌂</span><span class="heading-title">Dashboard</span></div>
    <div class="subtitle">Monitoring agro-food quality, food safety risks and research data</div>
  </div>
  <div class="kpis">
    <div class="kpi" style="--accent:#13854B;--soft:#E5F7EC"><div><div class="kpi-label">Total Analyses</div><div class="kpi-value">{len(history)}</div><div class="kpi-detail">Risk assessments</div></div><div class="kpi-icon">▥</div></div>
    <div class="kpi" style="--accent:#187A70;--soft:#E5F5F2"><div><div class="kpi-label">Research Observations</div><div class="kpi-value">{len(research)}</div><div class="kpi-detail">Scientific records</div></div><div class="kpi-icon">▤</div></div>
    <div class="kpi" style="--accent:#D92D20;--soft:#FDECEC"><div><div class="kpi-label">High Risk</div><div class="kpi-value">{high}</div><div class="kpi-detail">Requires attention</div></div><div class="kpi-icon">⚠</div></div>
    <div class="kpi" style="--accent:#13854B;--soft:#E5F7EC"><div><div class="kpi-label">Data Quality</div><div class="kpi-value">{score_label}</div><div class="kpi-detail">Dataset quality score</div></div><div class="kpi-icon">✓</div></div>
  </div>
  <div class="content">
    <div class="stack">
      <section class="panel top"><h3 class="panel-title"><span class="panel-icon">◉</span>Risk Distribution</h3>
        <div class="donut-area"><div class="donut"><div class="donut-center"><strong>{low_share if total_risk else '—'}{'%' if total_risk else ''}</strong><span>Low risk share</span></div></div>
        <div class="legend"><span class="legend-item"><i class="dot green"></i>Low Risk ({low})</span><span class="legend-item"><i class="dot red"></i>Moderate / High ({other})</span></div></div>
        <div class="chart-note">Risk-level distribution; not a regulatory conformity decision.</div>
      </section>
      <section class="panel bottom"><h3 class="panel-title"><span class="panel-icon">▥</span>Analyses by Product Category</h3>{_category_chart(research)}</section>
    </div>
    <div class="stack">
      <section class="panel top"><h3 class="panel-title"><span class="panel-icon">▤</span>Recent Activity</h3>{activity}</section>
      <section class="panel bottom"><h3 class="panel-title"><span class="panel-icon">◷</span>Analysis History</h3>{history_table}</section>
    </div>
  </div>
  <div class="disclaimer">FOODNEXA is an experimental food-safety risk-intelligence prototype. Indicators do not replace laboratory analyses, scientific expertise or applicable regulatory requirements.</div>
  <details><summary>Data Quality &amp; System Status</summary><div class="detail-body"><div><b>Quality review</b><ul>{issue_html}</ul><div style="margin-top:5px">Exact duplicate rows: {_duplicates(research)}</div></div><div><b>System pipeline</b><div>{pipeline_html}</div></div></div></details>
</div>
</body>
</html>'''


def render_dashboard(history_data=None, research_data=None, quality_report=None, pipeline_status=None):
    """Render compact live dashboard; source data is never changed."""
    history = _frame(history_data)
    research = _frame(research_data)
    risk_column = _find_column(history, ["risk_level", "expert_risk_label", "risk_category", "predicted_risk"])
    if risk_column is not None:
        levels = history[risk_column].map(_risk)
        low = int((levels == "Faible").sum())
        moderate = int((levels == "Modéré").sum())
        high = int((levels == "Élevé").sum())
    else:
        low = moderate = high = 0
    other = moderate + high
    document = _document(history, research, quality_report, pipeline_status, low, other, high)
    components.html(document, height=565, scrolling=True)
