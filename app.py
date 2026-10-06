import streamlit as st
import pandas as pd
import os

from foodguard_engine import assess_dairy_food_safety_risk
from foodnexa_data_quality import generate_quality_report


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
# FILE CONFIGURATION
# =====================================================

CSV_FILE = "agronexus_assessments.csv"
RESEARCH_CSV_FILE = "foodnexa_research_dataset.csv"
LOGO_FILE = "foodnexa_logo.png"


# =====================================================
# RESEARCH DATASET COLUMNS
# =====================================================

RESEARCH_COLUMNS = [
    "batch_id",
    "product_name",
    "temperature_celsius",
    "storage_days",
    "ph",
    "cold_chain_broken",
    "hygiene_controlled",
    "pasteurized",
    "total_viable_count",
    "enterobacteriaceae_count",
    "coliform_count",
    "staphylococcus_aureus_count",
    "salmonella_detected",
    "sensory_status",
    "nonconformity_detected",
    "expert_risk_label"
]


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
        margin-bottom: 25px;
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
# LOAD MAIN HISTORY
# =====================================================

if os.path.exists(CSV_FILE):

    try:
        history = pd.read_csv(CSV_FILE)

    except Exception:
        history = pd.DataFrame()

else:
    history = pd.DataFrame()


# =====================================================
# LOAD RESEARCH DATASET
# =====================================================

if os.path.exists(RESEARCH_CSV_FILE):

    try:
        research_data = pd.read_csv(
            RESEARCH_CSV_FILE
        )

    except Exception:
        research_data = pd.DataFrame(
            columns=RESEARCH_COLUMNS
        )

else:

    research_data = pd.DataFrame(
        columns=RESEARCH_COLUMNS
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
# SIDEBAR
# =====================================================

with st.sidebar:

    st.markdown(
        "## 🛡️ FOODNEXA"
    )

    st.caption(
        "FOOD SAFETY / RISK INTELLIGENCE"
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🔬 Nouvelle analyse",
            "🧪 Research Data",
            "📁 Historique",
            "🧬 Research Prototype"
        ]
    )

    st.divider()

    st.info(
        "Current research case:\n\n"
        "🥛 Lait pasteurisé"
    )

    st.caption(
        "FOODNEXA v1.0"
    )


# =====================================================
# DASHBOARD
# =====================================================

if page == "📊 Dashboard":

    st.title(
        "📊 FOODNEXA Intelligence Dashboard"
    )

    st.write(
        "Vue synthétique des évaluations expérimentales "
        "de risque en sécurité alimentaire."
    )

    if history.empty:

        st.info(
            "Aucune analyse disponible. "
            "Lancez votre première analyse."
        )

    else:

        if "risk_score" in history.columns:

            history["risk_score"] = pd.to_numeric(
                history["risk_score"],
                errors="coerce"
            )

        if "confidence" in history.columns:

            history["confidence"] = pd.to_numeric(
                history["confidence"],
                errors="coerce"
            )

        total_analyses = len(history)

        high_risk = len(
            history[
                history["risk_level"] == "Élevé"
            ]
        )

        moderate_risk = len(
            history[
                history["risk_level"] == "Modéré"
            ]
        )

        low_risk = len(
            history[
                history["risk_level"] == "Faible"
            ]
        )

        average_score = history[
            "risk_score"
        ].mean()

        average_confidence = history[
            "confidence"
        ].mean()

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "📊 Analyses",
                total_analyses
            )

        with c2:
            st.metric(
                "🔴 Risque élevé",
                high_risk
            )

        with c3:
            st.metric(
                "🟠 Risque modéré",
                moderate_risk
            )

        with c4:
            st.metric(
                "🟢 Risque faible",
                low_risk
            )

        st.divider()

        c5, c6 = st.columns(2)

        with c5:
            st.metric(
                "📈 Risk Score moyen",
                f"{average_score:.1f}/100"
            )

        with c6:
            st.metric(
                "🎯 Confidence moyenne",
                f"{average_confidence:.1f}%"
            )

        st.divider()

        st.subheader(
            "📊 Distribution des niveaux de risque"
        )

        distribution = pd.DataFrame(
            {
                "Niveau": [
                    "Faible",
                    "Modéré",
                    "Élevé"
                ],
                "Nombre": [
                    low_risk,
                    moderate_risk,
                    high_risk
                ]
            }
        )

        st.bar_chart(
            distribution.set_index(
                "Niveau"
            )
        )

        if len(history) > 1:

            st.subheader(
                "📈 Évolution des Risk Scores"
            )

            score_history = history[
                ["batch_id", "risk_score"]
            ].dropna()

            if not score_history.empty:

                score_history = score_history.set_index(
                    "batch_id"
                )

                st.line_chart(
                    score_history
                )

        st.subheader(
            "🕒 Dernières analyses"
        )

        recent_columns = [
            "analysis_date",
            "batch_id",
            "product_name",
            "risk_score",
            "risk_level",
            "confidence"
        ]

        available_columns = [
            column
            for column in recent_columns
            if column in history.columns
        ]

        recent = history[
            available_columns
        ].tail(10).iloc[::-1]

        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True
        )


