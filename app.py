
import os
import streamlit as st
import pandas as pd
import re

from foodguard_engine import assess_dairy_food_safety_risk
from foodnexa_data_quality import generate_quality_report
from foodnexa_cleaning_engine import clean_research_dataset
from foodnexa_dashboard import render_dashboard
from foodnexa_supabase import (
    save_risk_assessment,
    save_research_observation,
    get_research_observations,
)

# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="FOODNEXA",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_FILE = "agronexus_assessments.csv"
RESEARCH_CSV_FILE = "foodnexa_research_dataset.csv"
LOGO_FILE = "foodnexa_logo.png"

RESEARCH_COLUMNS = [
    "batch_id", "product_name", "temperature_celsius", "storage_days",
    "ph", "cold_chain_broken", "hygiene_controlled", "pasteurized",
    "total_viable_count", "enterobacteriaceae_count", "coliform_count",
    "staphylococcus_aureus_count", "salmonella_detected", "sensory_status",
    "nonconformity_detected", "expert_risk_label",
]

# =====================================================
# GLOBAL DESIGN - FOODNEXA WHITE ENTERPRISE
# =====================================================

st.markdown("""
<style>
:root {
    --fnx-navy: #123451;
    --fnx-blue: #087D9C;
    --fnx-teal: #0B8F98;
    --fnx-green: #15966F;
    --fnx-ink: #1B2D3B;
    --fnx-muted: #66798A;
    --fnx-border: #DCE6ED;
    --fnx-soft: #F4F8FB;
}

/* GLOBAL CANVAS */
html, body, [data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.main, .block-container {
    background: #FFFFFF !important;
    color: var(--fnx-ink) !important;
}

.block-container {
    max-width: 1480px !important;
    padding-top: 1.15rem !important;
    padding-bottom: 2.6rem !important;
}

/* TYPOGRAPHY */
[data-testid="stAppViewContainer"] .main,
[data-testid="stAppViewContainer"] .main p,
[data-testid="stAppViewContainer"] .main li,
[data-testid="stAppViewContainer"] .main span,
[data-testid="stAppViewContainer"] .main small,
[data-testid="stAppViewContainer"] .main label,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] {
    color: var(--fnx-ink) !important;
    opacity: 1 !important;
}

[data-testid="stAppViewContainer"] .main h1,
h1 {
    color: #075B91 !important;
    font-size: 1.48rem !important;
    font-weight: 850 !important;
    line-height: 1.25 !important;
}

[data-testid="stAppViewContainer"] .main h2,
h2 {
    color: #08758F !important;
    font-size: 1.12rem !important;
    font-weight: 800 !important;
}

[data-testid="stAppViewContainer"] .main h3,
h3 {
    color: #16734F !important;
    font-size: 0.96rem !important;
    font-weight: 800 !important;
}

[data-testid="stAppViewContainer"] .main p,
[data-testid="stAppViewContainer"] .main li,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"] {
    font-size: 0.86rem !important;
    line-height: 1.5 !important;
}

[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] {
    color: var(--fnx-muted) !important;
    font-size: 0.74rem !important;
}

[data-testid="stAppViewContainer"] .main strong,
[data-testid="stAppViewContainer"] .main b {
    color: var(--fnx-navy) !important;
}

[data-testid="stAppViewContainer"] .main a {
    color: var(--fnx-blue) !important;
    font-weight: 700 !important;
}

/* BRAND HEADER */
.foodnexa-brand-title {
    text-align: center;
    color: var(--fnx-blue) !important;
    font-size: clamp(2.5rem, 5.3vw, 4.25rem);
    line-height: 1.05;
    font-weight: 900;
    letter-spacing: 3px;
    margin: 4px 0 0;
    text-shadow: 0 3px 12px rgba(8,125,156,.12);
}

.foodnexa-brand-subtitle {
    text-align: center;
    color: var(--fnx-navy) !important;
    font-size: 0.82rem;
    font-weight: 850;
    letter-spacing: 2px;
    margin: 7px 0 17px;
}

.foodnexa-tagline {
    text-align: center;
    color: var(--fnx-blue) !important;
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 1px;
    margin: 8px 0 18px;
}

.foodnexa-line {
    height: 4px;
    width: 100%;
    background: linear-gradient(90deg, var(--fnx-navy), var(--fnx-blue), var(--fnx-green));
    border-radius: 10px;
    margin-bottom: 23px;
}

.footer-text {
    text-align: center;
    color: var(--fnx-muted) !important;
    font-size: 0.72rem;
    line-height: 1.7;
    padding: 16px;
}

/* SIDEBAR - NAVY BRAND */
section[data-testid="stSidebar"] {
    background: #123451 !important;
    border-right: 1px solid #D9E4EC !important;
}

section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    color: #FFFFFF !important;
    font-size: 0.84rem !important;
    font-weight: 650 !important;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #D8E5EF !important;
}

/* KPI METRICS - WHITE CARDS */
div[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid var(--fnx-border) !important;
    border-left: 4px solid var(--fnx-green) !important;
    border-radius: 12px !important;
    padding: 13px 15px !important;
    box-shadow: 0 3px 11px rgba(18,52,81,.055) !important;
}

div[data-testid="stMetric"] *,
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricLabel"],
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: var(--fnx-navy) !important;
    opacity: 1 !important;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 850 !important;
}

div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    font-size: 0.76rem !important;
    font-weight: 700 !important;
}

/* INPUTS */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stDateInput label, .stTextArea label, .stCheckbox label,
.stRadio label, .stMultiSelect label, .stSlider label {
    color: var(--fnx-navy) !important;
    opacity: 1 !important;
    font-weight: 700 !important;
    font-size: 0.80rem !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background: #FFFFFF !important;
    color: #1B2D3B !important;
    border: 1px solid #C9D7E1 !important;
    border-radius: 8px !important;
}

[data-baseweb="select"] > div {
    background: #FFFFFF !important;
    color: #1B2D3B !important;
    border-color: #C9D7E1 !important;
}

/* BUTTONS */
.stButton button, .stFormSubmitButton button, .stDownloadButton button {
    border-radius: 8px !important;
    font-weight: 750 !important;
    min-height: 38px;
    border: 1px solid #087D9C !important;
}

.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {
    background: #087D9C !important;
    color: #FFFFFF !important;
}

.stDownloadButton button {
    background: #FFFFFF !important;
    color: #087D9C !important;
}

/* TABLES */
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    background: #FFFFFF !important;
    border: 1px solid var(--fnx-border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

div[data-testid="stDataFrame"] * {
    color: #1B2D3B !important;
    font-size: 0.78rem !important;
}

/* TABS, EXPANDERS, ALERTS */
.stTabs [data-baseweb="tab"] {
    color: var(--fnx-navy) !important;
    font-weight: 750 !important;
}

.stTabs [aria-selected="true"] {
    color: var(--fnx-blue) !important;
    border-bottom-color: var(--fnx-green) !important;
}

details[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid var(--fnx-border) !important;
    border-radius: 10px !important;
}

div[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* CHARTS: keep a white plotting surface */
[data-testid="stVegaLiteChart"],
[data-testid="stArrowVegaLiteChart"],
[data-testid="stPyplotChart"],
[data-testid="stDeckGlJsonChart"] {
    background: #FFFFFF !important;
    border-radius: 10px !important;
}

/* RESPONSIVE */
@media (max-width: 768px) {
    .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    [data-testid="stAppViewContainer"] .main h1 {
        font-size: 1.2rem !important;
    }
    [data-testid="stAppViewContainer"] .main h2 {
        font-size: 1rem !important;
    }
    .foodnexa-brand-title {
        font-size: 2.5rem;
        letter-spacing: 2px;
    }
    .foodnexa-brand-subtitle {
        font-size: 0.7rem;
        letter-spacing: 1px;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.08rem !important;
    }
}
</style>
""", unsafe_allow_html=True)



