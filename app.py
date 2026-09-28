import streamlit as st
import pandas as pd
import os

from foodguard_engine import assess_dairy_food_safety_risk


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AgroNexus FoodGuard",
    page_icon="🛡️",
    layout="wide"
)


# =========================================================
# STYLE
# =========================================================

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
        color: #666;
        margin-bottom: 25px;
    }

    .risk-high {
        padding: 20px;
        border-radius: 12px;
        background-color: #ffe5e5;
        border: 2px solid #d9534f;
        color: #8a1f1f;
        font-size: 26px;
        font-weight: 700;
        text-align: center;
    }

    .risk-medium {
        padding: 20px;
        border-radius: 12px;
        background-color: #fff3cd;
        border: 2px solid #f0ad4e;
        color: #856404;
        font-size: 26px;
        font-weight: 700;
        text-align: center;
    }

    .risk-low {
        padding: 20px;
        border-radius: 12px;
        background-color: #e5f6e9;
        border: 2px solid #5cb85c;
        color: #286b2f;
        font-size: 26px;
        font-weight: 700;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🛡️ AgroNexus FoodGuard</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Prototype intelligent d’évaluation des risques liés à la sécurité alimentaire'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "Produit pilote : Lait pasteurisé | "
    "Système expérimental d'aide à la décision."
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Paramètres du lot")

batch_id = st.sidebar.text_input(
    "Numéro de lot",
    value="LOT-004"
)

product_name = st.sidebar.text_input(
    "Produit",
    value="Lait pasteurisé"
)

temperature = st.sidebar.number_input(
    "Température de stockage (°C)",
    min_value=-20.0,
    max_value=50.0,
    value=4.0,
    step=0.1
)

storage_days = st.sidebar.number_input(
    "Durée de stockage (jours)",
    min_value=0,
    max_value=365,
    value=2,
    step=1
)

ph = st.sidebar.number_input(
    "pH",
    min_value=0.0,
    max_value=14.0,
    value=6.6,
    step=0.1
)

cold_chain_broken = st.sidebar.selectbox(
    "Interruption de la chaîne du froid ?",
    ["Non", "Oui"]
)

hygiene_controlled = st.sidebar.selectbox(
    "Conditions d'hygiène maîtrisées ?",
    ["Oui", "Non"]
)

pasteurized = st.sidebar.selectbox(
    "Produit pasteurisé ?",
    ["Oui", "Non"]
)


# =========================================================
# CONVERSION
# =========================================================

cold_chain_value = cold_chain_broken == "Oui"
hygiene_value = hygiene_controlled == "Oui"
pasteurized_value = pasteurized == "Oui"


# =========================================================
# ANALYSE
# =========================================================

st.subheader("Analyse du lot")

if st.button("🔍 Lancer l'analyse", use_container_width=True):

    try:

        report = assess_dairy_food_safety_risk(
            temperature=temperature,
            storage_days=storage_days,
            ph=ph,
            cold_chain_broken=cold_chain_value,
            hygiene_controlled=hygiene_value,
            pasteurized=pasteurized_value,
            batch_id=batch_id,
            product_name=product_name
        )

        if report.get("status") != "SUCCESS":

            st.error("L'analyse n'a pas pu être effectuée.")

        else:

            risk_score = report.get("risk_score", 0)
            risk_level = report.get("risk_level", "Inconnu")
            confidence = report.get("confidence", 0)

            # -------------------------------------------------
            # SCORE
            # -------------------------------------------------

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Risk Score",
                    f"{risk_score}/100"
                )

            with col2:
                st.metric(
                    "Niveau de risque",
                    risk_level
                )

            with col3:
                st.metric(
                    "Confiance du prototype",
                    f"{confidence:.1f}%"
                )

            # -------------------------------------------------
            # RISK DISPLAY
            # -------------------------------------------------

            if risk_level == "Élevé":

                st.markdown(
                    '<div class="risk-high">'
                    '⚠️ RISQUE ÉLEVÉ'
                    '</div>',
                    unsafe_allow_html=True
                )

            elif risk_level in ["Moyen", "Modéré"]:

                st.markdown(
                    '<div class="risk-medium">'
                    '⚠️ RISQUE MOYEN'
                    '</div>',
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    '<div class="risk-low">'
                    '✓ RISQUE FAIBLE'
                    '</div>',
                    unsafe_allow_html=True
                )


            # -------------------------------------------------
            # FACTEURS
            # -------------------------------------------------

            st.subheader("Facteurs analysés")

            factors = report.get("factors", {})

            factor_rows = []

            factor_names = {
                "temperature": "Température",
                "storage_duration": "Durée de stockage",
                "ph": "pH",
                "cold_chain": "Chaîne du froid",
                "hygiene": "Hygiène",
                "pasteurization": "Pasteurisation"
            }

            for key, label in factor_names.items():

                factor = factors.get(key, {})

                factor_rows.append({
                    "Facteur": label,
                    "Score": factor.get("score", 0),
                    "Niveau": factor.get("level", ""),
                    "Évaluation": factor.get("reason", "")
                })

            factor_df = pd.DataFrame(factor_rows)

            st.dataframe(
                factor_df,
                use_container_width=True,
                hide_index=True
            )


            # -------------------------------------------------
            # RAISONS
            # -------------------------------------------------

            st.subheader("Raisons identifiées")

            reasons = report.get("reasons", [])

            if reasons:

                for reason in reasons:
                    st.warning(reason)

            else:

                st.success(
                    "Aucun facteur de risque détecté par les règles "
                    "actuelles du prototype."
                )


            # -------------------------------------------------
            # RECOMMANDATIONS
            # -------------------------------------------------

            st.subheader("Recommandations")

            recommendations = report.get(
                "recommendations",
                []
            )

            for recommendation in recommendations:
                st.write("• " + recommendation)


            # -------------------------------------------------
            # INFORMATIONS DU LOT
            # -------------------------------------------------

            st.subheader("Informations du lot")

            lot_data = pd.DataFrame([{
                "Lot": batch_id,
                "Produit": product_name,
                "Température °C": temperature,
                "Stockage jours": storage_days,
                "pH": ph,
                "Chaîne du froid interrompue": cold_chain_value,
                "Hygiène maîtrisée": hygiene_value,
                "Pasteurisé": pasteurized_value
            }])

            st.dataframe(
                lot_data,
                use_container_width=True,
                hide_index=True
            )


            # -------------------------------------------------
            # DISCLAIMER
            # -------------------------------------------------

            st.warning(
                report.get(
                    "disclaimer",
                    "Résultat expérimental d'aide à la décision."
                )
            )


# =========================================================
# HISTORIQUE
# =========================================================

st.divider()

st.subheader("Historique des analyses")

csv_file = "agronexus_assessments.csv"

if os.path.exists(csv_file):

    try:

        history = pd.read_csv(
            csv_file,
            sep=None,
            engine="python"
        )

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:

        st.error(
            f"Impossible de lire l'historique : {e}"
        )

else:

    st.info(
        "Aucun historique disponible pour le moment."
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AgroNexus FoodGuard — Prototype de recherche en sécurité alimentaire. "
    "Les résultats ne remplacent pas les analyses de laboratoire ni "
    "la décision du responsable qualité."
)