# =====================================================
# NEW ANALYSIS
# =====================================================

elif page == "🔬 Nouvelle analyse":

    st.title(
        "🔬 Nouvelle analyse FOODNEXA"
    )

    st.write(
        "Évaluation expérimentale du risque "
        "pour un lot de lait pasteurisé."
    )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "📦 Identification"
        )

        batch_id = st.text_input(
            "Numéro de lot",
            placeholder="Exemple : LOT-006"
        )

        product_name = st.text_input(
            "Nom du produit",
            value="Lait pasteurisé"
        )

        st.subheader(
            "🌡️ Conditions de stockage"
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

        st.subheader(
            "🧪 Paramètres qualité"
        )

        ph = st.number_input(
            "Valeur pH",
            min_value=0.0,
            max_value=14.0,
            value=6.6,
            step=0.1
        )

        st.subheader(
            "🧼 Contrôles"
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

    st.divider()

    start_analysis = st.button(
        "🚀 LANCER L'ANALYSE FOODNEXA",
        use_container_width=True,
        type="primary"
    )

    if start_analysis:

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
                "❌ Une erreur est survenue."
            )

            st.code(
                str(error)
            )

            st.stop()

        st.success(
            "✅ Analyse FOODNEXA terminée."
        )

        st.subheader(
            "📊 Résultat"
        )

        r1, r2, r3 = st.columns(3)

        with r1:

            st.metric(
                "RISK SCORE",
                f"{report['risk_score']}/100"
            )

        with r2:

            st.metric(
                "RISK LEVEL",
                report["risk_level"]
            )

        with r3:

            st.metric(
                "CONFIDENCE",
                f"{report['confidence']:.1f}%"
            )

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

        st.subheader(
            "⚠️ Facteurs de risque détectés"
        )

        if report["reasons"]:

            for reason in report["reasons"]:

                st.warning(
                    reason
                )

        else:

            st.success(
                "Aucun facteur de risque détecté."
            )

        st.subheader(
            "💡 Recommandations"
        )

        for recommendation in report["recommendations"]:

            st.info(
                recommendation
            )

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
                f"💾 Lot {batch_id} enregistré."
            )

        except Exception as error:

            st.warning(
                "L'analyse est terminée mais "
                "l'enregistrement a rencontré un problème."
            )

            st.code(
                str(error)
            )


# =====================================================
# RESEARCH DATA
# =====================================================

