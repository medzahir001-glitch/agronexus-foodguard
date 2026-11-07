
st.markdown("""
<style>

/* ================================
   FOODNEXA PROFESSIONAL UI
   NAVY + TURQUOISE + EMERALD
================================ */

:root {
    --navy: #102B46;
    --turquoise: #087E9B;
    --emerald: #16A078;
    --light: #F1F5F9;
    --text: #243B53;
    --white: #FFFFFF;
}

/* Main layout */
.block-container {
    max-width: 1450px;
    padding-top: 0.8rem !important;
    padding-bottom: 1.2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* Global typography */
html, body, [class*="css"] {
    font-size: 13px !important;
    color: var(--text) !important;
}

p, label, li, .stMarkdown,
[data-testid="stMarkdownContainer"] {
    font-size: 0.88rem !important;
    line-height: 1.5 !important;
    color: var(--text);
}

/* Headings */
h1, h2, h3 {
    color: var(--navy) !important;
    font-weight: 800 !important;
}

h1 {
    font-size: 1.75rem !important;
}

h2 {
    font-size: 1.4rem !important;
}

h3 {
    font-size: 1.12rem !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    min-width: 225px;
    max-width: 225px;
    background: #102B46 !important;
}

[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-size: 1.05rem !important;
    font-weight: 800 !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    font-size: 0.82rem !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

/* METRIC CARDS - FIX BLACK TEXT */
[data-testid="stMetric"] {
    background: #102B46 !important;
    border: 1px solid #087E9B !important;
    border-left: 4px solid #16A078 !important;
    border-radius: 11px !important;
    padding: 13px 15px !important;
    box-shadow: 0 3px 9px rgba(16,43,70,0.12);
}

/* Force all metric text to white */
[data-testid="stMetric"] *,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] *,
[data-testid="stMetricDelta"],
[data-testid="stMetricDelta"] * {
    color: #FFFFFF !important;
}

[data-testid="stMetricLabel"] {
    font-size: 0.78rem !important;
    font-weight: 650 !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.5rem !important;
    font-weight: 800 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.75rem !important;
}

/* Inputs */
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stDateInput label,
.stTextArea label,
.stCheckbox label {
    font-size: 0.82rem !important;
    font-weight: 650 !important;
    color: var(--navy) !important;
}

.stTextInput input,
.stNumberInput input,
.stSelectbox div,
.stDateInput input,
.stTextArea textarea {
    font-size: 0.85rem !important;
}

/* Buttons */
.stButton button,
.stFormSubmitButton button,
.stDownloadButton button {
    font-size: 0.83rem !important;
    min-height: 36px !important;
    padding: 7px 14px !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

/* Primary buttons */
.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {
    background: #087E9B !important;
    color: #FFFFFF !important;
    border: none !important;
}

/* Section headings */
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    border-left: 4px solid #16A078;
    padding-left: 10px;
    margin-top: 12px;
}

/* Tables */
[data-testid="stDataFrame"] {
    border: 1px solid #D8E3EC !important;
    border-radius: 9px !important;
    overflow: hidden !important;
}

[data-testid="stDataFrame"] * {
    font-size: 0.82rem !important;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid #D8E3EC !important;
    border-radius: 9px !important;
}

[data-testid="stExpander"] summary {
    font-size: 0.86rem !important;
    font-weight: 700 !important;
    color: var(--navy) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    font-size: 0.84rem !important;
    font-weight: 650 !important;
    padding: 8px 13px !important;
}

/* Alerts */
[data-testid="stAlert"] {
    padding: 10px 13px !important;
    border-radius: 9px !important;
}

[data-testid="stAlert"] p {
    font-size: 0.84rem !important;
}

/* Branding */
.foodnexa-tagline {
    text-align: center;
    color: #087E9B !important;
    font-size: 12px !important;
    font-weight: 800;
    letter-spacing: 1.2px;
    margin: 5px 0 12px;
}

.foodnexa-line {
    height: 4px;
    width: 100%;
    background: linear-gradient(
        90deg,
        #102B46,
        #087E9B,
        #16A078
    );
    border-radius: 10px;
    margin-bottom: 16px;
}

/* Footer */
.footer-text {
    text-align: center;
    color: #64748B !important;
    font-size: 10px !important;
    line-height: 1.7;
    padding: 12px;
}

/* Compact spacing */
div[data-testid="stVerticalBlock"] {
    gap: 0.7rem;
}

hr {
    margin-top: 0.7rem !important;
    margin-bottom: 0.7rem !important;
}

/* Responsive */
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }

    h1 {
        font-size: 1.4rem !important;
    }

    h2 {
        font-size: 1.15rem !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.15rem !important;
    }
}

</style>
""", unsafe_allow_html=True)