# =====================================================
# CSV AND DATA HELPERS
# =====================================================

def load_csv(path, columns=None):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass

    return pd.DataFrame(columns=columns) if columns else pd.DataFrame()


def save_csv_row(path, row):
    old = load_csv(path)
    updated = pd.concat(
        [old, pd.DataFrame([row])],
        ignore_index=True
    )
    updated.to_csv(path, index=False, encoding="utf-8-sig")
    return updated


def _is_missing_or_blank(value):
    """Safe scalar missing-value check for mixed and pandas extension dtypes."""
    if value is None:
        return True

    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return True
    except (TypeError, ValueError):
        pass

    return (
        isinstance(value, str)
        and value.strip().casefold() in {"", "nan", "none", "null"}
    )


def _safe_text_series(series):
    """Convert mixed values to ordinary Python strings."""
    return series.map(
        lambda value: "" if _is_missing_or_blank(value) else str(value)
    )


def flatten_research_for_analytics(frame):
    """Expand Supabase JSONB result groups."""
    import json

    data = (
        frame.copy()
        if isinstance(frame, pd.DataFrame)
        else pd.DataFrame(frame)
    )

    data = data.reset_index(drop=True)

    nested_columns = [
        "physicochemical_results",
        "microbiological_results",
        "contaminant_results",
        "process_data",
        "sensory_results",
        "packaging_results",
    ]

    for column in nested_columns:
        if column not in data.columns:
            continue

        parsed_rows = []

        for raw in data[column].tolist():
            value = raw

            if isinstance(raw, str) and raw.strip():
                try:
                    value = json.loads(raw)
                except (TypeError, ValueError):
                    value = {}

            if not isinstance(value, dict):
                value = {}

            parsed_rows.append(value)

        field_names = []

        for item in parsed_rows:
            for field in item:
                if field not in field_names:
                    field_names.append(field)

        for field in field_names:
            incoming = [item.get(field) for item in parsed_rows]

            if field not in data.columns:
                data[field] = pd.Series(
                    incoming,
                    index=data.index,
                    dtype="object"
                )
                continue

            current = data[field].tolist()

            for index, old_value in enumerate(current):
                if _is_missing_or_blank(old_value) and index < len(incoming):
                    current[index] = incoming[index]

            data[field] = pd.Series(
                current,
                index=data.index,
                dtype="object"
            )

    return data


def load_research_analytics_data():
    """Load observations from Supabase, then use local CSV as fallback."""

    local_data = load_csv(RESEARCH_CSV_FILE)

    try:
        remote_records = get_research_observations(limit=1000)

    except Exception as error:
        if not local_data.empty:
            try:
                return (
                    flatten_research_for_analytics(local_data),
                    "CSV local (secours)",
                    error
                )
            except Exception as local_error:
                return pd.DataFrame(), "Aucune source", local_error

        return pd.DataFrame(), "Aucune source", error

    if remote_records:
        try:
            remote_data = flatten_research_for_analytics(
                pd.DataFrame(remote_records)
            )

            if not remote_data.empty:
                return remote_data, "Supabase", None

        except Exception as error:
            if not local_data.empty:
                try:
                    return (
                        flatten_research_for_analytics(local_data),
                        "CSV local (secours)",
                        error
                    )
                except Exception as local_error:
                    return pd.DataFrame(), "Aucune source", local_error

            return pd.DataFrame(), "Aucune source", error

    if not local_data.empty:
        try:
            return (
                flatten_research_for_analytics(local_data),
                "CSV local (Supabase vide)",
                None
            )
        except Exception as error:
            return pd.DataFrame(), "Aucune source", error

    return pd.DataFrame(), "Aucune source", None


def show_error(title, error):
    """Display useful diagnostics without exposing credentials."""

    st.error(title)
    st.caption(f"Type d'erreur : {type(error).__name__}")

    fields = (
        ("Code", getattr(error, "code", None)),
        ("Message", getattr(error, "message", None)),
        ("Détails", getattr(error, "details", None)),
        ("Indice", getattr(error, "hint", None)),
    )

    shown = False

    for label, value in fields:
        if value:
            st.write(f"**{label} :** {value}")
            shown = True

    if not shown:
        message = str(error)

        message = re.sub(
            r"sb_(?:secret|publishable)_[A-Za-z0-9_-]+",
            "[SECRET MASQUÉ]",
            message
        )

        message = re.sub(
            r"eyJ[A-Za-z0-9._-]{20,}",
            "[TOKEN MASQUÉ]",
            message
        )

        st.caption(
            message[:1200]
            if message
            else "Aucun détail supplémentaire disponible."
        )


# =====================================================
# LOAD ORIGINAL DATA
# =====================================================

history = load_csv(CSV_FILE)
research_data = load_csv(RESEARCH_CSV_FILE, RESEARCH_COLUMNS)


# =====================================================
# BRAND HEADER
# =====================================================

if os.path.exists(LOGO_FILE):
    logo_left, logo_center, logo_right = st.columns([1, 1, 1])

    with logo_center:
        st.image(LOGO_FILE, width=170)

st.markdown(
    '<div class="foodnexa-brand-title">FOODNEXA</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="foodnexa-brand-subtitle">'
    'FOOD SAFETY • RISK INTELLIGENCE'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="foodnexa-line"></div>',
    unsafe_allow_html=True
)


# =====================================================
# SIDEBAR NAVIGATION
# =====================================================

with st.sidebar:
    st.markdown("## 🛡️ FOODNEXA")
    st.caption("FOOD SAFETY / RISK INTELLIGENCE")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🔬 Nouvelle analyse",
            "🧪 Research Data",
            "📊 Research Analytics",
            "🧹 Scientific Data Cleaning",
            "📁 Historique",
            "🧬 Research Prototype",
        ]
    )

    st.divider()
    st.info("Current research case:\n\n🥛 Lait pasteurisé")
    st.caption("FOODNEXA v1.0")


# =====================================================
# ENTERPRISE DASHBOARD
# =====================================================

if page == "📊 Dashboard":

    dashboard_research, dashboard_source, dashboard_error = (
        load_research_analytics_data()
    )

    dashboard_quality = None

    if not dashboard_research.empty:
        try:
            dashboard_quality = generate_quality_report(
                dashboard_research
            )
        except Exception:
            dashboard_quality = None

    dashboard_pipeline = {
        "Risk Assessment Engine": True,
        "Research Dataset": not dashboard_research.empty,
        "Data Quality Engine": dashboard_quality is not None,
        "Scientific Data Cleaning": None,
        "Research Analytics": not dashboard_research.empty,
        "Supabase": dashboard_source == "Supabase",
    }

    if dashboard_source.startswith("CSV local"):
        st.warning(
            "Les données de recherche affichées proviennent du CSV local "
            "de secours et non de Supabase."
        )

    if dashboard_error is not None:
        st.warning(
            "La source Supabase n'a pas pu être confirmée. "
            "Vérifiez la connexion si nécessaire."
        )

    render_dashboard(
        history_data=history,
        research_data=dashboard_research,
        quality_report=dashboard_quality,
        pipeline_status=dashboard_pipeline,
    )


