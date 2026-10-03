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
# CUSTOM STYLE
# =====================================================

st.markdown(
    """
    <style>

    /* ==============================
       GENERAL
    ============================== */

    .main {
        background-color: #ffffff;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }


    /* ==============================
       HEADER
    ============================== */

    .foodnexa-header {
        text-align: center;
        padding: 10px 0 0 0;
    }

    .foodnexa-tagline {
        text-align: center;
        color: #238B57;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: 1px;
        margin-top: 8px;
        margin-bottom: 20px;
    }

    .foodnexa-divider {
        height: 4px;
        width: 100%;
        background: linear-gradient(
            90deg,
            #0B2A4A,
            #00A6C7,
            #238B57
        );
        border-radius: 10px;
        margin-bottom: 30px;
    }


    /* ==============================
       SECTION TITLES
    ============================== */

    .section-title {
        color: #0B2A4A;
        font-size: 25px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 15px;
    }


    /* ==============================
       INFORMATION BOX
    ============================== */

    .info-box {
        background: linear-gradient(
            135deg,
            #F3F9FC,
            #F5FBF6
        );

        border-left: 5px solid #00A6C7;

        padding: 18px 22px;

        border-radius: 10px;

        margin-bottom: 25px;

        font-size: 15px;

        line-height: 1.6;
    }


    /* ==============================
       ANALYSIS CARD
    ============================== */

    .analysis-card {
        background-color: #F8FAFC;

        border: 1px solid #E2E8F0;

        border-radius: 14px;

        padding: 20px;

        margin-bottom: 20px;
    }


    /* ==============================
       FOOTER
    ============================== */

    .footer {
        text-align: center;

        color: #777777;

        font-size: 13px;

        padding-top: 15px;

        padding-bottom: 10px;

        line-height: 1.6;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# FOODNEXA HEADER
# =====================================================

st.markdown(
    '<div class="foodnexa-header">',
    unsafe_allow_html=True
)


# -----------------------------------------------------
# LOGO
# -----------------------------------------------------

if os.path.exists(LOGO_FILE):

    st.image(
        LOGO_FILE,
        width=700
    )

else:

    st.markdown(
        """
        <h1 style="
            text-align:center;
            color:#0B2A4A;
            font-size:48px;
            margin-bottom:5px;
        ">
            🛡️ FOODNEXA
        </h1>
        """,
        unsafe_allow_html=True
    )


# -----------------------------------------------------
# TAGLINE
# -----------------------------------------------------

st.markdown(
    """
    <div class="foodnexa-tagline">
        INTELLIGENT FOOD SAFETY RISK ASSESSMENT
    </div>
    """,
    unsafe_allow_html=True
)


# -----------------------------------------------------
# DIVIDER
# -----------------------------------------------------

st.markdown(
    '<div class="foodnexa-divider"></div>',
    unsafe_allow_html=True
)


# =====================================================
# INTRODUCTION
# =====================================================

st.markdown(
    """
    <div class="info-box">

        <b style="font-size:18px;">FOODNEXA</b>
        is an experimental intelligent decision-support
        prototype designed for food safety risk assessment.

        <br><br>

        <b>Current research case:</b>
        Pasteurized milk

        <br>

        <b>Objective:</b>
        Early identification of potential food safety risk
        factors using structured input data and an
        explainable rule-based assessment engine.

    </div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# NEW ANALYSIS
# =====================================================

st.markdown(
    '<div class="section-title">🔬 Nouvelle analyse</div>',
    unsafe_allow_html=True
)


st.markdown(
    """
    <div class="analysis-card">
    """,
    unsafe_allow_html=True
)


# =====================================================
# INPUT COLUMNS
# =====================================================

col1, col2 = st.columns(2)


# =====================================================
# LEFT COLUMN
# =====================================================

with col1:

    batch_id = st.text_input(
        "Numéro de lot",
        placeholder="Exemple : LOT-006"
    )

    product_name = st.text_input(
        "Nom du produit",
        value="Lait pasteurisé"
    )

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

    ph = st.number_input(
        "Valeur pH",
        min_value=0.0,
        max_value=14.0,
        value=6.6,
        step=0.1
    )

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


st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# =====================================================
# ANALYSIS BUTTON
# =====================================================

st.divider()


start_analysis = st.button(
    "🚀 Lancer l'analyse FOODNEXA",
    use_container_width=True
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
            "Veuillez saisir un numéro de lot."
        )

        st.stop()


    if not product_name.strip():

        st.warning(
            "Veuillez saisir le nom du produit."
        )

        st.stop()


    # -------------------------------------------------
    # RUN ENGINE
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
            "Une erreur est survenue pendant l'analyse."
        )

        st.code(
            str(error)
        )

        st.stop()


    # -------------------------------------------------
    # SUCCESS
    # -------------------------------------------------

    st.success(
        "Analyse FOODNEXA terminée avec succès."
    )


    # =================================================
    # RESULT
    # =================================================

    st.markdown(
        '<div class="section-title">📊 Résultat de l’analyse</div>',
        unsafe_allow_html=True
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

    st.subheader(
        "🔎 Facteurs analysés"
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

    st.subheader(
        "⚠️ Facteurs de risque détectés"
    )


    if report["reasons"]:

        for reason in report["reasons"]:

            st.write(
                "•",
                reason
            )

    else:

        st.write(
            "Aucun facteur de risque détecté "
            "selon les règles actuelles du prototype."
        )


    # =================================================
    # RECOMMENDATIONS
    # =================================================

    st.subheader(
        "💡 Recommandations FOODNEXA"
    )


    for recommendation in report["recommendations"]:

        st.write(
            "•",
            recommendation
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
            else
            "Aucun facteur de risque détecté",

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
            f"Analyse du lot {batch_id} "
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
    '<div class="section-title">📁 Historique des analyses</div>',
    unsafe_allow_html=True
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
                "Aucune analyse enregistrée "
                "pour le moment."
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
        "Aucune analyse enregistrée "
        "pour le moment."
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()


st.markdown(
    """
    <div class="footer">

        <b>FOODNEXA</b>
        — Food Safety / Risk Intelligence

        <br><br>

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