elif page == "🧪 Research Data":

    st.title(
        "🧪 FOODNEXA Research Data"
    )

    st.write(
        "Interface de collecte structurée des données "
        "destinées à la recherche et au développement "
        "du futur modèle prédictif."
    )

    st.warning(
        """
        ⚠️ Utilisez uniquement des données réelles correctement
        identifiées ou des données synthétiques clairement
        documentées comme synthétiques.
        """
    )

    st.divider()

    # =================================================
    # ADD OBSERVATION
    # =================================================

    st.subheader(
        "📝 Ajouter une observation"
    )

    research_col1, research_col2 = st.columns(2)

    with research_col1:

        research_batch_id = st.text_input(
            "ID du lot",
            placeholder="Exemple : R-LOT-001",
            key="research_batch_id"
        )

        research_product = st.text_input(
            "Produit",
            value="Lait pasteurisé",
            key="research_product"
        )

        research_temperature = st.number_input(
            "Température (°C)",
            min_value=-20.0,
            max_value=50.0,
            value=4.0,
            step=0.1,
            key="research_temperature"
        )

        research_storage = st.number_input(
            "Durée de stockage (jours)",
            min_value=0,
            max_value=365,
            value=2,
            step=1,
            key="research_storage"
        )

        research_ph = st.number_input(
            "pH",
            min_value=0.0,
            max_value=14.0,
            value=6.6,
            step=0.1,
            key="research_ph"
        )

    with research_col2:

        research_cold_chain = st.checkbox(
            "Interruption chaîne du froid",
            key="research_cold_chain"
        )

        research_hygiene = st.checkbox(
            "Hygiène maîtrisée",
            value=True,
            key="research_hygiene"
        )

        research_pasteurized = st.checkbox(
            "Produit pasteurisé",
            value=True,
            key="research_pasteurized"
        )

        st.markdown(
            "#### 🧫 Résultats microbiologiques"
        )

        total_viable_count = st.number_input(
            "Total Viable Count",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="total_viable_count"
        )

        enterobacteriaceae_count = st.number_input(
            "Enterobacteriaceae",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="enterobacteriaceae_count"
        )

        coliform_count = st.number_input(
            "Coliforms",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="coliform_count"
        )

        staphylococcus_aureus_count = st.number_input(
            "Staphylococcus aureus",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="staphylococcus_aureus_count"
        )

    st.markdown(
        "#### 🦠 Résultats pathogènes / qualité"
    )

    path_col1, path_col2, path_col3 = st.columns(3)

    with path_col1:

        salmonella_detected = st.selectbox(
            "Salmonella",
            [
                "Non analysé",
                "Non détectée",
                "Détectée"
            ],
            key="salmonella_detected"
        )

    with path_col2:

        sensory_status = st.selectbox(
            "État sensoriel",
            [
                "Non évalué",
                "Conforme",
                "Non conforme"
            ],
            key="sensory_status"
        )

    with path_col3:

        nonconformity_detected = st.selectbox(
            "Non-conformité",
            [
                "Non évaluée",
                "Non",
                "Oui"
            ],
            key="nonconformity_detected"
        )

    expert_risk_label = st.selectbox(
        "Expert Risk Label",
        [
            "Non attribué",
            "Faible",
            "Modéré",
            "Élevé"
        ],
        key="expert_risk_label"
    )

    st.divider()

    save_research = st.button(
        "💾 ENREGISTRER L'OBSERVATION",
        use_container_width=True,
        type="primary"
    )

    if save_research:

        if not research_batch_id.strip():

            st.warning(
                "⚠️ Veuillez saisir un ID de lot."
            )

            st.stop()

        new_research_row = {

            "batch_id":
                research_batch_id,

            "product_name":
                research_product,

            "temperature_celsius":
                research_temperature,

            "storage_days":
                research_storage,

            "ph":
                research_ph,

            "cold_chain_broken":
                research_cold_chain,

            "hygiene_controlled":
                research_hygiene,

            "pasteurized":
                research_pasteurized,

            "total_viable_count":
                total_viable_count,

            "enterobacteriaceae_count":
                enterobacteriaceae_count,

            "coliform_count":
                coliform_count,

            "staphylococcus_aureus_count":
                staphylococcus_aureus_count,

            "salmonella_detected":
                salmonella_detected,

            "sensory_status":
                sensory_status,

            "nonconformity_detected":
                nonconformity_detected,

            "expert_risk_label":
                expert_risk_label
        }

        new_research_df = pd.DataFrame(
            [new_research_row],
            columns=RESEARCH_COLUMNS
        )

        try:

            if os.path.exists(
                RESEARCH_CSV_FILE
            ):

                old_research = pd.read_csv(
                    RESEARCH_CSV_FILE
                )

                for column in RESEARCH_COLUMNS:

                    if column not in old_research.columns:

                        old_research[column] = ""

                old_research = old_research[
                    RESEARCH_COLUMNS
                ]

                final_research = pd.concat(
                    [
                        old_research,
                        new_research_df
                    ],
                    ignore_index=True
                )

            else:

                final_research = new_research_df

            final_research.to_csv(
                RESEARCH_CSV_FILE,
                index=False,
                encoding="utf-8-sig"
            )

            research_data = final_research

            st.success(
                f"✅ Observation {research_batch_id} "
                "enregistrée dans le Research Dataset."
            )

        except Exception as error:

            st.error(
                "❌ Impossible d'enregistrer l'observation."
            )

            st.code(
                str(error)
            )


    # =================================================
    # DATASET
    # =================================================

    st.divider()

    st.subheader(
        "📊 Research Dataset"
    )

    if os.path.exists(
        RESEARCH_CSV_FILE
    ):

        try:

            research_view = pd.read_csv(
                RESEARCH_CSV_FILE
            )

            st.metric(
                "Nombre d'observations",
                len(research_view)
            )

            st.dataframe(
                research_view,
                use_container_width=True,
                hide_index=True
            )

        except Exception as error:

            st.error(
                "Impossible de lire le Research Dataset."
            )

            st.code(
                str(error)
            )

            research_view = pd.DataFrame()

    else:

        st.info(
            "Aucune observation enregistrée pour le moment."
        )

        research_view = pd.DataFrame(
            columns=RESEARCH_COLUMNS
        )


    # =================================================
    # DATA QUALITY ENGINE
    # =================================================

    st.divider()

    st.subheader(
        "🔍 FOODNEXA Data Quality Check"
    )

    if not research_view.empty:

        try:

            quality_report = generate_quality_report(
                research_view
            )

            q1, q2, q3, q4 = st.columns(4)

            with q1:

                st.metric(
                    "Observations",
                    quality_report["rows"]
                )

            with q2:

                st.metric(
                    "Colonnes",
                    quality_report["columns"]
                )

            with q3:

                st.metric(
                    "Quality Score",
                    f"{quality_report['quality_score']:.1f}%"
                )

            with q4:

                st.metric(
                    "Doublons",
                    quality_report["duplicates"]
                )


            # -----------------------------------------
            # STATUS
            # -----------------------------------------

            if quality_report["status"] == "GOOD":

                st.success(
                    "🟢 DATASET STATUS: GOOD"
                )

            else:

                st.warning(
                    "🟠 DATASET STATUS: REVIEW REQUIRED"
                )


            # -----------------------------------------
            # MISSING COLUMNS
            # -----------------------------------------

            if quality_report["missing_columns"]:

                st.error(
                    "❌ Colonnes obligatoires manquantes:"
                )

                for column in quality_report[
                    "missing_columns"
                ]:

                    st.write(
                        f"• {column}"
                    )

            else:

                st.success(
                    "✅ Toutes les colonnes requises "
                    "sont présentes."
                )


            # -----------------------------------------
            # MISSING VALUES
            # -----------------------------------------

            st.subheader(
                "📋 Valeurs manquantes"
            )

            if quality_report["missing_values"]:

                missing_df = pd.DataFrame(
                    [
                        {
                            "Variable": column,
                            "Valeurs manquantes": count
                        }
                        for column, count
                        in quality_report[
                            "missing_values"
                        ].items()
                    ]
                )

                st.dataframe(
                    missing_df,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.success(
                    "✅ Aucune valeur manquante détectée."
                )


            # -----------------------------------------
            # DUPLICATES
            # -----------------------------------------

            st.subheader(
                "♻️ Doublons"
            )

            if quality_report["duplicates"] == 0:

                st.success(
                    "✅ Aucun doublon détecté."
                )

            else:

                st.warning(
                    f"⚠️ {quality_report['duplicates']} "
                    "doublon(s) détecté(s)."
                )


            # -----------------------------------------
            # RANGE ISSUES
            # -----------------------------------------

            st.subheader(
                "📏 Contrôle des plages de valeurs"
            )

            if quality_report["range_issues"]:

                for issue in quality_report[
                    "range_issues"
                ]:

                    st.warning(
                        f"⚠️ {issue}"
                    )

            else:

                st.success(
                    "✅ Aucune anomalie de plage détectée."
                )


            # -----------------------------------------
            # SCIENTIFIC NOTE
            # -----------------------------------------

            st.info(
                """
                **Important :** le Data Quality Score mesure
                la qualité technique du dataset uniquement.
                Ce n'est pas un score de sécurité alimentaire
                et ce n'est pas une validation scientifique
                du futur modèle prédictif.
                """
            )


            # -----------------------------------------
            # DOWNLOAD
            # -----------------------------------------

            st.subheader(
                "📥 Export"
            )

            research_csv = research_view.to_csv(
                index=False
            ).encode(
                "utf-8-sig"
            )

            st.download_button(
                "⬇️ Télécharger Research Dataset",
                data=research_csv,
                file_name="foodnexa_research_dataset.csv",
                mime="text/csv",
                use_container_width=True
            )


        except Exception as error:

            st.error(
                "❌ Le Data Quality Engine "
                "a rencontré une erreur."
            )

            st.code(
                str(error)
            )

    else:

        st.info(
            "Ajoutez au moins une observation "
            "pour lancer le Data Quality Check."
        )


# =====================================================
# HISTORY
# =====================================================

elif page == "📁 Historique":

    st.title(
        "📁 Historique FOODNEXA"
    )

    if history.empty:

        st.info(
            "Aucune analyse enregistrée."
        )

    else:

        st.write(
            f"Nombre total d'analyses : "
            f"**{len(history)}**"
        )

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        csv_data = history.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            "⬇️ Télécharger le dataset CSV",
            data=csv_data,
            file_name="foodnexa_assessments.csv",
            mime="text/csv",
            use_container_width=True
        )