# =====================================================
# NEW ANALYSIS + SUPABASE
# =====================================================

elif page == "🔬 Nouvelle analyse":

    st.title("🔬 Nouvelle analyse FOODNEXA")
    st.write(
        "Évaluation expérimentale du risque pour un lot de lait pasteurisé."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Identification")

        batch_id = st.text_input(
            "Numéro de lot",
            placeholder="Exemple : LOT-006"
        )

        product_name = st.text_input(
            "Nom du produit",
            value="Lait pasteurisé"
        )

        st.subheader("🌡️ Conditions de stockage")

        temperature = st.number_input(
            "Température de stockage (°C)",
            min_value=-20.0,
            max_value=50.0,
            value=4.0,
            step=0.1
        )

        storage_days = st.number_input(
            "Durée de stockage (jours)",
            min_value=0,
            max_value=365,
            value=2,
            step=1
        )

    with col2:
        st.subheader("🧪 Paramètres qualité")

        ph = st.number_input(
            "Valeur pH",
            min_value=0.0,
            max_value=14.0,
            value=6.6,
            step=0.1
        )

        st.subheader("🧼 Contrôles")

        cold_chain_broken = st.checkbox(
            "Interruption de la chaîne du froid"
        )

        hygiene_controlled = st.checkbox(
            "Conditions d’hygiène maîtrisées",
            value=True
        )

        pasteurized = st.checkbox(
            "Produit pasteurisé",
            value=True
        )

    if st.button(
        "🚀 LANCER L'ANALYSE FOODNEXA",
        width="stretch",
        type="primary"
    ):

        if not batch_id.strip() or not product_name.strip():
            st.warning(
                "Veuillez saisir le numéro de lot et le nom du produit."
            )
            st.stop()

        try:
            report = assess_dairy_food_safety_risk(
                temperature=temperature,
                storage_days=storage_days,
                ph=ph,
                cold_chain_broken=cold_chain_broken,
                hygiene_controlled=hygiene_controlled,
                pasteurized=pasteurized,
                batch_id=batch_id.strip(),
                product_name=product_name.strip(),
            )

        except Exception as error:
            show_error(
                "Une erreur est survenue pendant l'analyse.",
                error
            )
            st.stop()

        st.success("✅ Analyse FOODNEXA terminée.")

        r1, r2, r3 = st.columns(3)

        r1.metric("RISK SCORE", f"{report['risk_score']}/100")
        r2.metric("RISK LEVEL", report["risk_level"])
        r3.metric("CONFIDENCE", f"{report['confidence']:.1f}%")

        if report["risk_level"] == "Élevé":
            st.error("🔴 RISQUE ÉLEVÉ")
        elif report["risk_level"] == "Modéré":
            st.warning("🟠 RISQUE MODÉRÉ")
        else:
            st.success("🟢 RISQUE FAIBLE")

        factor_names = {
            "temperature": "Température",
            "storage_duration": "Durée de stockage",
            "ph": "pH",
            "cold_chain": "Chaîne du froid",
            "hygiene": "Hygiène",
            "pasteurization": "Pasteurisation",
        }

        factor_data = [
            {
                "Facteur": factor_names.get(name, name),
                "Score": factor["score"],
                "Niveau": factor["level"],
                "Explication": factor["reason"],
            }
            for name, factor in report["factors"].items()
        ]

        st.subheader("🔎 Facteurs analysés")

        st.dataframe(
            pd.DataFrame(factor_data),
            width="stretch",
            hide_index=True
        )

        st.subheader("⚠️ Facteurs de risque détectés")

        if report["reasons"]:
            for reason in report["reasons"]:
                st.warning(reason)
        else:
            st.success("Aucun facteur de risque détecté.")

        st.subheader("💡 Recommandations")

        for recommendation in report["recommendations"]:
            st.info(recommendation)

        row = {
            "analysis_date": report["analysis_date"],
            "batch_id": report["batch_id"],
            "product_name": report["product_name"],
            "temperature_celsius": temperature,
            "storage_days": storage_days,
            "ph": ph,
            "cold_chain_broken": cold_chain_broken,
            "hygiene_controlled": hygiene_controlled,
            "pasteurized": pasteurized,
            "temperature_score": report["factors"]["temperature"]["score"],
            "storage_score": report["factors"]["storage_duration"]["score"],
            "ph_score": report["factors"]["ph"]["score"],
            "cold_chain_score": report["factors"]["cold_chain"]["score"],
            "hygiene_score": report["factors"]["hygiene"]["score"],
            "pasteurization_score": report["factors"]["pasteurization"]["score"],
            "risk_score": report["risk_score"],
            "risk_level": report["risk_level"],
            "confidence": report["confidence"],
            "reasons": (
                " | ".join(report["reasons"])
                if report["reasons"]
                else "Aucun facteur de risque détecté"
            ),
            "recommendations": " | ".join(report["recommendations"]),
        }

        try:
            save_csv_row(CSV_FILE, row)
            st.success(f"💾 Lot {batch_id} enregistré dans le CSV.")

        except Exception as error:
            show_error(
                "Analyse terminée, mais sauvegarde CSV impossible.",
                error
            )

        try:
            save_risk_assessment(
                batch_id=batch_id.strip(),
                product_name=product_name.strip(),
                risk_score=float(report["risk_score"]),
                risk_level=report["risk_level"],
                confidence=float(report["confidence"]),
                inputs={
                    "temperature_celsius": float(temperature),
                    "storage_days": int(storage_days),
                    "ph": float(ph),
                    "cold_chain_broken": bool(cold_chain_broken),
                    "hygiene_controlled": bool(hygiene_controlled),
                    "pasteurized": bool(pasteurized),
                },
                factor_scores={
                    name: factor["score"]
                    for name, factor in report["factors"].items()
                },
                reasons=report["reasons"],
                recommendations=report["recommendations"],
            )

            st.success("☁️ Analyse enregistrée dans Supabase.")

        except Exception as error:
            show_error(
                "Analyse locale conservée, mais sauvegarde Supabase échouée.",
                error
            )


# =====================================================
# RESEARCH DATA + SUPABASE - V2
# =====================================================

elif page == "🧪 Research Data":

    st.title("🧪 FOODNEXA Research Data | V2")

    st.write(
        "Collecte multi-domaines des données physico-chimiques, "
        "microbiologiques, contaminants, procédé, emballage et traçabilité."
    )

    st.warning(
        "Renseignez uniquement les résultats réellement mesurés. "
        "Laissez vide tout paramètre non analysé : une valeur absente "
        "n'est jamais interprétée comme zéro ou comme un résultat conforme."
    )

    def optional_number(label, key, help_text=None):
        raw = st.text_input(
            label,
            key=key,
            placeholder="Laisser vide si non mesuré",
            help=help_text
        )

        if not raw.strip():
            return None

        try:
            value = float(raw.strip().replace(",", "."))

            if not pd.notna(value):
                return None

            return value

        except ValueError:
            st.error(f"Valeur numérique invalide pour : {label}")
            st.stop()

    def optional_yes_no(label, key):
        choice = st.selectbox(
            label,
            ["Non renseigné", "Oui", "Non"],
            key=key
        )

        return (
            True if choice == "Oui"
            else False if choice == "Non"
            else None
        )

    with st.form("foodnexa_research_v2_form", clear_on_submit=False):

        st.subheader("1. Identification et traçabilité de l'échantillon")

        id1, id2, id3 = st.columns(3)

        with id1:
            research_batch_id = st.text_input(
                "ID du lot *",
                placeholder="Ex. LOT-2026-001"
            )

            research_product = st.text_input(
                "Nom du produit *",
                value="Lait pasteurisé"
            )

            product_category = st.selectbox(
                "Catégorie du produit",
                [
                    "Produits laitiers",
                    "Produits végétaux",
                    "Céréales et farines",
                    "Viandes et volailles",
                    "Poissons et produits de la mer",
                    "Boissons",
                    "Huiles et matières grasses",
                    "Autre",
                ]
            )

        with id2:
            sample_reference = st.text_input("Référence de l'échantillon")
            supplier = st.text_input("Fournisseur")
            sampling_date = st.date_input("Date de prélèvement", value=None)

        with id3:
            analysis_date = st.date_input("Date d'analyse", value=None)
            laboratory = st.text_input("Laboratoire")
            analyst = st.text_input("Analyste")

        st.divider()
        st.subheader("2. Paramètres physico-chimiques")

        pcols = st.columns(4)

        phys_labels = [
            ("Température (°C)", "temperature_celsius"),
            ("Durée stockage (jours)", "storage_days"),
            ("pH", "ph"),
            ("Humidité (%)", "humidity_percent"),
            ("Matière sèche (%)", "dry_matter_percent"),
            ("Cendres (%)", "ash_percent"),
            ("Protéines (%)", "protein_percent"),
            ("Matières grasses (%)", "fat_percent"),
            ("Acidité titrable", "titratable_acidity"),
            ("Densité", "density"),
            ("Conductivité", "conductivity"),
            ("Viscosité", "viscosity"),
            ("Brix (°Bx)", "brix"),
            ("Sel (%)", "salt_percent"),
            ("Granulométrie", "particle_size"),
        ]

        phys_values = {}

        for i, (label, field) in enumerate(phys_labels):
            with pcols[i % 4]:
                phys_values[field] = optional_number(
                    label,
                    f"v2_{field}"
                )

        st.divider()
        st.subheader("3. Analyses microbiologiques")

        mcols = st.columns(4)

        micro_labels = [
            ("Flore totale / TVC", "total_viable_count"),
            ("Enterobacteriaceae", "enterobacteriaceae_count"),
            ("Coliformes", "coliform_count"),
            ("E. coli", "e_coli_count"),
            ("Levures et moisissures", "yeast_mould_count"),
            ("Staphylococcus aureus", "staphylococcus_aureus_count"),
            ("Bacillus cereus", "bacillus_cereus_count"),
            ("Listeria monocytogenes", "listeria_monocytogenes_count"),
        ]

        micro_values = {}

        for i, (label, field) in enumerate(micro_labels):
            with mcols[i % 4]:
                micro_values[field] = optional_number(
                    label,
                    f"v2_{field}",
                    "Indiquer l'unité dans Analyse units."
                )

        salmonella = st.selectbox(
            "Salmonella",
            ["Non analysée", "Non détectée", "Détectée"],
            key="v2_salmonella"
        )

        st.divider()
        st.subheader("4. Contaminants chimiques")

        ccols = st.columns(4)

        contaminant_labels = [
            ("Résidus de pesticides", "pesticide_residue"),
            ("Plomb", "lead"),
            ("Cadmium", "cadmium"),
            ("Mercure", "mercury"),
            ("Arsenic", "arsenic"),
            ("Aflatoxines", "aflatoxin"),
            ("Mycotoxines (autres)", "mycotoxin"),
        ]

        contaminant_values = {}

        for i, (label, field) in enumerate(contaminant_labels):
            with ccols[i % 4]:
                contaminant_values[field] = optional_number(
                    label,
                    f"v2_{field}",
                    "Respecter l'unité déclarée, par exemple µg/kg ou mg/kg."
                )

        st.divider()
        st.subheader("5. Procédé et chaîne du froid")

        prcols = st.columns(4)

        process_labels = [
            ("Température de traitement (°C)", "processing_temperature_celsius"),
            ("Temps de traitement (min)", "processing_time_minutes"),
            ("Température de refroidissement (°C)", "cooling_temperature_celsius"),
            ("Temps de refroidissement (min)", "cooling_time_minutes"),
        ]

        process_values = {}

        for i, (label, field) in enumerate(process_labels):
            with prcols[i]:
                process_values[field] = optional_number(
                    label,
                    f"v2_{field}"
                )

        b1, b2, b3 = st.columns(3)

        with b1:
            cold_chain = optional_yes_no(
                "Rupture de chaîne du froid ?",
                "v2_cold_chain"
            )

        with b2:
            hygiene = optional_yes_no(
                "Hygiène maîtrisée ?",
                "v2_hygiene"
            )

        with b3:
            pasteurized = optional_yes_no(
                "Produit pasteurisé ?",
                "v2_pasteurized"
            )

        st.divider()
        st.subheader("6. Contrôle sensoriel et emballage")

        s1, s2, s3 = st.columns(3)

        with s1:
            sensory_status = st.selectbox(
                "État sensoriel",
                ["Non évalué", "Conforme", "Non conforme"],
                key="v2_sensory"
            )

        with s2:
            net_weight = optional_number("Poids net", "v2_net_weight")
            seal_integrity = optional_number(
                "Intégrité du scellage (score)",
                "v2_seal_integrity"
            )

        with s3:
            vacuum_level = optional_number(
                "Niveau de vide",
                "v2_vacuum_level"
            )

            nonconformity = optional_yes_no(
                "Non-conformité détectée ?",
                "v2_nonconformity"
            )

        st.divider()
        st.subheader("7. Méthodes, unités et référence réglementaire")

        a1, a2, a3 = st.columns(3)

        with a1:
            analysis_units = st.text_input(
                "Unités des analyses",
                placeholder="Ex. UFC/g ; mg/kg ; %"
            )

        with a2:
            analysis_methods = st.text_input(
                "Méthodes d'analyse",
                placeholder="Ex. ISO / méthode interne"
            )

        with a3:
            limits_reference = st.text_input(
                "Référence des limites applicables",
                placeholder="Norme / règlement / cahier des charges"
            )

        expert_risk_label = st.selectbox(
            "Étiquette de risque attribuée par expert",
            ["Non attribué", "Faible", "Modéré", "Élevé"]
        )

        notes = st.text_area(
            "Notes complémentaires",
            placeholder=(
                "Conditions de prélèvement, observations, "
                "incertitudes, commentaires..."
            )
        )

        submitted = st.form_submit_button(
            "💾 ENREGISTRER L'OBSERVATION V2",
            type="primary",
            use_container_width=True
        )

    if submitted:

        if not research_batch_id.strip() or not research_product.strip():
            st.error(
                "L'ID du lot et le nom du produit sont obligatoires."
            )
            st.stop()

        physicochemical_results = {
            k: v for k, v in phys_values.items() if v is not None
        }

        microbiological_results = {
            k: v for k, v in micro_values.items() if v is not None
        }

        contaminant_results = {
            k: v for k, v in contaminant_values.items() if v is not None
        }

        process_data = {
            k: v for k, v in process_values.items() if v is not None
        }

        packaging_results = {
            k: v
            for k, v in {
                "net_weight": net_weight,
                "seal_integrity_score": seal_integrity,
                "vacuum_level": vacuum_level,
            }.items()
            if v is not None
        }

        sensory_results = {
            "sensory_status": (
                None if sensory_status == "Non évalué"
                else sensory_status
            ),
            "nonconformity_detected": nonconformity,
        }

        observation = {
            "batch_id": research_batch_id.strip(),
            "product_name": research_product.strip(),
            "product_category": product_category,
            "sample_reference": sample_reference or None,
            "supplier": supplier or None,
            "sampling_date": (
                sampling_date.isoformat() if sampling_date else None
            ),
            "analysis_date": (
                analysis_date.isoformat() if analysis_date else None
            ),
            "laboratory": laboratory or None,
            "analyst": analyst or None,
            "temperature_celsius": phys_values.get("temperature_celsius"),
            "storage_days": phys_values.get("storage_days"),
            "ph": phys_values.get("ph"),
            "cold_chain_broken": cold_chain,
            "hygiene_controlled": hygiene,
            "pasteurized": pasteurized,
            "total_viable_count": micro_values.get("total_viable_count"),
            "enterobacteriaceae_count": micro_values.get("enterobacteriaceae_count"),
            "coliform_count": micro_values.get("coliform_count"),
            "staphylococcus_aureus_count": micro_values.get("staphylococcus_aureus_count"),
            "salmonella_detected": (
                True if salmonella == "Détectée"
                else False if salmonella == "Non détectée"
                else None
            ),
            "sensory_status": (
                None if sensory_status == "Non évalué"
                else sensory_status
            ),
            "nonconformity_detected": nonconformity,
            "expert_risk_label": (
                None if expert_risk_label == "Non attribué"
                else expert_risk_label
            ),
            "process_data": process_data,
            "physicochemical_results": physicochemical_results,
            "microbiological_results": microbiological_results,
            "contaminant_results": contaminant_results,
            "sensory_results": sensory_results,
            "packaging_results": packaging_results,
            "analysis_units": analysis_units or None,
            "analysis_methods": analysis_methods or None,
            "applicable_limits_reference": limits_reference or None,
            "notes": notes or None,
        }

        csv_row = {
            k: v for k, v in observation.items()
            if not isinstance(v, dict)
        }

        for group in (
            physicochemical_results,
            microbiological_results,
            contaminant_results,
            process_data,
            packaging_results
        ):
            csv_row.update(group)

        csv_row["salmonella_detected"] = salmonella

        csv_row["nonconformity_detected"] = (
            "Non renseigné"
            if nonconformity is None
            else "Oui" if nonconformity
            else "Non"
        )

        try:
            save_csv_row(RESEARCH_CSV_FILE, csv_row)
            st.success("Observation ajoutée au Research Dataset local.")

        except Exception as error:
            show_error("Échec de la sauvegarde CSV.", error)

        try:
            save_research_observation(observation)
            st.success("Observation enregistrée dans Supabase.")

        except Exception as error:
            show_error(
                "La sauvegarde locale est conservée, "
                "mais Supabase a refusé l'observation.",
                error
            )

    st.divider()
    st.subheader("📚 Research Dataset")

    research_view = load_csv(RESEARCH_CSV_FILE)

    if not research_view.empty:

        st.metric("Nombre d'observations", len(research_view))

        st.dataframe(
            research_view,
            width="stretch",
            hide_index=True
        )

        st.download_button(
            "⬇️ Télécharger Research Dataset (CSV)",
            data=research_view.to_csv(index=False).encode("utf-8-sig"),
            file_name=RESEARCH_CSV_FILE,
            mime="text/csv",
            use_container_width=True
        )

        st.info(
            "Les lignes représentent des observations/échantillons. "
            "Un même lot peut apparaître plusieurs fois."
        )

        try:
            quality = generate_quality_report(research_view)

            st.subheader("🔎 Data Quality Engine V2")

            q1, q2, q3, q4 = st.columns(4)

            q1.metric(
                "Observations",
                quality.get("rows", len(research_view))
            )

            q2.metric(
                "Colonnes",
                quality.get("columns", len(research_view.columns))
            )

            q3.metric(
                "Dataset Quality Score",
                f"{quality.get('quality_score', 0):.1f}%"
            )

            q4.metric(
                "Doublons exacts",
                quality.get("duplicates", 0)
            )

            v1, v2, v3 = st.columns(3)

            v1.metric(
                "Statut de validation",
                quality.get("validation_status", "Non évalué")
            )

            v2.metric(
                "Erreurs techniques",
                quality.get("validation_errors", 0)
            )

            v3.metric(
                "Alertes à vérifier",
                quality.get("validation_warnings", 0)
            )

            if quality.get("validation_errors", 0):
                st.error(
                    "Des erreurs techniques ont été détectées. "
                    "Vérifiez les lignes signalées avant toute analyse scientifique."
                )

            elif quality.get("validation_warnings", 0):
                st.warning(
                    "Certaines informations demandent une vérification "
                    "ou un complément documentaire."
                )

            else:
                st.success(
                    "Aucune anomalie détectée par les contrôles actuellement activés."
                )

            st.caption(
                quality.get(
                    "interpretation",
                    "Score documentaire uniquement."
                )
            )

            st.info(
                quality.get(
                    "message",
                    "Les champs non renseignés ne sont pas considérés "
                    "comme des résultats négatifs."
                )
            )

            profile_report = quality.get("product_profiles", {})

            st.subheader("🧩 Product-Specific Validation Profiles")

            st.caption(
                profile_report.get(
                    "message",
                    "Les priorités dépendent de la catégorie du produit."
                )
            )

            profile_rows = []

            for profile in profile_report.get("profiles", []):
                profile_rows.append({
                    "Catégorie": profile.get("category", "—"),
                    "Profil": profile.get("profile", "Profil général"),
                    "Observations": profile.get("observations", 0),
                    "Couverture des champs prioritaires (%)": profile.get(
                        "coverage_percent", "N/D"
                    ),
                    "Champs prioritaires présents": (
                        ", ".join(profile.get("measured_priority_fields", []))
                        or "Aucun résultat renseigné"
                    ),
                    "Domaines prioritaires": ", ".join(
                        profile.get("priority_domains", [])
                    ),
                })

            if profile_rows:
                st.dataframe(
                    pd.DataFrame(profile_rows),
                    width="stretch",
                    hide_index=True
                )

                for profile in profile_report.get("profiles", []):
                    with st.expander(
                        f"Détails — {profile.get('category', 'Catégorie')}"
                    ):
                        st.write(profile.get("note", "Profil indicatif."))

                        st.caption(
                            "Champs prioritaires identifiés : "
                            + (
                                ", ".join(profile.get("priority_fields", []))
                                or "Aucun champ spécifique reconnu dans le CSV."
                            )
                        )

            else:
                st.caption(
                    "Ajoutez une catégorie de produit pour activer "
                    "les profils spécialisés."
                )

            components = quality.get("score_components", {})

            if components:
                st.markdown("**Composition du score**")

                component_df = pd.DataFrame([
                    {
                        "Dimension": k,
                        "Couverture / cohérence (%)": v
                    }
                    for k, v in components.items()
                ])

                st.dataframe(
                    component_df,
                    width="stretch",
                    hide_index=True
                )

            with st.expander(
                "Voir la couverture des analyses par domaine",
                expanded=True
            ):

                group_rows = []

                for group_name, details in quality.get(
                    "coverage", {}
                ).get("Analyses par domaine", {}).items():

                    group_rows.append({
                        "Domaine": group_name,
                        "Champs disponibles dans le fichier": len(
                            details.get("fields", [])
                        ),
                        "Valeurs renseignées": details.get("available", 0),
                        "Valeurs possibles": details.get("possible", 0),
                        "Couverture (%)": details.get("percent", 0.0),
                    })

                if group_rows:
                    st.dataframe(
                        pd.DataFrame(group_rows),
                        width="stretch",
                        hide_index=True
                    )
                else:
                    st.caption(
                        "Aucun champ analytique reconnu dans les colonnes actuelles."
                    )

            issues = quality.get("issues", [])

            st.markdown(
                f"**Alertes techniques à vérifier : "
                f"{quality.get('issue_count', len(issues))}**"
            )

            if issues:
                st.dataframe(
                    pd.DataFrame(issues),
                    width="stretch",
                    hide_index=True
                )
            else:
                st.success(
                    "Aucune incohérence technique détectée "
                    "dans les contrôles appliqués."
                )

            st.caption(
                "Les analyses non réalisées restent non testées. "
                "Les seuils réglementaires ne sont pas appliqués automatiquement : "
                "ils dépendent du produit, de la méthode, de l'unité "
                "et de la réglementation de référence."
            )

        except Exception as error:
            show_error(
                "Le contrôle qualité du dataset a rencontré une erreur.",
                error
            )

    else:
        st.info(
            "Aucune observation locale pour le moment. "
            "Ajoutez un premier échantillon ci-dessus."
        )


# =====================================================
# RESEARCH ANALYTICS
# =====================================================

elif page == "📊 Research Analytics":

    st.title("📊 FOODNEXA Research Analytics V2.1")

    st.write(
        "Statistiques descriptives multi-domaines, calculées uniquement "
        "sur les résultats réellement renseignés."
    )

    st.warning(
        "Analyse exploratoire uniquement : elle ne constitue pas "
        "un modèle prédictif validé et ne remplace pas les analyses "
        "de laboratoire ni l'interprétation réglementaire."
    )

    data, data_source, source_error = load_research_analytics_data()

    if data_source == "Supabase":
        st.caption(
            "Source des données : Supabase — base centrale des observations."
        )

    elif data_source.startswith("CSV local"):
        st.caption(f"Source des données : {data_source}.")

        if source_error is not None:
            st.warning(
                "Supabase n'a pas pu être interrogé. "
                "Les statistiques affichées proviennent du fichier CSV local de secours."
            )

    if data.empty:

        if source_error is not None:
            show_error(
                "Impossible de charger ou traiter les données de recherche "
                "depuis Supabase et aucun CSV local exploitable n'est disponible.",
                source_error
            )

        elif data_source == "CSV local (Supabase vide)":
            st.info(
                "Supabase ne contient pas encore d'observation. "
                "Les données locales sont affichées en attendant."
            )

        else:
            st.info(
                "Aucune donnée disponible. Ajoutez des observations dans Research Data."
            )

    else:

        if "product_category" in data.columns:
            category_values = _safe_text_series(
                data["product_category"]
            ).str.strip()

            categories = ["Toutes les catégories"] + sorted([
                v for v in category_values.unique().tolist() if v
            ])

            selected_category = st.selectbox(
                "Filtrer par catégorie",
                categories
            )

            if selected_category != "Toutes les catégories":
                data = data[category_values == selected_category]

        if "product_name" in data.columns:
            product_values = _safe_text_series(
                data["product_name"]
            ).str.strip()

            products = ["Tous les produits"] + sorted([
                v for v in product_values.unique().tolist() if v
            ])

            selected_product = st.selectbox(
                "Filtrer par produit",
                products
            )

            if selected_product != "Tous les produits":
                data = data[product_values == selected_product]

        st.divider()

        total = len(data)

        if total == 0:
            st.info(
                "Aucune observation ne correspond aux filtres sélectionnés."
            )

        else:

            def _normalise_label(value):
                text = (
                    ""
                    if _is_missing_or_blank(value)
                    else str(value).strip().casefold()
                )

                return {
                    "faible": "Faible",
                    "low": "Faible",
                    "modere": "Modéré",
                    "modéré": "Modéré",
                    "moderate": "Modéré",
                    "medium": "Modéré",
                    "eleve": "Élevé",
                    "élevé": "Élevé",
                    "high": "Élevé",
                }.get(text, "")

            def _state_of_value(value):
                """Classify a cell without treating untested results as negative."""

                if _is_missing_or_blank(value):
                    return "Manquante"

                if isinstance(value, (dict, list, tuple)) and len(value) == 0:
                    return "Manquante"

                if isinstance(value, str):
                    token = value.strip().casefold()

                    not_applicable = {
                        "n/a", "na", "non applicable", "not applicable",
                        "sans objet"
                    }

                    not_tested = {
                        "non analysé", "non analysee", "non analysée",
                        "non testé", "non testée", "not tested",
                        "not tested / non analysé"
                    }

                    if token in not_applicable:
                        return "Non applicable"

                    if token in not_tested:
                        return "Non testé"

                    if token in {
                        "", "non renseigné", "non renseignee",
                        "non attribué", "non attribue"
                    }:
                        return "Manquante"

                return "Renseignée"

            label_raw = data.get(
                "expert_risk_label",
                pd.Series(index=data.index, dtype="object")
            )

            labels = label_raw.map(_normalise_label)

            valid_labels = labels[
                labels.isin(["Faible", "Modéré", "Élevé"])
            ]

            risk_count = int(len(valid_labels))

            salm = _safe_text_series(
                data.get(
                    "salmonella_detected",
                    pd.Series(index=data.index, dtype="object")
                )
            ).str.strip().str.casefold()

            salm_unknown = {
                "", "nan", "none", "non analysée", "non analysé",
                "non testé", "non testée", "not tested",
                "non renseigné", "n/a", "non applicable"
            }

            salm_valid = ~salm.isin(salm_unknown)

            salm_positive = {
                "détectée", "detectee", "oui", "true", "positive", "1"
            }

            srate = (
                float(salm[salm_valid].isin(salm_positive).mean() * 100)
                if salm_valid.any()
                else None
            )

            nonconf = _safe_text_series(
                data.get(
                    "nonconformity_detected",
                    pd.Series(index=data.index, dtype="object")
                )
            ).str.strip().str.casefold()

            nonconf_unknown = {
                "", "nan", "none", "non évaluée", "non evaluee",
                "non évalué", "non testé", "not tested",
                "non renseigné", "n/a", "non applicable"
            }

            nonconf_valid = ~nonconf.isin(nonconf_unknown)

            nonconf_positive = {
                "oui", "true", "non conforme", "non-conforme", "1"
            }

            nrate = (
                float(
                    nonconf[nonconf_valid].isin(nonconf_positive).mean() * 100
                )
                if nonconf_valid.any()
                else None
            )

            k1, k2, k3, k4 = st.columns(4)

            k1.metric("Observations", total)

            k2.metric(
                "Labels experts renseignés",
                f"{risk_count}/{total}"
            )

            k3.metric(
                "Salmonella détectée",
                "N/D" if srate is None else f"{srate:.1f}%",
                help=(
                    f"Calculé sur {int(salm_valid.sum())} résultats "
                    "interprétables, pas sur les tests non réalisés."
                )
            )

            k4.metric(
                "Non-conformités",
                "N/D" if nrate is None else f"{nrate:.1f}%",
                help=(
                    f"Calculé sur {int(nonconf_valid.sum())} "
                    "évaluations renseignées."
                )
            )

            st.subheader("Distribution des labels experts")

            if risk_count:

                label_order = ["Faible", "Modéré", "Élevé"]

                dist = valid_labels.value_counts().reindex(
                    label_order,
                    fill_value=0
                ).astype(int)

                dist_df = dist.rename_axis(
                    "Label expert"
                ).reset_index(name="Nombre d'observations")

                chart_col, table_col = st.columns([2, 1])

                with chart_col:
                    st.bar_chart(
                        dist_df.set_index("Label expert"),
                        horizontal=True
                    )

                with table_col:
                    st.dataframe(
                        dist_df,
                        width="stretch",
                        hide_index=True
                    )

            else:
                st.info(
                    "Aucun label expert attribué pour les observations filtrées. "
                    "Les labels manquants ne sont pas assimilés à un risque faible."
                )

            st.subheader(
                "Statistiques descriptives des paramètres numériques"
            )

            numeric_candidates = [
                "temperature_celsius", "storage_days", "ph",
                "humidity_percent", "moisture_percent",
                "dry_matter_percent", "ash_percent", "protein_percent",
                "fat_percent", "titratable_acidity", "density",
                "conductivity", "viscosity", "brix", "salt_percent",
                "particle_size", "total_viable_count",
                "enterobacteriaceae_count", "coliform_count",
                "e_coli_count", "yeast_mould_count",
                "staphylococcus_aureus_count", "bacillus_count",
                "lead", "cadmium", "mercury", "arsenic",
                "aflatoxin", "mycotoxin", "pesticide_residue",
            ]

            available_numeric = [
                column for column in numeric_candidates
                if column in data.columns
            ]

            if available_numeric:

                numeric_data = data[available_numeric].apply(
                    pd.to_numeric,
                    errors="coerce"
                )

                numeric_cols = [
                    column for column in available_numeric
                    if numeric_data[column].notna().any()
                ]

                if numeric_cols:

                    stats = numeric_data[numeric_cols].describe().T[
                        ["count", "mean", "50%", "min", "max"]
                    ]

                    stats = stats.rename(
                        columns={
                            "count": "n mesures",
                            "50%": "médiane",
                            "mean": "moyenne",
                            "min": "minimum",
                            "max": "maximum",
                        }
                    ).round(3)

                    stats["n mesures"] = stats["n mesures"].astype(int)

                    st.dataframe(
                        stats,
                        width="stretch"
                    )

                else:
                    st.info(
                        "Aucune mesure numérique exploitable "
                        "pour les filtres sélectionnés."
                    )

            else:
                st.info(
                    "Aucun paramètre numérique reconnu n'est disponible "
                    "pour les filtres sélectionnés."
                )

            st.subheader("Complétude et statut des données")

            field_groups = {
                "Traçabilité": [
                    "sample_reference", "supplier", "sampling_date",
                    "analysis_date", "laboratory", "analyst"
                ],
                "Physico-chimique": [
                    "temperature_celsius", "storage_days", "ph",
                    "humidity_percent", "moisture_percent",
                    "dry_matter_percent", "ash_percent", "protein_percent",
                    "fat_percent", "titratable_acidity", "density",
                    "conductivity", "viscosity", "brix", "salt_percent",
                    "particle_size"
                ],
                "Microbiologique": [
                    "total_viable_count", "enterobacteriaceae_count",
                    "coliform_count", "e_coli_count", "yeast_mould_count",
                    "staphylococcus_aureus_count", "bacillus_count",
                    "salmonella_detected"
                ],
                "Contaminants": [
                    "pesticide_residue", "lead", "cadmium", "mercury",
                    "arsenic", "aflatoxin", "mycotoxin"
                ],
                "Méthodes et références": [
                    "analysis_units", "analysis_methods",
                    "applicable_limits_reference"
                ],
                "Processus et sensoriel": [
                    "cold_chain_broken", "hygiene_controlled",
                    "pasteurized", "sensory_status",
                    "nonconformity_detected", "expert_risk_label"
                ],
                "Emballage": [
                    "packaging_integrity", "packaging_results"
                ],
            }

            completeness_rows = []

            for group_name, fields in field_groups.items():

                for field in fields:

                    if field not in data.columns:
                        continue

                    states = data[field].map(_state_of_value)
                    counts = states.value_counts()

                    filled = int(counts.get("Renseignée", 0))
                    not_tested = int(counts.get("Non testé", 0))
                    not_applicable = int(counts.get("Non applicable", 0))
                    missing = int(counts.get("Manquante", 0))

                    applicable_total = total - not_applicable

                    completeness = (
                        filled / applicable_total * 100
                        if applicable_total else None
                    )

                    completeness_rows.append({
                        "Domaine": group_name,
                        "Variable": field,
                        "Renseignées": filled,
                        "Non testées": not_tested,
                        "Non applicables": not_applicable,
                        "Manquantes": missing,
                        "Complétude (%)": (
                            "N/D"
                            if completeness is None
                            else round(completeness, 1)
                        ),
                    })

            if completeness_rows:

                completeness_df = pd.DataFrame(completeness_rows)

                st.dataframe(
                    completeness_df,
                    width="stretch",
                    hide_index=True
                )

                domain_rows = []

                for domain, group in completeness_df.groupby(
                    "Domaine",
                    sort=False
                ):

                    present = int(group["Renseignées"].sum())

                    possible = (
                        len(group) * total
                        - int(group["Non applicables"].sum())
                    )

                    domain_rows.append({
                        "Domaine": domain,
                        "Champs suivis": len(group),
                        "Valeurs renseignées": present,
                        "Valeurs attendues": possible,
                        "Complétude globale (%)": (
                            round(present / possible * 100, 1)
                            if possible else None
                        ),
                    })

                st.caption(
                    "Synthèse par domaine (la complétude mesure "
                    "la présence des données, pas leur conformité)."
                )

                st.dataframe(
                    pd.DataFrame(domain_rows),
                    width="stretch",
                    hide_index=True
                )

            else:
                st.info(
                    "Aucun champ de qualité reconnu n'est disponible "
                    "dans les observations filtrées."
                )

            st.info(
                "Important : 'Non testé', 'Non applicable' et 'Manquante' "
                "sont des états distincts. Une absence de résultat "
                "microbiologique ne signifie jamais 'non détecté'. "
                "La complétude ne prouve ni la conformité ni l'innocuité alimentaire."
            )


# =====================================================
# SCIENTIFIC DATA CLEANING ENGINE
# =====================================================

elif page == "🧹 Scientific Data Cleaning":

    st.title("🧹 FOODNEXA Scientific Data Cleaning Engine V1")

    st.write(
        "Prétraitement scientifique non destructif des observations "
        "avant les analyses avancées et le Machine Learning."
    )

    st.warning(
        "Le moteur crée une copie de travail. Les données originales "
        "dans Supabase et le CSV source ne sont jamais modifiés."
    )

    cleaning_source, cleaning_source_name, cleaning_source_error = (
        load_research_analytics_data()
    )

    if (
        cleaning_source_error is not None
        and cleaning_source_name == "Aucune source"
    ):

        show_error(
            "Impossible de charger les observations pour le nettoyage.",
            cleaning_source_error
        )

    elif cleaning_source.empty:

        st.info(
            "Aucune observation disponible. "
            "Ajoutez d'abord des données dans Research Data."
        )

    else:

        st.caption(
            f"Source : {cleaning_source_name} | "
            f"Observations originales : {len(cleaning_source)}"
        )

        cleaned_data, cleaning_audit, cleaning_summary = (
            clean_research_dataset(cleaning_source)
        )

        m1, m2, m3, m4 = st.columns(4)

        m1.metric(
            "Observations",
            cleaning_summary["rows_input"]
        )

        m2.metric(
            "Lignes à vérifier",
            cleaning_summary["rows_flagged"]
        )

        m3.metric(
            "Événements d'audit",
            cleaning_summary["audit_events"]
        )

        m4.metric(
            "Doublons détectés",
            cleaning_summary["duplicate_rows_flagged"]
        )

        st.subheader("1. Règles de prétraitement")

        st.markdown("""
        - Nettoyage des espaces et harmonisation des cellules textuelles vides.
        - Conversion numérique des paramètres reconnus, sans remplacer les valeurs absentes par zéro.
        - Vérification de plages techniques générales et signalement des valeurs atypiques.
        - Détection statistique IQR lorsque l'effectif le permet (au moins 4 mesures).
        - Détection des doublons exacts sans suppression automatique.
        - Conversion d'unité uniquement si l'unité est explicitement fournie et qu'une règle sûre existe.
        """)

        st.info(
            "Les plages sont des contrôles de plausibilité exploratoires, "
            "pas des limites réglementaires ni des critères de libération produit. "
            "Les valeurs signalées restent conservées pour vérification humaine."
        )

        st.subheader("2. Aperçu du dataset préparé")

        st.dataframe(
            cleaned_data,
            width="stretch",
            hide_index=True
        )

        st.download_button(
            "⬇️ Télécharger le dataset prétraité (CSV)",
            data=cleaned_data.to_csv(index=False).encode("utf-8-sig"),
            file_name="foodnexa_cleaned_research_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.subheader("3. Audit trail — historique des opérations")

        if cleaning_audit.empty:

            st.success(
                "Aucune transformation ou anomalie nécessitant "
                "un événement d'audit n'a été détectée."
            )

        else:

            st.dataframe(
                cleaning_audit,
                width="stretch",
                hide_index=True
            )

            st.download_button(
                "⬇️ Télécharger le journal d'audit (CSV)",
                data=cleaning_audit.to_csv(index=False).encode("utf-8-sig"),
                file_name="foodnexa_cleaning_audit.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.subheader("4. Garanties d'intégrité")

        g1, g2, g3 = st.columns(3)

        g1.metric("Suppression automatique", "Non")
        g2.metric("Imputation automatique", "Non")
        g3.metric("Source originale", "Préservée")

        st.caption(
            "Cellules manquantes conservées dans la copie de travail : "
            f"{cleaning_summary['missing_cells_retained']}. "
            "Aucune ligne n'est supprimée automatiquement."
        )


# =====================================================
# HISTORY
# =====================================================

elif page == "📁 Historique":

    st.title("📁 Historique FOODNEXA")

    if history.empty:

        st.info("Aucune analyse enregistrée.")

    else:

        st.write(
            f"Nombre total d'analyses : **{len(history)}**"
        )

        st.dataframe(
            history,
            width="stretch",
            hide_index=True
        )

        st.download_button(
            "⬇️ Télécharger le dataset CSV",
            data=history.to_csv(index=False).encode("utf-8-sig"),
            file_name="foodnexa_assessments.csv",
            mime="text/csv",
            width="stretch",
        )


# =====================================================
# RESEARCH PROTOTYPE
# =====================================================

elif page == "🧬 Research Prototype":

    st.title("🧬 FOODNEXA Research Prototype")

    with st.expander("☁️ Diagnostic de connexion Supabase"):

        if st.button(
            "Tester la connexion Supabase",
            key="test_supabase_connection"
        ):

            try:
                from foodnexa_supabase import test_supabase_connection

                test_result = test_supabase_connection()

                st.success(
                    "Connexion Supabase établie. "
                    "La table lots est accessible."
                )

                st.caption(
                    f"Lignes retournées : {test_result['rows_returned']}"
                )

            except Exception as error:
                show_error(
                    "Le test de connexion Supabase a échoué.",
                    error
                )

    st.info("""
    FOODNEXA est actuellement un prototype expérimental basé sur des règles explicables.
    L'objectif est de construire progressivement une base de données structurée pour étudier
    des approches statistiques et de Machine Learning.
    """)

    st.subheader("🔬 Architecture actuelle")

    architecture = pd.DataFrame({
        "Module": [
            "Data Input",
            "Risk Engine",
            "Explainability",
            "Risk Classification",
            "Recommendations",
            "Research Dataset",
            "Data Quality Engine",
            "Research Analytics",
            "Feature Engineering",
            "Machine Learning",
            "Validation",
        ],
        "État": [
            "Disponible",
            "Disponible",
            "Disponible",
            "Disponible",
            "Disponible",
            "Disponible",
            "Disponible",
            "Disponible",
            "À développer",
            "À développer",
            "À développer",
        ],
    })

    st.dataframe(
        architecture,
        width="stretch",
        hide_index=True
    )

    st.subheader("🎯 Objectif scientifique")

    st.write("""
    Construire un dataset de lots alimentaires contenant des variables de procédé, de stockage,
    de qualité et, lorsque disponibles, des résultats microbiologiques et des observations d'experts.
    """)

    st.subheader("🧠 Pipeline prévu")

    pipeline = pd.DataFrame({
        "Étape": [
            "Collecte des données",
            "Data Quality",
            "Nettoyage",
            "Research Analytics",
            "Feature Engineering",
            "Séparation Train/Test",
            "Entraînement ML",
            "Validation",
            "Évaluation",
            "Risk Prediction",
        ],
        "Statut": [
            "En cours",
            "Disponible",
            "À développer",
            "Disponible",
            "À développer",
            "À développer",
            "À développer",
            "À développer",
            "À développer",
            "À développer",
        ],
    })

    st.dataframe(
        pipeline,
        width="stretch",
        hide_index=True
    )

    st.warning(
        "Les résultats actuels sont expérimentaux. "
        "Ils ne remplacent pas les analyses de laboratoire "
        "ni les exigences réglementaires."
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.markdown("""
<div class="footer-text">
<b>FOODNEXA</b> — FOOD SAFETY / RISK INTELLIGENCE<br>
Intelligent Food Safety Risk Assessment<br><br>
Experimental decision-support prototype. Not a replacement for laboratory analysis,
regulatory requirements or quality-management decisions.
</div>
""", unsafe_allow_html=True)
