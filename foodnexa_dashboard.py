"""
FoodNexa — FoodGuard Dashboard
Reusable Streamlit dashboard inspired by the supplied AgroNexus reference.
Run: streamlit run app.py
Or import: from dashboard_foodnexa import render_dashboard
"""

from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st


# ----------------------------- PAGE THEME -----------------------------
GREEN = "#14532D"
GREEN_2 = "#166534"
LIGHT_GREEN = "#DCFCE7"
RED = "#DC2626"
LIGHT_RED = "#FEE2E2"
TEXT = "#17231B"
MUTED = "#647067"
BG = "#F5F7F5"

st.set_page_config(
    page_title="FoodNexa | FoodGuard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: Inter, sans-serif; }}
    .stApp {{ background: {BG}; color: {TEXT}; }}
    [data-testid="stSidebar"] {{
        background: #FFFFFF;
        border-right: 1px solid #E5EAE5;
    }}
    [data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}
    .brand {{
        display:flex; align-items:center; gap:12px;
        padding: 4px 4px 22px 4px;
    }}
    .brand-icon {{
        width:48px; height:48px; border-radius:14px;
        display:flex; align-items:center; justify-content:center;
        background:#DCFCE7; font-size:27px;
    }}
    .brand-name {{ color:{GREEN}; font-weight:800; font-size:24px; line-height:1.1; }}
    .brand-sub {{ color:{MUTED}; font-size:13px; }}
    .page-title {{
        color:{GREEN}; font-size: clamp(34px, 4vw, 54px);
        font-weight:800; letter-spacing:-1.8px; margin:0; line-height:1.1;
    }}
    .page-subtitle {{ color:#59645C; font-size:16px; margin-top:5px; }}
    .metric-card {{
        background:white; border:1px solid #E8EDE8; border-radius:16px;
        padding:18px 18px 15px 18px; min-height:132px;
        box-shadow:0 3px 12px rgba(20,50,25,.055);
    }}
    .metric-top {{ display:flex; align-items:center; gap:10px; color:#4B554D; font-size:14px; }}
    .metric-icon {{
        width:40px; height:40px; border-radius:50%;
        display:flex; align-items:center; justify-content:center; font-size:20px;
    }}
    .metric-value {{ font-size:36px; line-height:1.2; font-weight:800; margin:5px 0 0 51px; }}
    .metric-note {{ font-size:12px; color:{MUTED}; margin-left:51px; }}
    .panel {{
        background:white; border:1px solid #E8EDE8; border-radius:16px;
        padding:18px; box-shadow:0 3px 12px rgba(20,50,25,.045);
    }}
    .panel-title {{ color:{GREEN}; font-size:20px; font-weight:750; margin-bottom:0; }}
    .panel-sub {{ color:{MUTED}; font-size:12px; margin-top:2px; }}
    .status-ok {{
        background:#DCFCE7; color:#166534; padding:5px 10px;
        border-radius:8px; font-weight:650; font-size:12px;
    }}
    .status-bad {{
        background:#FEE2E2; color:#B91C1C; padding:5px 10px;
        border-radius:8px; font-weight:650; font-size:12px;
    }}
    div[data-testid="stDataFrame"] {{
        border:1px solid #E5EAE5; border-radius:10px; overflow:hidden;
    }}
    div.stButton > button[kind="primary"] {{
        background:{GREEN}; border:1px solid {GREEN}; border-radius:10px;
        font-weight:650; min-height:42px;
    }}
    div.stButton > button[kind="primary"]:hover {{
        background:{GREEN_2}; border-color:{GREEN_2};
    }}
    .small-muted {{ color:{MUTED}; font-size:12px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------- DEMO DATA -----------------------------
# Replace these sample records with your existing FoodNexa database/API.
if "foodnexa_analyses" not in st.session_state:
    st.session_state.foodnexa_analyses = pd.DataFrame([
        ["2026-11-15", "FNX-2026-0142", "Tomatoes — Batch T-204", "Marine Dupont", "Conforme"],
        ["2026-11-15", "FNX-2026-0141", "Milk — Batch M-932", "Nadia Kerrou", "Non conforme"],
        ["2026-11-14", "FNX-2026-0140", "Wheat — Batch W-770", "Marine Dupont", "Conforme"],
        ["2026-11-14", "FNX-2026-0139", "Cheese — Batch C-411", "Nadia Kerrou", "Non conforme"],
        ["2026-11-13", "FNX-2026-0138", "Apples — Batch A-055", "Marine Dupont", "Conforme"],
    ], columns=["Date", "Sample ID", "Product", "Analyst", "Result"])

df = st.session_state.foodnexa_analyses.copy()
total = len(df)
conforme = int((df["Result"] == "Conforme").sum()) if total else 0
non_conforme = int((df["Result"] == "Non conforme").sum()) if total else 0
pending = int((df["Result"] == "Pending").sum()) if total else 0
rate = round(conforme / total * 100) if total else 0


# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-icon">🛡️</div>
          <div><div class="brand-name">FoodNexa</div>
          <div class="brand-sub">FoodGuard</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**WORKSPACE**")
    page = st.radio(
        "Navigation",
        ["Dashboard", "Products", "Analyses", "Reports", "Quality Standards"],
        label_visibility="collapsed",
        index=0,
    )
    st.divider()
    st.markdown("**SUPPORT**")
    st.markdown("❔ Help & Support")
    st.markdown("⚙️ Settings")
    st.markdown("---")
    st.caption("FoodNexa FoodGuard · Prototype")


# ----------------------------- HEADER -----------------------------
header_left, header_right = st.columns([5, 1])
with header_left:
    st.markdown(f'<div class="page-title">{page}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Monitoring agro-food quality &amp; compliance in real time</div>',
        unsafe_allow_html=True,
    )
with header_right:
    st.write("")
    st.write("")
    st.markdown(
        '<div style="text-align:right;font-weight:650;color:#344238">👤 FoodNexa Admin</div>',
        unsafe_allow_html=True,
    )

st.write("")

# Filters and action
f1, f2, f3 = st.columns([1.2, 1.35, 1.1])
with f1:
    selected_date = st.date_input("Date", value=date.today())
with f2:
    analyst = st.text_input("Analyst", value="FoodNexa Admin")
with f3:
    st.write("")
    if st.button("＋  Run Analysis", type="primary", use_container_width=True):
        st.session_state.show_new_analysis = True

if st.session_state.get("show_new_analysis", False):
    with st.expander("Start a new product analysis", expanded=True):
        with st.form("new_analysis_form"):
            product_name = st.text_input("Product / Batch name", placeholder="e.g. Olive oil — Batch O-102")
            analyst_name = st.text_input("Analyst name", value=analyst)
            result = st.selectbox("Initial status", ["Pending", "Conforme", "Non conforme"])
            submitted = st.form_submit_button("Save analysis", type="primary")
            if submitted:
                if product_name.strip():
                    new_row = pd.DataFrame([[
                        selected_date.isoformat(),
                        f"FNX-{date.today().year}-{total + 1:04d}",
                        product_name.strip(),
                        analyst_name.strip() or "Unassigned",
                        result,
                    ]], columns=df.columns)
                    st.session_state.foodnexa_analyses = pd.concat(
                        [st.session_state.foodnexa_analyses, new_row], ignore_index=True
                    )
                    st.session_state.show_new_analysis = False
                    st.success("Analysis added to this session.")
                    st.rerun()
                else:
                    st.warning("Please enter a product or batch name.")

st.write("")

# ----------------------------- KPI CARDS -----------------------------
def metric_card(icon, label, value, note, icon_bg, value_color=GREEN):
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-top">
            <div class="metric-icon" style="background:{icon_bg}">{icon}</div>
            <span>{label}</span>
          </div>
          <div class="metric-value" style="color:{value_color}">{value}</div>
          <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

m1, m2, m3, m4 = st.columns(4)
with m1:
    metric_card("▣", "Total Analyses", total, "All recorded analyses", LIGHT_GREEN)
with m2:
    metric_card("✓", "Conforme", conforme, f"{rate}% of total", LIGHT_GREEN)
with m3:
    pct_bad = round(non_conforme / total * 100) if total else 0
    metric_card("⚠", "Non Conforme", non_conforme, f"{pct_bad}% of total", LIGHT_RED, RED)
with m4:
    metric_card("⌛", "Pending Review", pending, "Awaiting validation", "#E8F5E9")

st.write("")

# ----------------------------- CHARTS + ACTIVITY -----------------------------
left, right = st.columns([0.95, 1.75], gap="medium")

with left:
    st.markdown('<div class="panel-title">Conformity Rate</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-sub">Based on all recorded analyses</div>', unsafe_allow_html=True)
    if total:
        donut = pd.DataFrame({
            "Status": ["Conforme", "Non conforme", "Pending"],
            "Count": [conforme, non_conforme, pending],
        })
        donut = donut[donut["Count"] > 0]
        fig = px.pie(
            donut, names="Status", values="Count", hole=0.68,
            color="Status",
            color_discrete_map={
                "Conforme": GREEN_2,
                "Non conforme": RED,
                "Pending": "#EAB308",
            },
        )
        fig.update_traces(textinfo="none", hovertemplate="%{label}: %{value}<extra></extra>")
        fig.update_layout(
            height=245, margin=dict(t=5, b=5, l=5, r=5),
            showlegend=True, legend=dict(orientation="h", y=-0.08, x=0.0, font=dict(size=10)),
            annotations=[dict(text=f"<b>{rate}%</b>", x=0.5, y=0.5,
                               font=dict(size=27, color=TEXT), showarrow=False)],
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No analyses recorded yet.")

    st.markdown('<div class="panel-title">Analyses by Product Category</div>', unsafe_allow_html=True)
    # Demo category values; replace with product category aggregation from your database.
    categories = pd.DataFrame({
        "Category": ["Tomatoes", "Milk", "Wheat", "Cheese", "Apples"],
        "Analyses": [42, 36, 28, 22, 14],
    })
    bar = px.bar(categories, x="Analyses", y="Category", orientation="h", text="Analyses",
                 color="Analyses", color_continuous_scale=["#A7D9A0", GREEN])
    bar.update_traces(textposition="outside", marker_line_width=0)
    bar.update_layout(
        height=245, margin=dict(t=5, b=5, l=0, r=25),
        xaxis_title=None, yaxis_title=None, coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(categoryorder="array", categoryarray=categories["Category"].tolist()[::-1]),
    )
    st.plotly_chart(bar, use_container_width=True, config={"displayModeBar": False})

with right:
    st.markdown('<div class="panel-title">Recent Activity</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-sub">Latest product analyses</div>', unsafe_allow_html=True)
    if not df.empty:
        latest = df.head(3)
        for _, row in latest.iterrows():
            status_color = GREEN if row["Result"] == "Conforme" else RED if row["Result"] == "Non conforme" else "#A16207"
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                padding:10px 2px;border-bottom:1px solid #EEF1EE;gap:12px">
                  <div><b style="font-size:13px">{row['Product']}</b>
                  <div class="small-muted">{row['Sample ID']} · {row['Date']}</div></div>
                  <span style="color:{status_color};font-weight:700;font-size:12px">{row['Result']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No recent activity.")

    st.write("")
    st.markdown('<div class="panel-title">Analysis History</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-sub">Latest recorded product analyses</div>', unsafe_allow_html=True)

    search = st.text_input("Search history", placeholder="Search product, sample ID or analyst", label_visibility="collapsed")
    filtered = df.copy()
    if search:
        mask = filtered.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered = filtered[mask]

    display_df = filtered.rename(columns={
        "Date": "Date",
        "Sample ID": "Sample ID",
        "Product": "Product",
        "Analyst": "Analyst",
        "Result": "Result",
    })
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=265,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "Result": st.column_config.TextColumn("Result"),
        },
    )
    st.caption(f"Showing {len(filtered)} of {len(df)} results")

st.markdown("---")
st.caption("© FoodNexa FoodGuard · Food quality and safety monitoring")