# =====================================================
# RESEARCH PROTOTYPE
# =====================================================

elif page == "🧬 Research Prototype":

    st.title(
        "🧬 FOODNEXA Research Prototype"
    )

    st.info(
        """
        **FOODNEXA** est actuellement un prototype
        expérimental basé sur des règles explicables.

        L'objectif est de construire progressivement
        une base de données structurée permettant
        ensuite d'étudier des approches statistiques
        et de Machine Learning.
        """
    )

    st.subheader(
        "🔬 Architecture actuelle"
    )

    architecture = pd.DataFrame(
        {
            "Module": [
                "Data Input",
                "Risk Engine",
                "Explainability",
                "Risk Classification",
                "Recommendations",
                "Research Dataset",
                "Data Quality Engine",
                "Feature Engineering",
                "Machine Learning",
                "Validation"
            ],

            "État": [
                "Disponible",
                "Disponible",
                "Disponible",
                "Disponible",
                "Disponible",
                "Disponible",
                "Disponible",
                "À développer",
                "À développer",
                "À développer"
            ]
        }
    )

    st.dataframe(
        architecture,
        use_container_width=True,
        hide_index=True
    )

    st.subheader(
        "🎯 Objectif scientifique"
    )

    st.write(
        """
        Construire progressivement un dataset de lots
        alimentaires contenant des variables de procédé,
        de stockage, de qualité et, lorsque disponibles,
        des résultats microbiologiques et des observations
        d'experts.

        Après contrôle de qualité et préparation des variables,
        le dataset pourra être utilisé pour étudier et comparer
        différentes approches de prévision du risque.
        """
    )

    st.subheader(
        "🧠 Pipeline prévu"
    )

    pipeline = pd.DataFrame(
        {
            "Étape": [
                "Collecte des données",
                "Data Quality",
                "Nettoyage",
                "Feature Engineering",
                "Séparation Train/Test",
                "Entraînement ML",
                "Validation",
                "Évaluation",
                "Risk Prediction"
            ],

            "Statut": [
                "En cours",
                "Disponible",
                "À développer",
                "À développer",
                "À développer",
                "À développer",
                "À développer",
                "À développer",
                "À développer"
            ]
        }
    )

    st.dataframe(
        pipeline,
        use_container_width=True,
        hide_index=True
    )

    st.warning(
        """
        ⚠️ Les résultats actuels sont expérimentaux.
        Ils ne constituent pas une validation scientifique
        ou réglementaire et ne remplacent pas les analyses
        de laboratoire.
        """
    )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.markdown(
    """
    <div class="footer-text">

    <b>FOODNEXA</b>
    — FOOD SAFETY / RISK INTELLIGENCE

    <br>

    Intelligent Food Safety Risk Assessment

    <br><br>

    Experimental decision-support prototype.
    Not a replacement for laboratory analysis,
    regulatory requirements or quality-management decisions.

    </div>
    """,
    unsafe_allow_html=True
)
