import streamlit as st
import pandas as pd
import os

from foodguard_engine import assess_dairy_food_safety_risk


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="AgroNexus FoodGuard",
    page_icon="🛡️",
    layout="wide"
)


# =====================================================
# CONFIGURATION
# =====================================================

CSV_FILE = "agronexus_assessments.csv"


# =====================================================
# CUSTOM STYLE
# =====================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 18px;
        color: #666666;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 25px;
        font-weight: 650;
        margin-top: 20px;
        margin-bottom: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# HEADER
# =====================================================

st.markdown(
    '<div class="main-title">🛡️ AgroNexus FoodGuard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Prototype intelligent d’évaluation des risques en sécurité alimentaire'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "Produit actuellement étudié : Lait pasteurisé | "
    "Outil expérimental d’aide à la décision."
)


# =====================================================
# NEW ANALYSIS
# =====================================================

st.header("🔬 Nouvelle analyse")

col1, col2 = st.columns(2)


# =====================================================
# LEFT COLUMN
# =====================================================

with col1:

    batch_id = st.text_input(
        "Numéro de lot",
        placeholder="Exemple : LOT-004"
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
        "Conditions d’hygiène maîtrisées",
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
    "🚀 Lancer l'analyse",
    use_container_width=True
)


if start_analysis:

    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    if not batch_id.strip():

        st.warning(
            "Veuillez saisir un numéro de lot."
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

        st.code(str(error))

        st.stop()


    # -------------------------------------------------
    # SUCCESS
    # -------------------------------------------------

    st.success(
        "Analyse terminée avec succès."
    )


    # =================================================
    # RESULT
    # =================================================

    st.header("📊 Résultat de l'analyse")


    result_col1, result_col2, result_col3 = st.columns(3)


    with result_col1:

        st.metric(
            "Risk Score",
            f"{report['risk_score']}/100"
        )


    with result_col2:

        st.metric(
            "Niveau de risque",
            report["risk_level"]
        )


    with result_col3:

        st.metric(
            "Confidence",
            f"{report['confidence']:.1f}%"
        )


    # -------------------------------------------------
    # RISK STATUS
    # -------------------------------------------------

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

    st.subheader("🔎 Facteurs analysés")


    factor_names = {

        "temperature": "Température",

        "storage_duration": "Durée de stockage",

        "ph": "pH",

        "cold_chain": "Chaîne du froid",

        "hygiene": "Hygiène",

        "pasteurization": "Pasteurisation"

    }


    factor_data = []


    for factor_name, factor in report["factors"].items():

        factor_data.append(
            {
                "Facteur": factor_names.get(
                    factor_name,
                    factor_name
                ),

                "Score": factor["score"],

                "Niveau": factor["level"],

                "Explication": factor["reason"]
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
        "💡 Recommandations"
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
            " | ".join(report["reasons"])
            if report["reasons"]
            else "Aucun facteur de risque détecté",

        "recommendations":
            " | ".join(report["recommendations"])

    }


    new_row = pd.DataFrame(
        [row]
    )


    # -------------------------------------------------
    # UPDATE CSV
    # -------------------------------------------------

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
            "enregistrée avec succès."
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

st.header(
    "📁 Historique des analyses"
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

st.caption(
    "AgroNexus FoodGuard est un prototype expérimental "
    "d'aide à la décision. Il ne remplace pas les analyses "
    "de laboratoire, les exigences réglementaires ni la "
    "décision du responsable qualité."
)
