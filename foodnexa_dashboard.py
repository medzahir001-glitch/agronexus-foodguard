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
        f"conic-gradient(#13854B 0 {angle}deg, #E52C22 {angle}deg 360deg)"
        if total_risk else "conic-gradient(#D9E2DC 0 360deg)"
    )
    score = _quality_score(quality_report)
    score_label = f"{score:.1f}%" if score is not None else "N/D"
    activity = _table(["Date", "Sample ID", "Product", "Result"], _activity_rows(history, research, limit=5), "Result")
    history_table = _table(["Date", "Sample ID", "Product", "Analyst", "Result"], _history_rows(history, limit=3), "Result")
    issues = _quality_issues(quality_report)
    issue_html = "".join(f"<li>{_esc(issue)}</li>" for issue in issues) or '<li>No quality issue was returned by the current report.</li>'
    pipeline = []
    if isinstance(pipeline_status, dict):
        for name, status in pipeline_status.items():
            label = "Available" if status is True else "Unavailable" if status is False else "Not confirmed"
            css = "success" if status is True else "danger" if status is False else "neutral"
            pipeline.append(f'<span class="status {css}">{_esc(name)}: {label}</span>')
    pipeline_html = "".join(pipeline) or '<span class="status neutral">System status not supplied</span>'
    system_ok = not (isinstance(pipeline_status, dict) and any(value is False for value in pipeline_status.values()))
    system_label = "Système opérationnel" if system_ok else "Vérification requise"
    system_class = "operational" if system_ok else "attention"

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--deep:#064B32;--green:#13854B;--blue:#1478D4;--red:#E52C22;--muted:#6D7E76;--border:#DCE9E2;--ink:#172B24;--paper:#F3F8F5;}}
*{{box-sizing:border-box;}}
html,body{{margin:0;padding:0;width:100%;background:var(--paper);font-family:Inter,Arial,sans-serif;color:var(--ink);}}
body{{overflow-x:hidden;}}
.shell{{width:100%;padding:8px 7px 7px;display:flex;flex-direction:column;gap:12px;}}
.dashboard-head{{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:52px;padding:0 2px;}}
.heading-left{{display:flex;align-items:center;gap:11px;min-width:0;}}
.heading-icon{{width:42px;height:42px;flex:0 0 42px;border-radius:12px;background:linear-gradient(145deg,#159650,#075C3A);color:white;display:grid;place-items:center;font-size:24px;box-shadow:0 4px 10px #0b684026;}}
.heading-title{{font-size:27px;font-weight:850;color:var(--deep);line-height:1.05;}}
.subtitle{{font-size:12px;color:var(--muted);margin:4px 0 0 53px;line-height:1.25;}}
.top-actions{{display:flex;align-items:center;gap:14px;padding-right:8px;color:#173B2B;}}
.bell{{font-size:22px;line-height:1;}}
.avatar{{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:#087A9C;color:white;font-size:14px;font-weight:800;}}
.kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;}}
.kpi{{height:106px;background:#fff;border:1px solid var(--border);border-top:4px solid var(--accent);border-radius:16px;padding:13px 15px;display:flex;align-items:center;justify-content:space-between;gap:8px;box-shadow:0 4px 13px #1648300d;min-width:0;}}
.kpi-copy{{min-width:0;}}
.kpi-label{{font-size:12px;font-weight:800;color:#345548;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.kpi-value{{font-size:28px;font-weight:900;line-height:1.05;color:var(--deep);margin-top:5px;}}
.kpi-detail{{font-size:10px;color:#7A8982;margin-top:4px;}}
.kpi-icon{{width:52px;height:52px;flex:0 0 52px;border-radius:50%;display:grid;place-items:center;background:var(--soft);color:var(--accent);font-size:25px;font-weight:850;}}
.content-row{{display:grid;gap:14px;align-items:stretch;min-width:0;}}
.content-row.primary{{grid-template-columns:minmax(340px,.46fr) minmax(0,1fr);}}
.content-row.secondary{{grid-template-columns:minmax(380px,.61fr) minmax(0,1fr);}}
.panel{{background:#fff;border:1px solid var(--border);border-radius:17px;padding:13px 15px;box-shadow:0 4px 14px #1648300c;min-width:0;overflow:hidden;}}
.panel.primary{{height:262px;}}
.panel.secondary{{height:174px;}}
.panel-title{{display:flex;align-items:center;gap:9px;border-bottom:1px solid #E5EEE9;padding:0 0 8px;margin:0 0 9px;font-size:15px;font-weight:850;color:var(--deep);line-height:1.15;}}
.panel-icon{{font-size:19px;color:var(--green);}}
.donut-area{{height:192px;display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:0 0 1px;}}
.donut{{width:145px;height:145px;border-radius:50%;background:{ring};display:grid;place-items:center;position:relative;}}
.donut:before{{content:"";position:absolute;inset:14px;border-radius:50%;background:#fff;}}
.donut-center{{position:relative;z-index:1;text-align:center;}}
.donut-center strong{{display:block;font-size:28px;line-height:1.05;color:var(--deep);}}
.donut-center span{{font-size:10px;color:#829089;}}
.legend{{display:flex;align-items:center;justify-content:center;gap:13px;flex-wrap:wrap;font-size:10px;color:#586B61;}}
.legend-item{{display:flex;align-items:center;gap:5px;white-space:nowrap;}}
.dot{{width:10px;height:10px;border-radius:3px;display:inline-block;}}
.dot.green{{background:#13854B;}}.dot.red{{background:#E52C22;}}
.chart-note{{font-size:8px;color:#87938D;line-height:1.2;margin-top:3px;}}
.table-wrap{{width:100%;overflow:hidden;}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:10.5px;}}
th{{text-align:left;background:#EAF5EF;color:#234C3A;font-size:10.5px;font-weight:850;padding:8px 9px;border:1px solid #D9E8E0;white-space:nowrap;}}
td{{font-size:10.5px;color:#344A40;padding:7px 9px;border:1px solid #E8EFEB;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;height:30px;}}
tbody tr:nth-child(even) td{{background:#FBFDFC;}}
.pill{{display:inline-block;max-width:100%;border-radius:14px;padding:3px 8px;font-size:9px;font-weight:850;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle;}}
.pill.success{{background:#DDF6E5;color:#087443;}}.pill.danger{{background:#FDE6E4;color:#B42318;}}.pill.warning{{background:#FFF1D6;color:#9A5B00;}}.pill.info{{background:#E3F0FF;color:#1457A6;}}.pill.neutral{{background:#EEF2EF;color:#5D6B63;}}
.empty{{text-align:center;color:#87938D;padding:18px 5px;}}
.panel-link{{display:flex;justify-content:flex-end;margin-top:5px;font-size:10px;font-weight:800;color:#087A43;}}
.category-chart{{height:110px;display:flex;align-items:flex-end;gap:9px;padding:3px 7px 0;border-bottom:1px solid #DCE9E2;background:repeating-linear-gradient(to top,transparent 0,transparent 25px,#EEF3F0 26px);}}
.bar-col{{flex:1 1 0;min-width:0;height:100%;display:flex;align-items:center;justify-content:flex-end;flex-direction:column;gap:3px;}}
.bar-value{{font-size:10px;color:#27483A;font-weight:850;}}
.bar-track{{height:76px;width:min(100%,44px);display:flex;align-items:flex-end;justify-content:center;}}
.bar{{width:100%;min-height:4px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#25A35D,#08713D);}}
.bar-label{{font-size:9.5px;color:#52695D;text-align:center;line-height:1.08;white-space:nowrap;}}
.footer{{min-height:48px;display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1.25fr) auto;align-items:center;gap:10px;padding:8px 11px;border:1px solid #D9E9E0;border-radius:14px;background:linear-gradient(90deg,#F5FBF7,#FFFFFF);}}
.footer-note{{display:flex;align-items:center;gap:9px;font-size:9px;color:#586E62;line-height:1.3;}}
.footer-shield{{width:25px;height:25px;flex:0 0 25px;border-radius:50%;display:grid;place-items:center;background:#DDF3E5;color:#087A43;font-size:15px;}}
.footer-tags{{display:flex;justify-content:center;gap:13px;flex-wrap:wrap;font-size:9px;color:#536B5E;}}
.footer-tag{{white-space:nowrap;}}
.system-status{{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border-radius:20px;padding:7px 11px;font-size:9px;font-weight:850;}}
.system-status.operational{{background:#DDF6E5;color:#087443;border:1px solid #BFE7CC;}}
.system-status.attention{{background:#FFF1D6;color:#965B00;border:1px solid #F3D99E;}}
.system-dot{{width:8px;height:8px;border-radius:50%;background:#21A45A;}}
.system-details{{margin-top:-4px;background:#fff;border:1px solid var(--border);border-radius:9px;padding:5px 9px;}}
.system-details summary{{font-size:9px;font-weight:800;color:var(--deep);cursor:pointer;}}
.detail-body{{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:7px 2px 3px;font-size:9px;color:#52665B;}}
.detail-body ul{{margin:4px 0 0;padding-left:16px;}}
.status{{display:inline-block;margin:2px 4px 0 0;padding:3px 6px;border-radius:12px;font-size:8px;background:#EEF2EF;color:#5D6B63;}}
.status.success{{background:#DDF6E5;color:#087443;}}.status.danger{{background:#FDE6E4;color:#B42318;}}
@media(max-width:1050px){{.content-row.primary{{grid-template-columns:minmax(280px,.55fr) minmax(0,1fr);}}.content-row.secondary{{grid-template-columns:minmax(300px,.65fr) minmax(0,1fr);}}.kpi{{padding:10px;}}.kpi-icon{{width:42px;height:42px;flex-basis:42px;}}}}
@media(max-width:760px){{.kpis{{grid-template-columns:repeat(2,minmax(0,1fr));}}.content-row{{grid-template-columns:1fr!important;}}.panel.primary,.panel.secondary{{height:auto;min-height:210px;}}.footer{{grid-template-columns:1fr;justify-items:start;}}.footer-tags{{justify-content:flex-start;}}.detail-body{{grid-template-columns:1fr;}}.heading-title{{font-size:22px;}}}}
</style>
</head>
<body>
<div class="shell">
  <header class="dashboard-head">
    <div>
      <div class="heading-left"><span class="heading-icon">⌂</span><span class="heading-title">Dashboard</span></div>
      <div class="subtitle">Monitoring agro-food quality, food safety risks and research data</div>
    </div>
    <div class="top-actions"><span class="bell">♧</span><span class="avatar">M</span></div>
  </header>
  <section class="kpis">
    <div class="kpi" style="--accent:#13854B;--soft:#E5F7EC"><div class="kpi-copy"><div class="kpi-label">Total Analyses</div><div class="kpi-value">{len(history)}</div><div class="kpi-detail">Risk assessments</div></div><div class="kpi-icon">▥</div></div>
    <div class="kpi" style="--accent:#1678D4;--soft:#E3F0FF"><div class="kpi-copy"><div class="kpi-label">Research Observations</div><div class="kpi-value">{len(research)}</div><div class="kpi-detail">Scientific records</div></div><div class="kpi-icon">▤</div></div>
    <div class="kpi" style="--accent:#E52C22;--soft:#FDECEC"><div class="kpi-copy"><div class="kpi-label">High Risk</div><div class="kpi-value">{high}</div><div class="kpi-detail">Requires attention</div></div><div class="kpi-icon">⚠</div></div>
    <div class="kpi" style="--accent:#13854B;--soft:#E5F7EC"><div class="kpi-copy"><div class="kpi-label">Data Quality</div><div class="kpi-value">{score_label}</div><div class="kpi-detail">Dataset quality score</div></div><div class="kpi-icon">✓</div></div>
  </section>
  <section class="content-row primary">
    <section class="panel primary"><h3 class="panel-title"><span class="panel-icon">▥</span>Risk Distribution</h3>
      <div class="donut-area"><div class="donut"><div class="donut-center"><strong>{low_share if total_risk else '—'}{'%' if total_risk else ''}</strong><span>Low risk</span></div></div>
      <div class="legend"><span class="legend-item"><i class="dot green"></i>Low Risk ({low})</span><span class="legend-item"><i class="dot red"></i>Moderate / High Risk ({other})</span></div></div>
      <div class="chart-note">Risk-level distribution; not a regulatory conformity decision.</div>
    </section>
    <section class="panel primary"><h3 class="panel-title"><span class="panel-icon">▤</span>Recent Activity</h3>{activity}<div class="panel-link">Voir tout&nbsp; →</div></section>
  </section>
  <section class="content-row secondary">
    <section class="panel secondary"><h3 class="panel-title"><span class="panel-icon">🍃</span>Analyses by Product Category</h3>{_category_chart(research)}</section>
    <section class="panel secondary"><h3 class="panel-title"><span class="panel-icon">◷</span>Analysis History</h3>{history_table}<div class="panel-link">Voir l'historique&nbsp; →</div></section>
  </section>
  <footer class="footer">
    <div class="footer-note"><span class="footer-shield">✦</span><span><b>FOODNEXA</b> is an experimental food-safety risk-intelligence prototype.</span></div>
    <div class="footer-tags"><span class="footer-tag">⚗ Innovation</span><span class="footer-tag">⬡ Sécurité Alimentaire</span><span class="footer-tag">🍃 Recherche Scientifique</span></div>
    <span class="system-status {system_class}"><i class="system-dot"></i>{system_label}</span>
  </footer>
  <details class="system-details"><summary>Data Quality &amp; System Status</summary><div class="detail-body"><div><b>Quality review</b><ul>{issue_html}</ul><div style="margin-top:5px">Exact duplicate rows: {_duplicates(research)}</div></div><div><b>System pipeline</b><div>{pipeline_html}</div></div></div></details>
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
    components.html(document, height=730, scrolling=False)
