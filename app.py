import os
import streamlit as st
import pandas as pd
import re

from foodguard_engine import assess_dairy_food_safety_risk
from foodnexa_data_quality import generate_quality_report
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

st.markdown("""
<style>
:root {
    --foodnexa-navy: #102B46;
    --foodnexa-blue: #087E9B;
    --foodnexa-green: #16A078;
    --foodnexa-light: #FFFFFF;
    --foodnexa-white: #FFFFFF;
}

/* Pure white application background */
html, body, [data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.main, .block-container {
    background-color: #FFFFFF !important;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 2.5rem;
}

/* Strong, readable typography on the white background */
[data-testid="stAppViewContainer"] .main,
[data-testid="stAppViewContainer"] .main p,
[data-testid="stAppViewContainer"] .main li,
[data-testid="stAppViewContainer"] .main span,
[data-testid="stAppViewContainer"] .main small,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] {
    color: #1B2735 !important;
}

h1, h2, h3,
[data-testid="stAppViewContainer"] .main h1,
[data-testid="stAppViewContainer"] .main h2,
[data-testid="stAppViewContainer"] .main h3 {
    font-weight: 850 !important;
    opacity: 1 !important;
}
h1 { font-size: 1.42rem !important; color: #075B9A !important; }
h2 { font-size: 1.08rem !important; color: #08758F !important; }
h3 { font-size: 0.94rem !important; color: #16734F !important; }

/* Smaller, consistent text across the application */
[data-testid="stAppViewContainer"] .main p,
[data-testid="stAppViewContainer"] .main li,
[data-testid="stAppViewContainer"] .main [data-testid="stMarkdownContainer"],
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] {
    font-size: 0.84rem !important;
    line-height: 1.45 !important;
}
[data-testid="stAppViewContainer"] .main label,
[data-testid="stAppViewContainer"] .main .stSelectbox,
[data-testid="stAppViewContainer"] .main .stTextInput,
[data-testid="stAppViewContainer"] .main .stNumberInput,
[data-testid="stAppViewContainer"] .main .stDateInput,
[data-testid="stAppViewContainer"] .main .stTextArea {
    font-size: 0.80rem !important;
}
[data-testid="stAppViewContainer"] .main [data-testid="stCaptionContainer"] {
    font-size: 0.72rem !important;
}

/* Markdown emphasis and links remain visible on white */
[data-testid="stAppViewContainer"] .main strong,
[data-testid="stAppViewContainer"] .main b {
    color: #102B46 !important;
}
[data-testid="stAppViewContainer"] .main a {
    color: #006B8F !important;
    font-weight: 700 !important;
    text-decoration: underline;
}
.foodnexa-brand-title {
    text-align: center;
    color: #087E9B !important;
    font-size: clamp(2.8rem, 6vw, 4.7rem);
    line-height: 1.05;
    font-weight: 900;
    letter-spacing: 3px;
    margin: 5px 0 0;
    text-shadow: 0 3px 12px rgba(8,126,155,.14);
}
.foodnexa-brand-subtitle {
    text-align: center;
    color: #17324D !important;
    font-size: 0.9rem;
    font-weight: 800;
    letter-spacing: 2.2px;
    margin: 7px 0 18px;
}

.foodnexa-tagline {
    text-align: center;
    color: var(--foodnexa-blue) !important;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 1.2px;
    margin: 8px 0 18px;
}
.foodnexa-line {
    height: 4px;
    width: 100%;
    background: linear-gradient(90deg, #102B46, #087E9B, #16A078);
    border-radius: 10px;
    margin-bottom: 22px;
}
.footer-text {
    text-align: center;
    color: #64748B !important;
    font-size: 11px;
    line-height: 1.7;
    padding: 15px;
}

/* High-contrast colored metric cards */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #087E9B, #075B75) !important;
    border: 1px solid #087E9B !important;
    border-left: 5px solid #16A078 !important;
    border-radius: 13px !important;
    padding: 14px 16px !important;
    box-shadow: 0 4px 13px rgba(16, 43, 70, 0.13) !important;
}
div[data-testid="stMetric"] * {
    color: #FFFFFF !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.28rem !important;
    font-weight: 800 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    font-size: 0.72rem !important;
    font-weight: 700 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.68rem !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #102B46 !important;
}
section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    font-weight: 650 !important;
}

/* Input labels and fields */
.stTextInput label, .stNumberInput label, .stSelectbox label,
.stDateInput label, .stTextArea label, .stCheckbox label,
.stRadio label, .stMultiSelect label {
    color: #102B46 !important;
    opacity: 1 !important;
    font-weight: 700 !important;
    font-size: 0.78rem !important;
}

/* Buttons */
.stButton button, .stFormSubmitButton button, .stDownloadButton button {
    border-radius: 8px !important;
    font-weight: 700 !important;
    min-height: 38px;
}
.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {
    background: #087E9B !important;
    color: #FFFFFF !important;
    border: 1px solid #087E9B !important;
}

/* Tables */
div[data-testid="stDataFrame"] {
    border: 1px solid #D8E3EC !important;
    border-radius: 9px !important;
    overflow: hidden !important;
}
div[data-testid="stDataFrame"] * {
    color: #172B3A !important;
    font-size: 0.76rem !important;
}

/* Tabs and expanders */
.stTabs [data-baseweb="tab"] {
    font-weight: 700 !important;
}
details[data-testid="stExpander"] {
    border: 1px solid #D8E3EC !important;
    border-radius: 9px !important;
}

/* Alert boxes retain readable theme-specific contrast */
div[data-testid="stAlert"] p {
    font-weight: 550;
}

@media (max-width: 768px) {
    .block-container {
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }
    h1 { font-size: 1.18rem !important; }
    h2 { font-size: 0.98rem !important; }
    h3 { font-size: 0.88rem !important; }
    .foodnexa-brand-title { font-size: 2.8rem; letter-spacing: 2px; }
    .foodnexa-brand-subtitle { font-size: 0.72rem; letter-spacing: 1.2px; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.08rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


def load_csv(path, columns=None):
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            pass
    return pd.DataFrame(columns=columns) if columns else pd.DataFrame()


def save_csv_row(path, row):
    old = load_csv(path)
    updated = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
    updated.to_csv(path, index=False, encoding="utf-8-sig")
    return updated


def flatten_research_for_analytics(frame):
    """Expand Supabase JSONB result groups into columns for descriptive statistics."""
    import json

    data = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(frame)
    nested_columns = [
        "physicochemical_results", "microbiological_results",
        "contaminant_results", "process_data", "sensory_results",
        "packaging_results",
    ]
    for column in nested_columns:
        if column not in data.columns:
            continue
        expanded_rows = []
        for raw in data[column]:
            if isinstance(raw, dict):
                value = raw
            elif isinstance(raw, str) and raw.strip():
                try:
                    value = json.loads(raw)
                except (TypeError, ValueError):
                    value = {}
            else:
                value = {}
            expanded_rows.append(value if isinstance(value, dict) else {})
        expanded = pd.json_normalize(expanded_rows)
        for field in expanded.columns:
            target = field
            # Preserve an already populated top-level column; otherwise add the JSONB field.
            if target not in data.columns:
                data[target] = expanded[field].reindex(data.index)
            else:
                empty = data[target].isna() | data[target].astype(str).str.strip().isin(["", "nan", "None"])
                data.loc[empty, target] = expanded.loc[empty, field]
    return data


def load_research_analytics_data():
    """Prefer the central Supabase dataset; use local CSV only as a fallback."""
    local_data = load_csv(RESEARCH_CSV_FILE)
    try:
        remote_records = get_research_observations(limit=1000)
        remote_data = pd.DataFrame(remote_records)
        if not remote_data.empty:
            return flatten_research_for_analytics(remote_data), "Supabase", None
        if not local_data.empty:
            return flatten_research_for_analytics(local_data), "CSV local (Supabase vide)", None
        return pd.DataFrame(), "Aucune source", None
    except Exception as error:
        if not local_data.empty:
            return flatten_research_for_analytics(local_data), "CSV local (secours)", error
        return pd.DataFrame(), "Aucune source", error


def show_error(title, error):
    """Display useful Supabase/PostgREST diagnostics without exposing credentials."""
    st.error(title)
    st.caption(f"Type d'erreur : {type(error).__name__}")

    # Supabase PostgREST errors expose these fields. Never print request headers,
    # URLs containing tokens, or Streamlit Secrets.
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
        # Exception text can be useful for local validation errors; redact common
        # secret formats defensively before showing it.
        message = str(error)
        message = re.sub(r"sb_(?:secret|publishable)_[A-Za-z0-9_-]+", "[SECRET MASQUÉ]", message)
        message = re.sub(r"eyJ[A-Za-z0-9._-]{20,}", "[TOKEN MASQUÉ]", message)
        st.caption(message[:1200] if message else "Aucun détail supplémentaire disponible.")


history = load_csv(CSV_FILE)
research_data = load_csv(RESEARCH_CSV_FILE, RESEARCH_COLUMNS)

if os.path.exists(LOGO_FILE):
    logo_left, logo_center, logo_right = st.columns([1, 1, 1])
    with logo_center:
        st.image(LOGO_FILE, width=170)

st.markdown('<div class="foodnexa-brand-title">FOODNEXA</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="foodnexa-brand-subtitle">FOOD SAFETY • RISK INTELLIGENCE</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="foodnexa-line"></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🛡️ FOODNEXA")
    st.caption("FOOD SAFETY / RISK INTELLIGENCE")
    st.divider()
    page = st.radio("Navigation", [
        "📊 Dashboard", "🔬 Nouvelle analyse", "🧪 Research Data",
        "📊 Research Analytics", "📁 Historique", "🧬 Research Prototype"
    ])
    st.divider()
    st.info("Current research case:\n\n🥛 Lait pasteurisé")
    st.caption("FOODNEXA v1.0")


# =====================================================
# DASHBOARD
# =====================================================

if page == "📊 Dashboard":
    st.title("📊 FOODNEXA Intelligence Dashboard")
    st.write("Vue synthétique des évaluations expérimentales de risque.")
    if history.empty:
        st.info("Aucune analyse disponible. Lancez votre première analyse.")
    else:
        for col in ["risk_score", "confidence"]:
            if col in history:
                history[col] = pd.to_numeric(history[col], errors="coerce")
        levels = history.get("risk_level", pd.Series(dtype=str))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 Analyses", len(history))
        c2.metric("🔴 Risque élevé", int((levels == "Élevé").sum()))
        c3.metric("🟠 Risque modéré", int((levels == "Modéré").sum()))
        c4.metric("🟢 Risque faible", int((levels == "Faible").sum()))
        c5, c6 = st.columns(2)
        avg_score = history["risk_score"].mean() if "risk_score" in history else 0
        avg_conf = history["confidence"].mean() if "confidence" in history else 0
        c5.metric("📈 Risk Score moyen", f"{avg_score:.1f}/100")
        c6.metric("🎯 Confidence moyenne", f"{avg_conf:.1f}%")
        st.divider()
        st.subheader("📊 Distribution des niveaux de risque")
        distribution = pd.DataFrame({
            "Niveau": ["Faible", "Modéré", "Élevé"],
            "Nombre": [(levels == "Faible").sum(),
                       (levels == "Modéré").sum(),
                       (levels == "Élevé").sum()],
        })
        st.bar_chart(distribution.set_index("Niveau"))
        if {"batch_id", "risk_score"}.issubset(history.columns) and len(history) > 1:
            st.subheader("📈 Évolution des Risk Scores")
            st.line_chart(history.set_index("batch_id")[["risk_score"]])
        st.subheader("🕒 Dernières analyses")
        cols = [c for c in [
            "analysis_date", "batch_id", "product_name",
            "risk_score", "risk_level", "confidence"
        ] if c in history.columns]
        st.dataframe(history[cols].tail(10).iloc[::-1],
                     width="stretch", hide_index=True)


# =====================================================
# NEW ANALYSIS + SUPABASE
# =====================================================

elif page == "🔬 Nouvelle analyse":
    st.title("🔬 Nouvelle analyse FOODNEXA")
    st.write("Évaluation expérimentale du risque pour un lot de lait pasteurisé.")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Identification")
        batch_id = st.text_input("Numéro de lot", placeholder="Exemple : LOT-006")
        product_name = st.text_input("Nom du produit", value="Lait pasteurisé")
        st.subheader("🌡️ Conditions de stockage")
        temperature = st.number_input("Température de stockage (°C)",
                                      min_value=-20.0, max_value=50.0, value=4.0, step=0.1)
        storage_days = st.number_input("Durée de stockage (jours)",
                                       min_value=0, max_value=365, value=2, step=1)
    with col2:
        st.subheader("🧪 Paramètres qualité")
        ph = st.number_input("Valeur pH", min_value=0.0, max_value=14.0, value=6.6, step=0.1)
        st.subheader("🧼 Contrôles")
        cold_chain_broken = st.checkbox("Interruption de la chaîne du froid")
        hygiene_controlled = st.checkbox("Conditions d’hygiène maîtrisées", value=True)
        pasteurized = st.checkbox("Produit pasteurisé", value=True)

    if st.button("🚀 LANCER L'ANALYSE FOODNEXA",
                 width="stretch", type="primary"):
        if not batch_id.strip() or not product_name.strip():
            st.warning("Veuillez saisir le numéro de lot et le nom du produit.")
            st.stop()
        try:
            report = assess_dairy_food_safety_risk(
                temperature=temperature, storage_days=storage_days, ph=ph,
                cold_chain_broken=cold_chain_broken,
                hygiene_controlled=hygiene_controlled,
                pasteurized=pasteurized, batch_id=batch_id.strip(),
                product_name=product_name.strip(),
            )
        except Exception as error:
            show_error("Une erreur est survenue pendant l'analyse.", error)
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
            "temperature": "Température", "storage_duration": "Durée de stockage",
            "ph": "pH", "cold_chain": "Chaîne du froid",
            "hygiene": "Hygiène", "pasteurization": "Pasteurisation",
        }
        factor_data = [{
            "Facteur": factor_names.get(name, name),
            "Score": factor["score"], "Niveau": factor["level"],
            "Explication": factor["reason"],
        } for name, factor in report["factors"].items()]
        st.subheader("🔎 Facteurs analysés")
        st.dataframe(pd.DataFrame(factor_data), width="stretch", hide_index=True)

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
            "reasons": " | ".join(report["reasons"]) if report["reasons"]
                       else "Aucun facteur de risque détecté",
            "recommendations": " | ".join(report["recommendations"]),
        }

        # Local CSV backup is retained even if Supabase is unavailable.
        try:
            save_csv_row(CSV_FILE, row)
            st.success(f"💾 Lot {batch_id} enregistré dans le CSV.")
        except Exception as error:
            show_error("Analyse terminée, mais sauvegarde CSV impossible.", error)

        # Supabase risk assessment
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
            show_error("Analyse locale conservée, mais sauvegarde Supabase échouée.", error)


# =====================================================
# RESEARCH DATA + SUPABASE - V2
# =====================================================

elif page == "🧪 Research Data":
    st.title("🧪 FOODNEXA Research Data | V2")
    st.write("Collecte multi-domaines des données physico-chimiques, microbiologiques, contaminants, procédé, emballage et traçabilité.")
    st.warning("Renseignez uniquement les résultats réellement mesurés. Laissez vide tout paramètre non analysé : une valeur absente n'est jamais interprétée comme zéro ou comme un résultat conforme.")

    def optional_number(label, key, help_text=None):
        raw = st.text_input(label, key=key, placeholder="Laisser vide si non mesuré", help=help_text)
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
        choice = st.selectbox(label, ["Non renseigné", "Oui", "Non"], key=key)
        return True if choice == "Oui" else False if choice == "Non" else None

    with st.form("foodnexa_research_v2_form", clear_on_submit=False):
        st.subheader("1. Identification et traçabilité de l'échantillon")
        id1, id2, id3 = st.columns(3)
        with id1:
            research_batch_id = st.text_input("ID du lot *", placeholder="Ex. LOT-2026-001")
            research_product = st.text_input("Nom du produit *", value="Lait pasteurisé")
            product_category = st.selectbox("Catégorie du produit", ["Produits laitiers", "Produits végétaux", "Céréales et farines", "Viandes et volailles", "Poissons et produits de la mer", "Boissons", "Huiles et matières grasses", "Autre"])
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
            ("Température (°C)", "temperature_celsius"), ("Durée stockage (jours)", "storage_days"),
            ("pH", "ph"), ("Humidité (%)", "humidity_percent"),
            ("Matière sèche (%)", "dry_matter_percent"), ("Cendres (%)", "ash_percent"),
            ("Protéines (%)", "protein_percent"), ("Matières grasses (%)", "fat_percent"),
            ("Acidité titrable", "titratable_acidity"), ("Densité", "density"),
            ("Conductivité", "conductivity"), ("Viscosité", "viscosity"),
            ("Brix (°Bx)", "brix"), ("Sel (%)", "salt_percent"),
            ("Granulométrie", "particle_size"),
        ]
        phys_values = {}
        for i, (label, field) in enumerate(phys_labels):
            with pcols[i % 4]:
                phys_values[field] = optional_number(label, f"v2_{field}")

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
                micro_values[field] = optional_number(label, f"v2_{field}", "Indiquer l'unité dans Analyse units.")
        salmonella = st.selectbox("Salmonella", ["Non analysée", "Non détectée", "Détectée"], key="v2_salmonella")

        st.divider()
        st.subheader("4. Contaminants chimiques")
        ccols = st.columns(4)
        contaminant_labels = [
            ("Résidus de pesticides", "pesticide_residue"), ("Plomb", "lead"),
            ("Cadmium", "cadmium"), ("Mercure", "mercury"),
            ("Arsenic", "arsenic"), ("Aflatoxines", "aflatoxin"),
            ("Mycotoxines (autres)", "mycotoxin"),
        ]
        contaminant_values = {}
        for i, (label, field) in enumerate(contaminant_labels):
            with ccols[i % 4]:
                contaminant_values[field] = optional_number(label, f"v2_{field}", "Respecter l'unité déclarée, par exemple µg/kg ou mg/kg.")

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
                process_values[field] = optional_number(label, f"v2_{field}")
        b1, b2, b3 = st.columns(3)
        with b1:
            cold_chain = optional_yes_no("Rupture de chaîne du froid ?", "v2_cold_chain")
        with b2:
            hygiene = optional_yes_no("Hygiène maîtrisée ?", "v2_hygiene")
        with b3:
            pasteurized = optional_yes_no("Produit pasteurisé ?", "v2_pasteurized")

        st.divider()
        st.subheader("6. Contrôle sensoriel et emballage")
        s1, s2, s3 = st.columns(3)
        with s1:
            sensory_status = st.selectbox("État sensoriel", ["Non évalué", "Conforme", "Non conforme"], key="v2_sensory")
        with s2:
            net_weight = optional_number("Poids net", "v2_net_weight")
            seal_integrity = optional_number("Intégrité du scellage (score)", "v2_seal_integrity")
        with s3:
            vacuum_level = optional_number("Niveau de vide", "v2_vacuum_level")
            nonconformity = optional_yes_no("Non-conformité détectée ?", "v2_nonconformity")

        st.divider()
        st.subheader("7. Méthodes, unités et référence réglementaire")
        a1, a2, a3 = st.columns(3)
        with a1:
            analysis_units = st.text_input("Unités des analyses", placeholder="Ex. UFC/g ; mg/kg ; %")
        with a2:
            analysis_methods = st.text_input("Méthodes d'analyse", placeholder="Ex. ISO / méthode interne")
        with a3:
            limits_reference = st.text_input("Référence des limites applicables", placeholder="Norme / règlement / cahier des charges")
        expert_risk_label = st.selectbox("Étiquette de risque attribuée par expert", ["Non attribué", "Faible", "Modéré", "Élevé"])
        notes = st.text_area("Notes complémentaires", placeholder="Conditions de prélèvement, observations, incertitudes, commentaires...")
        submitted = st.form_submit_button("💾 ENREGISTRER L'OBSERVATION V2", type="primary", use_container_width=True)

    if submitted:
        if not research_batch_id.strip() or not research_product.strip():
            st.error("L'ID du lot et le nom du produit sont obligatoires.")
            st.stop()

        physicochemical_results = {k: v for k, v in phys_values.items() if v is not None}
        microbiological_results = {k: v for k, v in micro_values.items() if v is not None}
        contaminant_results = {k: v for k, v in contaminant_values.items() if v is not None}
        process_data = {k: v for k, v in process_values.items() if v is not None}
        packaging_results = {k: v for k, v in {
            "net_weight": net_weight, "seal_integrity_score": seal_integrity,
            "vacuum_level": vacuum_level,
        }.items() if v is not None}
        sensory_results = {
            "sensory_status": None if sensory_status == "Non évalué" else sensory_status,
            "nonconformity_detected": nonconformity,
        }
        observation = {
            "batch_id": research_batch_id.strip(), "product_name": research_product.strip(),
            "product_category": product_category, "sample_reference": sample_reference or None,
            "supplier": supplier or None,
            "sampling_date": sampling_date.isoformat() if sampling_date else None,
            "analysis_date": analysis_date.isoformat() if analysis_date else None,
            "laboratory": laboratory or None, "analyst": analyst or None,
            "temperature_celsius": phys_values.get("temperature_celsius"),
            "storage_days": phys_values.get("storage_days"), "ph": phys_values.get("ph"),
            "cold_chain_broken": cold_chain, "hygiene_controlled": hygiene,
            "pasteurized": pasteurized,
            "total_viable_count": micro_values.get("total_viable_count"),
            "enterobacteriaceae_count": micro_values.get("enterobacteriaceae_count"),
            "coliform_count": micro_values.get("coliform_count"),
            "staphylococcus_aureus_count": micro_values.get("staphylococcus_aureus_count"),
            "salmonella_detected": True if salmonella == "Détectée" else False if salmonella == "Non détectée" else None,
            "sensory_status": None if sensory_status == "Non évalué" else sensory_status,
            "nonconformity_detected": nonconformity,
            "expert_risk_label": None if expert_risk_label == "Non attribué" else expert_risk_label,
            "process_data": process_data, "physicochemical_results": physicochemical_results,
            "microbiological_results": microbiological_results,
            "contaminant_results": contaminant_results,
            "sensory_results": sensory_results, "packaging_results": packaging_results,
            "analysis_units": analysis_units or None, "analysis_methods": analysis_methods or None,
            "applicable_limits_reference": limits_reference or None, "notes": notes or None,
        }
        # Append-only local backup: repeated samples from the same lot are allowed.
        csv_row = {k: v for k, v in observation.items() if not isinstance(v, dict)}
        for group in (physicochemical_results, microbiological_results, contaminant_results, process_data, packaging_results):
            csv_row.update(group)
        csv_row["salmonella_detected"] = salmonella
        csv_row["nonconformity_detected"] = "Non renseigné" if nonconformity is None else "Oui" if nonconformity else "Non"
        try:
            save_csv_row(RESEARCH_CSV_FILE, csv_row)
            st.success("Observation ajoutée au Research Dataset local.")
        except Exception as error:
            show_error("Échec de la sauvegarde CSV.", error)
        try:
            save_research_observation(observation)
            st.success("Observation enregistrée dans Supabase.")
        except Exception as error:
            show_error("La sauvegarde locale est conservée, mais Supabase a refusé l'observation.", error)

    st.divider()
    st.subheader("📚 Research Dataset")
    research_view = load_csv(RESEARCH_CSV_FILE)
    if not research_view.empty:
        st.metric("Nombre d'observations", len(research_view))
        st.dataframe(research_view, width="stretch", hide_index=True)
        st.download_button("⬇️ Télécharger Research Dataset (CSV)", data=research_view.to_csv(index=False).encode("utf-8-sig"), file_name=RESEARCH_CSV_FILE, mime="text/csv", use_container_width=True)
        st.info("Les lignes représentent des observations/échantillons. Un même lot peut apparaître plusieurs fois.")
        try:
            quality = generate_quality_report(research_view)
            st.subheader("🔎 Data Quality Engine V2")
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Observations", quality.get("rows", len(research_view)))
            q2.metric("Colonnes", quality.get("columns", len(research_view.columns)))
            q3.metric("Dataset Quality Score", f"{quality.get('quality_score', 0):.1f}%")
            q4.metric("Doublons exacts", quality.get("duplicates", 0))

            v1, v2, v3 = st.columns(3)
            v1.metric("Statut de validation", quality.get("validation_status", "Non évalué"))
            v2.metric("Erreurs techniques", quality.get("validation_errors", 0))
            v3.metric("Alertes à vérifier", quality.get("validation_warnings", 0))
            if quality.get("validation_errors", 0):
                st.error("Des erreurs techniques ont été détectées. Vérifiez les lignes signalées avant toute analyse scientifique.")
            elif quality.get("validation_warnings", 0):
                st.warning("Certaines informations demandent une vérification ou un complément documentaire.")
            else:
                st.success("Aucune anomalie détectée par les contrôles actuellement activés.")

            st.caption(quality.get("interpretation", "Score documentaire uniquement."))
            st.info(quality.get("message", "Les champs non renseignés ne sont pas considérés comme des résultats négatifs."))

            # Product-specific analytical priorities (research guidance, not legal limits).
            profile_report = quality.get("product_profiles", {})
            st.subheader("🧩 Product-Specific Validation Profiles")
            st.caption(profile_report.get("message", "Les priorités dépendent de la catégorie du produit."))
            profile_rows = []
            for profile in profile_report.get("profiles", []):
                profile_rows.append({
                    "Catégorie": profile.get("category", "—"),
                    "Profil": profile.get("profile", "Profil général"),
                    "Observations": profile.get("observations", 0),
                    "Couverture des champs prioritaires (%)": profile.get("coverage_percent", "N/D"),
                    "Champs prioritaires présents": ", ".join(profile.get("measured_priority_fields", [])) or "Aucun résultat renseigné",
                    "Domaines prioritaires": ", ".join(profile.get("priority_domains", [])),
                })
            if profile_rows:
                st.dataframe(pd.DataFrame(profile_rows), width="stretch", hide_index=True)
                for profile in profile_report.get("profiles", []):
                    with st.expander(f"Détails — {profile.get('category', 'Catégorie')}"):
                        st.write(profile.get("note", "Profil indicatif."))
                        st.caption("Champs prioritaires identifiés : " + (", ".join(profile.get("priority_fields", [])) or "Aucun champ spécifique reconnu dans le CSV."))
            else:
                st.caption("Ajoutez une catégorie de produit pour activer les profils spécialisés.")

            components = quality.get("score_components", {})
            if components:
                st.markdown("**Composition du score**")
                component_df = pd.DataFrame([{"Dimension": k, "Couverture / cohérence (%)": v} for k, v in components.items()])
                st.dataframe(component_df, width="stretch", hide_index=True)

            with st.expander("Voir la couverture des analyses par domaine", expanded=True):
                group_rows = []
                for group_name, details in quality.get("coverage", {}).get("Analyses par domaine", {}).items():
                    group_rows.append({
                        "Domaine": group_name,
                        "Champs disponibles dans le fichier": len(details.get("fields", [])),
                        "Valeurs renseignées": details.get("available", 0),
                        "Valeurs possibles": details.get("possible", 0),
                        "Couverture (%)": details.get("percent", 0.0),
                    })
                if group_rows:
                    st.dataframe(pd.DataFrame(group_rows), width="stretch", hide_index=True)
                else:
                    st.caption("Aucun champ analytique reconnu dans les colonnes actuelles.")

            issues = quality.get("issues", [])
            st.markdown(f"**Alertes techniques à vérifier : {quality.get('issue_count', len(issues))}**")
            if issues:
                st.dataframe(pd.DataFrame(issues), width="stretch", hide_index=True)
            else:
                st.success("Aucune incohérence technique détectée dans les contrôles appliqués.")
            st.caption("Les analyses non réalisées restent non testées. Les seuils réglementaires ne sont pas appliqués automatiquement : ils dépendent du produit, de la méthode, de l'unité et de la réglementation de référence.")
        except Exception as error:
            show_error("Le contrôle qualité du dataset a rencontré une erreur.", error)
    else:
        st.info("Aucune observation locale pour le moment. Ajoutez un premier échantillon ci-dessus.")


# =====================================================
# RESEARCH ANALYTICS
# =====================================================

elif page == "📊 Research Analytics":
    st.title("📊 FOODNEXA Research Analytics V2")
    st.write("Statistiques descriptives multi-domaines, calculées uniquement sur les résultats réellement renseignés.")
    st.warning("Analyse exploratoire uniquement : elle ne constitue pas un modèle prédictif validé et ne remplace pas les analyses de laboratoire ni l'interprétation réglementaire.")
    data, data_source, source_error = load_research_analytics_data()
    if data_source == "Supabase":
        st.caption("Source des données : Supabase — base centrale des observations.")
    elif data_source.startswith("CSV local"):
        st.caption(f"Source des données : {data_source}.")
        if source_error is not None:
            st.warning("Supabase n'a pas pu être interrogé. Les statistiques affichées proviennent du fichier CSV local de secours.")
    if data.empty:
        if source_error is not None:
            show_error("Impossible de récupérer les données de recherche depuis Supabase et aucun CSV local exploitable n'est disponible.", source_error)
        elif data_source == "CSV local (Supabase vide)":
            st.info("Supabase ne contient pas encore d'observation. Les données locales sont affichées en attendant.")
        else:
            st.info("Aucune donnée disponible. Ajoutez des observations dans Research Data.")
    else:
        if "product_category" in data.columns:
            categories = ["Toutes les catégories"] + sorted(data["product_category"].dropna().astype(str).unique().tolist())
            selected_category = st.selectbox("Filtrer par catégorie", categories)
            if selected_category != "Toutes les catégories":
                data = data[data["product_category"].astype(str) == selected_category]
        if "product_name" in data.columns:
            products = ["Tous les produits"] + sorted(data["product_name"].dropna().astype(str).unique().tolist())
            selected_product = st.selectbox("Filtrer par produit", products)
            if selected_product != "Tous les produits":
                data = data[data["product_name"].astype(str) == selected_product]
        st.divider()
        total = len(data)
        label_series = data.get("expert_risk_label", pd.Series(index=data.index, dtype="object"))
        assigned = label_series.dropna().astype(str).str.strip()
        risk_count = int(assigned.isin(["Faible", "Modéré", "Élevé"]).sum())
        salm = data.get("salmonella_detected", pd.Series(index=data.index, dtype="object")).astype(str).str.strip().str.casefold()
        salm_valid = ~salm.isin(["", "nan", "none", "non analysée", "non analysé", "non renseigné"])
        nonconf = data.get("nonconformity_detected", pd.Series(index=data.index, dtype="object")).astype(str).str.strip().str.casefold()
        nonconf_valid = ~nonconf.isin(["", "nan", "none", "non évaluée", "non évalué", "non renseigné"])
        srate = (salm[salm_valid].isin(["détectée", "detectee", "oui", "true", "positive"]).mean() * 100) if salm_valid.any() else None
        nrate = (nonconf[nonconf_valid].isin(["oui", "true", "non conforme", "non-conforme"]).mean() * 100) if nonconf_valid.any() else None
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Observations", total)
        k2.metric("Labels experts renseignés", f"{risk_count}/{total}")
        k3.metric("Salmonella détectée", "N/D" if srate is None else f"{srate:.1f}%")
        k4.metric("Non-conformités", "N/D" if nrate is None else f"{nrate:.1f}%")
        if risk_count:
            st.subheader("Distribution des labels experts")
            dist = assigned[assigned.isin(["Faible", "Modéré", "Élevé"])].value_counts().reindex(["Faible", "Modéré", "Élevé"], fill_value=0)
            st.bar_chart(dist)
        st.subheader("Statistiques descriptives des paramètres numériques")
        excluded = {"id"}
        numeric_data = data.drop(columns=[c for c in excluded if c in data.columns]).apply(pd.to_numeric, errors="coerce")
        numeric_cols = [c for c in numeric_data.columns if numeric_data[c].notna().any()]
        if numeric_cols:
            stats = numeric_data[numeric_cols].describe().T[["count", "mean", "50%", "min", "max"]].rename(columns={"50%": "median"}).round(3)
            st.dataframe(stats, use_container_width=True)
        else:
            st.info("Aucune mesure numérique disponible pour les filtres sélectionnés.")
        st.subheader("Complétude des données")
        missing_rows = []
        for col in data.columns:
            available_count = int(data[col].notna().sum())
            missing_rows.append({"Variable": col, "Renseignées": available_count, "Manquantes": total - available_count, "Complétude (%)": round(available_count / total * 100, 1) if total else 0})
        missing_df = pd.DataFrame(missing_rows).sort_values("Complétude (%)")
        st.dataframe(missing_df, use_container_width=True, hide_index=True)
        st.info("Un taux de complétude élevé ne prouve ni la conformité ni l'innocuité alimentaire. Les mesures doivent être interprétées avec leurs unités, méthodes, matrices et limites applicables.")


# =====================================================
# HISTORY
# =====================================================

elif page == "📁 Historique":
    st.title("📁 Historique FOODNEXA")
    if history.empty:
        st.info("Aucune analyse enregistrée.")
    else:
        st.write(f"Nombre total d'analyses : **{len(history)}**")
        st.dataframe(history, width="stretch", hide_index=True)
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
        if st.button("Tester la connexion Supabase", key="test_supabase_connection"):
            try:
                from foodnexa_supabase import test_supabase_connection
                test_result = test_supabase_connection()
                st.success("Connexion Supabase établie. La table lots est accessible.")
                st.caption(f"Lignes retournées : {test_result['rows_returned']}")
            except Exception as error:
                show_error("Le test de connexion Supabase a échoué.", error)
    st.info("""
    FOODNEXA est actuellement un prototype expérimental basé sur des règles explicables.
    L'objectif est de construire progressivement une base de données structurée pour étudier
    des approches statistiques et de Machine Learning.
    """)
    st.subheader("🔬 Architecture actuelle")
    architecture = pd.DataFrame({
        "Module": [
            "Data Input", "Risk Engine", "Explainability", "Risk Classification",
            "Recommendations", "Research Dataset", "Data Quality Engine",
            "Research Analytics", "Feature Engineering", "Machine Learning", "Validation",
        ],
        "État": [
            "Disponible", "Disponible", "Disponible", "Disponible", "Disponible",
            "Disponible", "Disponible", "Disponible", "À développer", "À développer", "À développer",
        ],
    })
    st.dataframe(architecture, width="stretch", hide_index=True)
    st.subheader("🎯 Objectif scientifique")
    st.write("""
    Construire un dataset de lots alimentaires contenant des variables de procédé, de stockage,
    de qualité et, lorsque disponibles, des résultats microbiologiques et des observations d'experts.
    """)
    st.subheader("🧠 Pipeline prévu")
    pipeline = pd.DataFrame({
        "Étape": [
            "Collecte des données", "Data Quality", "Nettoyage", "Research Analytics",
            "Feature Engineering", "Séparation Train/Test", "Entraînement ML",
            "Validation", "Évaluation", "Risk Prediction",
        ],
        "Statut": [
            "En cours", "Disponible", "À développer", "Disponible", "À développer",
            "À développer", "À développer", "À développer", "À développer", "À développer",
        ],
    })
    st.dataframe(pipeline, width="stretch", hide_index=True)
    st.warning("Les résultats actuels sont expérimentaux. Ils ne remplacent pas les analyses de laboratoire ni les exigences réglementaires.")


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
