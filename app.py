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
        margin-bottom: 25px;
    }

    .dashboard-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        background-color: #F8FAFC;
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
# LOAD HISTORY
# =====================================================

if os.path.exists(CSV_FILE):

    try:

        history = pd.read_csv(CSV_FILE)

    except Exception:

        history = pd.DataFrame()

else:

    history = pd.DataFrame()


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

    st.markdown("## 🛡️ FOODNEXA")

    st.caption(
        "FOOD SAFETY / RISK INTELLIGENCE"
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🔬 Nouvelle analyse",
            "📁 Historique",
            "🧪 Research Prototype"
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


    # -------------------------------------------------
    # NO DATA
    # -------------------------------------------------

    if history.empty:

        st.info(
            "Aucune analyse disponible. "
            "Lancez votre première analyse pour alimenter "
            "le dashboard."
        )


    else:

        # -------------------------------------------------
        # DATA CLEANING
        # -------------------------------------------------

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


        # -------------------------------------------------
        # KPI
        # -------------------------------------------------

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


        # -------------------------------------------------
        # KPI ROW 1
        # -------------------------------------------------

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


        # -------------------------------------------------
        # KPI ROW 2
        # -------------------------------------------------

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


        # -------------------------------------------------
        # RISK DISTRIBUTION
        # -------------------------------------------------

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
            distribution.set_index("Niveau")
        )


        # -------------------------------------------------
        # SCORE TREND
        # -------------------------------------------------

        if len(history) > 1:

            st.subheader(
                "📈 Évolution des Risk Scores"
            )

            score_history = history[
                ["batch_id", "risk_score"]
            ].copy()

            score_history = score_history.dropna()

            if not score_history.empty:

                score_history = score_history.set_index(
                    "batch_id"
                )

                st.line_chart(
                    score_history
                )


        # -------------------------------------------------
        # RECENT ANALYSES
        # -------------------------------------------------

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


    # -------------------------------------------------
    # LEFT
    # -------------------------------------------------

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


    # -------------------------------------------------
    # RIGHT
    # -------------------------------------------------

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
            "Conditions d'hygiène maîtrisées",
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
        # ANALYSIS
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
                "❌ Une erreur est survenue."
            )

            st.code(
                str(error)
            )

            st.stop()


        # -------------------------------------------------
        # RESULT
        # -------------------------------------------------

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


        # -------------------------------------------------
        # STATUS
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


        # -------------------------------------------------
        # FACTORS
        # -------------------------------------------------

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


        # -------------------------------------------------
        # REASONS
        # -------------------------------------------------

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


        # -------------------------------------------------
        # RECOMMENDATIONS
        # -------------------------------------------------

        st.subheader(
            "💡 Recommandations"
        )


        for recommendation in report["recommendations"]:

            st.info(
                recommendation
            )


        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------

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
            f"Nombre total d'analyses : **{len(history)}**"
        )


        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )


        st.divider()


        st.subheader(
            "📥 Export des données"
        )


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

elif page == "🧪 Research Prototype":

    st.title(
        "🧪 FOODNEXA Research Prototype"
    )


    st.info(
        """
        **FOODNEXA** est actuellement un prototype
        expérimental basé sur des règles explicables.

        L'objectif de cette phase est de construire
        progressivement une base de données structurée
        permettant ensuite d'étudier des approches
        statistiques et de Machine Learning.
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
                "Historical Dataset"
            ],

            "État": [
                "Disponible",
                "Disponible",
                "Disponible",
                "Disponible",
                "Disponible",
                "En construction"
            ]
        }
    )


    st.dataframe(
        architecture,
        use_container_width=True,
        hide_index=True
    )


    st.subheader(
        "🎯 Prochain objectif scientifique"
    )


    st.write(
        """
        Construire progressivement un dataset de lots
        alimentaires avec variables mesurables, résultats
        analytiques et événements de non-conformité.

        Cette base pourra ensuite servir à comparer
        différentes méthodes de prévision du risque.
        """
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
