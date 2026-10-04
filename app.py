import streamlit as st
import pandas as pd
import os

from foodguard_engine import assess_dairy_food_safety_risk


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="FOODNEXA",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =====================================================
# CONFIGURATION
# =====================================================

CSV_FILE = "agronexus_assessments.csv"
LOGO_FILE = "foodnexa_logo.png"


# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1400px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .foodnexa-tagline {
        text-align: center;
        color: #20A36A;
        font-size: 17px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-top: 8px;
        margin-bottom: 20px;
    }

    .foodnexa-line {
        height: 4px;
        width: 100%;
        background: linear-gradient(
            90deg,
            #0B2A4A,
            #00A6C7,
            #20A36A
        );
        border-radius: 10px;
        margin-bottom: 28px;
    }

    .section-title {
        color: #0B2A4A;
        font-size: 25px;
        font-weight: 700;
        margin-top: 18px;
        margin-bottom: 15px;
    }

    .small-label {
        color: #64748B;
        font-size: 14px;
    }

    .footer-text {
        text-align: center;
        color: #64748B;
        font-size: 13px;
        line-height: 1.7;
        padding: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.markdown("## 🛡️ FOODNEXA")

    st.markdown(
        "**Food Safety / Risk Intelligence**"
    )

    st.divider()

    st.markdown("### 🔬 Research Prototype")

    st.write(
        "Current research case:"
    )

    st.info(
        "🥛 Lait pasteurisé"
    )

    st.markdown("### 📌 Fonction")

    st.write(
        "Évaluation expérimentale des facteurs "
        "pouvant contribuer au risque en sécurité "
        "alimentaire."
    )

    st.divider()

    st.caption(
        "FOODNEXA v1.0 — Experimental Prototype"
    )


# =====================================================
# HEADER
# =====================================================

if os.path.exists(LOGO_FILE):

    st.image(
        LOGO_FILE,
        width=700
    )

else:

    st.markdown(
        "# 🛡️ FOODNEXA"
    )


st.markdown(
    """
    <div class="foodnexa-tagline">
        INTELLIGENT FOOD SAFETY RISK ASSESSMENT
    </div>
    """,
    unsafe_allow_html=True
)


st.markdown(
    '<div class="foodnexa-line"></div>',
    unsafe_allow_html=True
)


# =====================================================
# INTRODUCTION
# =====================================================

st.markdown(
    "### 🛡️ À propos de FOODNEXA"
)

st.info(
    """
    **FOODNEXA** est un prototype expérimental
    d'aide intelligente à la décision en sécurité alimentaire.

    **Cas de recherche actuel :** Lait pasteurisé.

    **Objectif :** identifier rapidement des facteurs
    pouvant contribuer au risque à partir de données
    structurées et fournir une analyse explicable.
    """
)


# =====================================================
# NEW ANALYSIS
# =====================================================

st.markdown(
    "### 🔬 Nouvelle analyse"
)


col1, col2 = st.columns(2)


# =====================================================
# LEFT COLUMN
# =====================================================

with col1:

    st.markdown("#### 📦 Identification")

    batch_id = st.text_input(
        "Numéro de lot",
        placeholder="Exemple : LOT-006"
    )

    product_name = st.text_input(
        "Nom du produit",
        value="Lait pasteurisé"
    )

    st.markdown("#### 🌡️ Conditions de stockage")

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


# =====================================================
# RIGHT COLUMN
# =====================================================

with col2:

    st.markdown("#### 🧪 Paramètres qualité")

    ph = st.number_input(
        "Valeur pH",
        min_value=0.0,
        max_value=14.0,
        value=6.6,
        step=0.1
    )

    st.markdown("#### 🧼 Contrôles")

    cold_chain_broken = st.checkbox(
        "Interruption de la chaîne du froid"
    )

    hygiene_controlled = st.checkbox(
        "Conditions d'hygiène maîtrisées",
        value=True
    )

    pasteurized = st.checkbox(
        "Produit pasteurisé",
        value=True
    )


# =====================================================
# ANALYSIS BUTTON
# =====================================================

st.divider()


start_analysis = st.button(
    "🚀 LANCER L'ANALYSE FOODNEXA",
    use_container_width=True,
    type="primary"
)


# =====================================================
# RUN ANALYSIS
# =====================================================

if start_analysis:

    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    if not batch_id.strip():

        st.warning(
            "⚠️ Veuillez saisir un numéro de lot."
        )

        st.stop()


    if not product_name.strip():

        st.warning(
            "⚠️ Veuillez saisir le nom du produit."
        )

        st.stop()


    # -------------------------------------------------
    # ENGINE
    # -------------------------------------------------

    try:

        report = assess_dairy_food_safety_risk(

            temperature=temperature,

            storage_days=storage_days,

            ph=ph,

            cold_chain_broken=cold_chain_broken,

            hygiene_controlled=hygiene_controlled,

            pasteurized=pasteurized,

            batch_id=batch_id,

            product_name=product_name

        )

    except Exception as error:

        st.error(
            "❌ Une erreur est survenue pendant l'analyse."
        )

        st.code(
            str(error)
        )

        st.stop()


    # =================================================
    # SUCCESS
    # =================================================

    st.success(
        "✅ Analyse FOODNEXA terminée avec succès."
    )


    # =================================================
    # RESULTS
    # =================================================

    st.markdown(
        "### 📊 Résultat de l'analyse"
    )


    result_col1, result_col2, result_col3 = st.columns(3)


    with result_col1:

        st.metric(
            "RISK SCORE",
            f"{report['risk_score']}/100"
        )


    with result_col2:

        st.metric(
            "NIVEAU DE RISQUE",
            report["risk_level"]
        )


    with result_col3:

        st.metric(
            "CONFIDENCE",
            f"{report['confidence']:.1f}%"
        )


    # =================================================
    # RISK STATUS
    # =================================================

    if report["risk_level"] == "Élevé":

        st.error(
            "🔴 RISQUE ÉLEVÉ"
        )

    elif report["risk_level"] == "Modéré":

        st.warning(
            "🟠 RISQUE MODÉRÉ"
        )

    else:

        st.success(
            "🟢 RISQUE FAIBLE"
        )


    # =================================================
    # FACTORS
    # =================================================

    st.markdown(
        "### 🔎 Facteurs analysés"
    )


    factor_names = {

        "temperature":
            "Température",

        "storage_duration":
            "Durée de stockage",

        "ph":
            "pH",

        "cold_chain":
            "Chaîne du froid",

        "hygiene":
            "Hygiène",

        "pasteurization":
            "Pasteurisation"

    }


    factor_data = []


    for factor_name, factor in report["factors"].items():

        factor_data.append(
            {
                "Facteur":
                    factor_names.get(
                        factor_name,
                        factor_name
                    ),

                "Score":
                    factor["score"],

                "Niveau":
                    factor["level"],

                "Explication":
                    factor["reason"]
            }
        )


    factors_df = pd.DataFrame(
        factor_data
    )


    st.dataframe(
        factors_df,
        use_container_width=True,
        hide_index=True
    )


    # =================================================
    # RISK FACTORS
    # =================================================

    st.markdown(
        "### ⚠️ Facteurs de risque détectés"
    )


    if report["reasons"]:

        for reason in report["reasons"]:

            st.warning(
                reason
            )

    else:

        st.success(
            "Aucun facteur de risque détecté "
            "selon les règles actuelles du prototype."
        )


    # =================================================
    # RECOMMENDATIONS
    # =================================================

    st.markdown(
        "### 💡 Recommandations FOODNEXA"
    )


    for recommendation in report["recommendations"]:

        st.info(
            recommendation
        )


    # =================================================
    # ANALYSIS SUMMARY
    # =================================================

    st.markdown(
        "### 📋 Résumé de l'analyse"
    )


    summary_col1, summary_col2 = st.columns(2)


    with summary_col1:

        st.write(
            "**Lot :**",
            report["batch_id"]
        )

        st.write(
            "**Produit :**",
            report["product_name"]
        )

        st.write(
            "**Température :**",
            f"{temperature} °C"
        )

        st.write(
            "**Durée :**",
            f"{storage_days} jours"
        )


    with summary_col2:

        st.write(
            "**pH :**",
            ph
        )

        st.write(
            "**Chaîne du froid interrompue :**",
            "Oui" if cold_chain_broken else "Non"
        )

        st.write(
            "**Hygiène maîtrisée :**",
            "Oui" if hygiene_controlled else "Non"
        )

        st.write(
            "**Pasteurisé :**",
            "Oui" if pasteurized else "Non"
        )


    # =================================================
    # SAVE RESULT
    # =================================================

    row = {

        "analysis_date":
            report["analysis_date"],

        "batch_id":
            report["batch_id"],

        "product_name":
            report["product_name"],

        "temperature_celsius":
            temperature,

        "storage_days":
            storage_days,

        "ph":
            ph,

        "cold_chain_broken":
            cold_chain_broken,

        "hygiene_controlled":
            hygiene_controlled,

        "pasteurized":
            pasteurized,

        "temperature_score":
            report["factors"]["temperature"]["score"],

        "storage_score":
            report["factors"]["storage_duration"]["score"],

        "ph_score":
            report["factors"]["ph"]["score"],

        "cold_chain_score":
            report["factors"]["cold_chain"]["score"],

        "hygiene_score":
            report["factors"]["hygiene"]["score"],

        "pasteurization_score":
            report["factors"]["pasteurization"]["score"],

        "risk_score":
            report["risk_score"],

        "risk_level":
            report["risk_level"],

        "confidence":
            report["confidence"],

        "reasons":
            " | ".join(
                report["reasons"]
            )
            if report["reasons"]
            else "Aucun facteur de risque détecté",

        "recommendations":
            " | ".join(
                report["recommendations"]
            )
    }


    new_row = pd.DataFrame(
        [row]
    )


    # =================================================
    # UPDATE CSV
    # =================================================

    try:

        if os.path.exists(CSV_FILE):

            old_data = pd.read_csv(
                CSV_FILE
            )

            final_data = pd.concat(
                [
                    old_data,
                    new_row
                ],
                ignore_index=True
            )

        else:

            final_data = new_row


        final_data.to_csv(
            CSV_FILE,
            index=False,
            encoding="utf-8-sig"
        )


        st.success(
            f"💾 Analyse du lot {batch_id} "
            "enregistrée dans l'historique."
        )


    except Exception as error:

        st.warning(
            "L'analyse a été effectuée, "
            "mais l'enregistrement dans l'historique "
            "a rencontré un problème."
        )

        st.code(
            str(error)
        )


# =====================================================
# HISTORY
# =====================================================

st.divider()


st.markdown(
    "### 📁 Historique des analyses"
)


if os.path.exists(CSV_FILE):

    try:

        history = pd.read_csv(
            CSV_FILE
        )


        if not history.empty:

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Aucune analyse enregistrée pour le moment."
            )


    except Exception as error:

        st.warning(
            "Impossible de lire l'historique."
        )

        st.code(
            str(error)
        )

else:

    st.info(
        "Aucune analyse enregistrée pour le moment."
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()


st.markdown(
    """
    <div class="footer-text">

    <b>FOODNEXA</b> — FOOD SAFETY / RISK INTELLIGENCE

    <br>

    Intelligent Food Safety Risk Assessment

    <br><br>

    Prototype expérimental d’aide à la décision.
    Il ne remplace pas les analyses de laboratoire,
    les exigences réglementaires ni la décision
    du responsable qualité.

    </div>
    """,
    unsafe_allow_html=True
)
