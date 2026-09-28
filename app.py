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

CSV_FILE = "agronexus_assessments.csv"


# =========================================================
# STYLE
# =========================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 18px;
        color: #666;
        margin-bottom: 30px;
    }

    .risk-box {
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin: 15px 0;
        border: 1px solid #ddd;
    }

    .small-note {
        color: #666;
        font-size: 14px;
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
    'Prototype intelligent d’évaluation des risques de sécurité des aliments'
    '</div>',
    unsafe_allow_html=True
)

st.info(
    "Prototype expérimental d’aide à la décision pour l’évaluation "
    "préliminaire des risques dans les produits laitiers."
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🛡️ FoodGuard")

st.sidebar.markdown(
    """
    **Produit analysé :**

    🥛 Lait pasteurisé

    **Fonction :**

    Évaluation préliminaire du niveau de risque.
    """
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "AgroNexus FoodGuard — Prototype de recherche"
)


# =========================================================
# INPUT FORM
# =========================================================

st.header("🔬 Nouvelle analyse")

with st.form("risk_assessment_form"):

    col1, col2 = st.columns(2)

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

    with col2:

        ph = st.number_input(
            "Valeur pH",
            min_value=0.0,
            max_value=14.0,
            value=6.6,
            step=0.1
        )

        cold_chain_answer = st.selectbox(
            "Interruption de la chaîne du froid ?",
            ["Non", "Oui"]
        )

        hygiene_answer = st.selectbox(
            "Conditions d'hygiène maîtrisées ?",
            ["Oui", "Non"]
        )

        pasteurization_answer = st.selectbox(
            "Produit pasteurisé ?",
            ["Oui", "Non"]
        )

    submitted = st.form_submit_button(
        "🚀 Lancer l'analyse",
        use_container_width=True
    )


# =========================================================
# ANALYSIS
# =========================================================

if submitted:

    if not batch_id.strip():

        st.error(
            "Veuillez saisir un numéro de lot."
        )

    else:

        cold_chain_broken = (
            cold_chain_answer == "Oui"
        )

        hygiene_controlled = (
            hygiene_answer == "Oui"
        )

        pasteurized = (
            pasteurization_answer == "Oui"
        )

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

            st.session_state["last_report"] = report

            st.session_state["last_inputs"] = {

                "temperature": temperature,

                "storage_days": storage_days,

                "ph": ph,

                "cold_chain_broken": cold_chain_broken,

                "hygiene_controlled": hygiene_controlled,

                "pasteurized": pasteurized
            }

        except Exception as e:

            st.error(
                f"Erreur pendant l'analyse : {e}"
            )


# =========================================================
# DISPLAY RESULT
# =========================================================

if "last_report" in st.session_state:

    report = st.session_state["last_report"]

    inputs = st.session_state["last_inputs"]

    st.markdown("---")

    st.header("📊 Résultat de l'analyse")

    risk_score = report.get(
        "risk_score",
        0
    )

    risk_level = report.get(
        "risk_level",
        "Inconnu"
    )

    confidence = report.get(
        "confidence",
        0
    )

    # -----------------------------------------------------
    # KPI
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # RISK DISPLAY
    # -----------------------------------------------------

    if risk_level == "Élevé":

        st.error(
            f"🔴 RISQUE ÉLEVÉ — Score : {risk_score}/100"
        )

    elif risk_level == "Modéré":

        st.warning(
            f"🟠 RISQUE MODÉRÉ — Score : {risk_score}/100"
        )

    else:

        st.success(
            f"🟢 RISQUE FAIBLE — Score : {risk_score}/100"
        )

    # -----------------------------------------------------
    # LOT INFORMATION
    # -----------------------------------------------------

    st.subheader("📦 Informations du lot")

    info_col1, info_col2, info_col3 = st.columns(3)

    with info_col1:

        st.write(
            f"**Lot :** {report.get('batch_id', '')}"
        )

        st.write(
            f"**Produit :** {report.get('product_name', '')}"
        )

    with info_col2:

        st.write(
            f"**Température :** "
            f"{inputs['temperature']} °C"
        )

        st.write(
            f"**Durée :** "
            f"{inputs['storage_days']} jours"
        )

    with info_col3:

        st.write(
            f"**pH :** {inputs['ph']}"
        )

        st.write(
            f"**Pasteurisé :** "
            f"{'Oui' if inputs['pasteurized'] else 'Non'}"
        )

    # -----------------------------------------------------
    # FACTORS
    # -----------------------------------------------------

    st.subheader("🔎 Facteurs analysés")

    factors = report.get(
        "factors",
        {}
    )

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

        factor = factors.get(
            key,
            {}
        )

        factor_rows.append({

            "Facteur": label,

            "Score": factor.get(
                "score",
                0
            ),

            "Niveau": factor.get(
                "level",
                ""
            ),

            "Observation": factor.get(
                "reason",
                ""
            )
        })

    factor_df = pd.DataFrame(
        factor_rows
    )

    st.dataframe(
        factor_df,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------------------
    # REASONS
    # -----------------------------------------------------

    st.subheader("⚠️ Facteurs de risque détectés")

    reasons = report.get(
        "reasons",
        []
    )

    if reasons:

        for reason in reasons:

            st.warning(
                f"• {reason}"
            )

    else:

        st.success(
            "Aucun facteur de risque détecté "
            "par les règles actuelles du prototype."
        )

    # -----------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------

    st.subheader("💡 Recommandations")

    recommendations = report.get(
        "recommendations",
        []
    )

    for recommendation in recommendations:

        st.info(
            f"• {recommendation}"
        )

    # -----------------------------------------------------
    # DISCLAIMER
    # -----------------------------------------------------

    st.markdown("---")

    st.warning(
        report.get(
            "disclaimer",
            "Résultat expérimental d'aide à la décision. "
            "Ne remplace pas les analyses de laboratoire "
            "ni la décision du responsable qualité."
        )
    )


# =========================================================
# HISTORICAL DATA
# =========================================================

st.markdown("---")

st.header("📚 Historique des analyses")

if os.path.exists(CSV_FILE):

    try:

        history_df = pd.read_csv(
            CSV_FILE,
            sep=None,
            engine="python"
        )

        if not history_df.empty:

            st.dataframe(
                history_df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                label="⬇️ Télécharger l'historique CSV",
                data=history_df.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="agronexus_assessments.csv",
                mime="text/csv"
            )

        else:

            st.info(
                "Aucune analyse enregistrée."
            )

    except Exception as e:

        st.error(
            f"Impossible de lire l'historique : {e}"
        )

else:

    st.info(
        "Le fichier historique n'est pas encore disponible."
    )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.markdown(
    """
    <div class="small-note">
    AgroNexus FoodGuard — Prototype de recherche en sécurité alimentaire.<br>
    Version expérimentale — Ne remplace pas les analyses de laboratoire.
    </div>
    """,
    unsafe_allow_html=True
)
