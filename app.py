import os
import streamlit as st
import pandas as pd

from foodguard_engine import assess_dairy_food_safety_risk
from foodnexa_data_quality import generate_quality_report
from foodnexa_supabase import (
    save_risk_assessment,
    save_research_observation,
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
.block-container {max-width:1400px;padding-top:1.5rem;padding-bottom:3rem;}
.foodnexa-tagline {text-align:center;color:#20A36A;font-size:17px;
font-weight:700;letter-spacing:1px;margin:8px 0 20px;}
.foodnexa-line {height:4px;width:100%;background:linear-gradient(
90deg,#0B2A4A,#00A6C7,#20A36A);border-radius:10px;margin-bottom:25px;}
.footer-text {text-align:center;color:#64748B;font-size:13px;
line-height:1.7;padding:15px;}
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


def show_error(title, error):
    st.warning(title)
    # Do not display credentials or secret values in the UI.
    st.caption(f"Détail technique : {type(error).__name__}")


history = load_csv(CSV_FILE)
research_data = load_csv(RESEARCH_CSV_FILE, RESEARCH_COLUMNS)

if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=700)
else:
    st.markdown("# 🛡️ FOODNEXA")

st.markdown(
    '<div class="foodnexa-tagline">INTELLIGENT FOOD SAFETY RISK ASSESSMENT</div>',
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
                     use_container_width=True, hide_index=True)


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
                 use_container_width=True, type="primary"):
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
            st.error("Une erreur est survenue pendant l'analyse.")
            st.caption(type(error).__name__)
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
        st.dataframe(pd.DataFrame(factor_data), use_container_width=True, hide_index=True)

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
# RESEARCH DATA + SUPABASE
# =====================================================

elif page == "🧪 Research Data":
    st.title("🧪 FOODNEXA Research Data")
    st.write("Collecte structurée des données destinées à la recherche.")
    st.warning("Utilisez des données réelles correctement identifiées ou des données synthétiques clairement documentées.")
    st.divider()
    st.subheader("📝 Ajouter une observation")
    c1, c2 = st.columns(2)
    with c1:
        research_batch_id = st.text_input("ID du lot", placeholder="Exemple : R-LOT-001", key="research_batch_id")
        research_product = st.text_input("Produit", value="Lait pasteurisé", key="research_product")
        research_temperature = st.number_input("Température (°C)", -20.0, 50.0, 4.0, 0.1, key="research_temperature")
        research_storage = st.number_input("Durée de stockage (jours)", 0, 365, 2, 1, key="research_storage")
        research_ph = st.number_input("pH", 0.0, 14.0, 6.6, 0.1, key="research_ph")
    with c2:
        research_cold_chain = st.checkbox("Interruption chaîne du froid", key="research_cold_chain")
        research_hygiene = st.checkbox("Hygiène maîtrisée", value=True, key="research_hygiene")
        research_pasteurized = st.checkbox("Produit pasteurisé", value=True, key="research_pasteurized")
        st.markdown("#### 🧫 Résultats microbiologiques")
        total_viable_count = st.number_input("Total Viable Count", min_value=0.0, value=0.0, key="total_viable_count")
        enterobacteriaceae_count = st.number_input("Enterobacteriaceae", min_value=0.0, value=0.0, key="enterobacteriaceae_count")
        coliform_count = st.number_input("Coliforms", min_value=0.0, value=0.0, key="coliform_count")
        staphylococcus_aureus_count = st.number_input("Staphylococcus aureus", min_value=0.0, value=0.0, key="staphylococcus_aureus_count")

    st.markdown("#### 🦠 Résultats pathogènes / qualité")
    p1, p2, p3 = st.columns(3)
    with p1:
        salmonella_detected = st.selectbox("Salmonella", ["Non analysé", "Non détectée", "Détectée"], key="salmonella_detected")
    with p2:
        sensory_status = st.selectbox("État sensoriel", ["Non évalué", "Conforme", "Non conforme"], key="sensory_status")
    with p3:
        nonconformity_detected = st.selectbox("Non-conformité", ["Non évaluée", "Non", "Oui"], key="nonconformity_detected")
    expert_risk_label = st.selectbox("Expert Risk Label", ["Non attribué", "Faible", "Modéré", "Élevé"], key="expert_risk_label")

    if st.button("💾 ENREGISTRER L'OBSERVATION", use_container_width=True, type="primary"):
        if not research_batch_id.strip():
            st.warning("Veuillez saisir un ID de lot.")
            st.stop()

        observation = {
            "batch_id": research_batch_id.strip(),
            "product_name": research_product,
            "temperature_celsius": research_temperature,
            "storage_days": research_storage,
            "ph": research_ph,
            "cold_chain_broken": research_cold_chain,
            "hygiene_controlled": research_hygiene,
            "pasteurized": research_pasteurized,
            "total_viable_count": total_viable_count,
            "enterobacteriaceae_count": enterobacteriaceae_count,
            "coliform_count": coliform_count,
            "staphylococcus_aureus_count": staphylococcus_aureus_count,
            "salmonella_detected": (
                True if salmonella_detected == "Détectée"
                else False if salmonella_detected == "Non détectée" else None
            ),
            "sensory_status": sensory_status,
            "nonconformity_detected": (
                True if nonconformity_detected == "Oui"
                else False if nonconformity_detected == "Non" else None
            ),
            "expert_risk_label": (
                None if expert_risk_label == "Non attribué" else expert_risk_label
            ),
        }

        # CSV stores the human-readable labels for research review.
        csv_observation = dict(observation)
        csv_observation["salmonella_detected"] = salmonella_detected
        csv_observation["nonconformity_detected"] = nonconformity_detected
        csv_observation["expert_risk_label"] = expert_risk_label

        try:
            old = load_csv(RESEARCH_CSV_FILE, RESEARCH_COLUMNS)
            for column in RESEARCH_COLUMNS:
                if column not in old.columns:
                    old[column] = ""
            old = old[RESEARCH_COLUMNS]
            # Replace an existing row with the same batch ID (DB column is UNIQUE).
            if not old.empty and "batch_id" in old.columns:
                old = old[old["batch_id"].astype(str) != research_batch_id.strip()]
            updated = pd.concat([old, pd.DataFrame([csv_observation])], ignore_index=True)
            updated.to_csv(RESEARCH_CSV_FILE, index=False, encoding="utf-8-sig")
            research_data = updated
            st.success(f"✅ Observation {research_batch_id} enregistrée dans le CSV.")
        except Exception as error:
            show_error("Impossible d'enregistrer le CSV.", error)

        try:
            # The connector helper is expected to accept one dictionary argument.
            save_research_observation(observation)
            st.success("☁️ Observation enregistrée dans Supabase.")
        except Exception as error:
            show_error("Observation CSV conservée, mais sauvegarde Supabase échouée.", error)

    st.divider()
    st.subheader("📊 Research Dataset")
    research_view = load_csv(RESEARCH_CSV_FILE, RESEARCH_COLUMNS)
    if not research_view.empty:
        st.metric("Nombre d'observations", len(research_view))
        st.dataframe(research_view, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🔍 FOODNEXA Data Quality Check")
        try:
            quality = generate_quality_report(research_view)
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Observations", quality["rows"])
            q2.metric("Colonnes", quality["columns"])
            q3.metric("Quality Score", f"{quality['quality_score']:.1f}%")
            q4.metric("Doublons", quality["duplicates"])
            if quality["status"] == "GOOD":
                st.success("🟢 DATASET STATUS: GOOD")
            else:
                st.warning("🟠 DATASET STATUS: REVIEW REQUIRED")
            if quality["missing_columns"]:
                st.error("Colonnes obligatoires manquantes : " + ", ".join(quality["missing_columns"]))
            else:
                st.success("Toutes les colonnes requises sont présentes.")
            st.subheader("📋 Valeurs manquantes")
            missing = quality.get("missing_values", {})
            if missing:
                st.dataframe(pd.DataFrame([{"Variable": k, "Valeurs manquantes": v} for k, v in missing.items()]), use_container_width=True, hide_index=True)
            else:
                st.success("Aucune valeur manquante détectée.")
            st.subheader("♻️ Doublons")
            if quality["duplicates"] == 0:
                st.success("Aucun doublon détecté.")
            else:
                st.warning(f"{quality['duplicates']} doublon(s) détecté(s).")
            st.subheader("📏 Contrôle des plages de valeurs")
            if quality["range_issues"]:
                for issue in quality["range_issues"]:
                    st.warning(issue)
            else:
                st.success("Aucune anomalie de plage détectée.")
            st.info("Le Data Quality Score mesure la qualité technique du dataset. Il ne constitue pas une validation scientifique.")
        except Exception as error:
            show_error("Le Data Quality Engine a rencontré une erreur.", error)
        st.download_button(
            "⬇️ Télécharger Research Dataset",
            data=research_view.to_csv(index=False).encode("utf-8-sig"),
            file_name="foodnexa_research_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Ajoutez au moins une observation pour lancer le Data Quality Check.")


# =====================================================
# RESEARCH ANALYTICS
# =====================================================

elif page == "📊 Research Analytics":
    st.title("📊 FOODNEXA Research Analytics")
    st.write("Analyse exploratoire du Research Dataset.")
    st.warning("Cette analyse est exploratoire et ne constitue pas encore un modèle prédictif validé scientifiquement.")
    data = load_csv(RESEARCH_CSV_FILE)
    if data.empty:
        st.info("Aucun Research Dataset disponible.")
    else:
        numeric = [
            "temperature_celsius", "storage_days", "ph", "total_viable_count",
            "enterobacteriaceae_count", "coliform_count", "staphylococcus_aureus_count",
        ]
        for col in numeric:
            if col in data:
                data[col] = pd.to_numeric(data[col], errors="coerce")
        risk_map = {"Faible": 0, "Modéré": 1, "Élevé": 2}
        if "expert_risk_label" in data:
            data["risk_numeric"] = data["expert_risk_label"].map(risk_map)
        total = len(data)
        classes = data["expert_risk_label"].replace("Non attribué", pd.NA).dropna().nunique() if "expert_risk_label" in data else 0
        salmonella_rate = data["salmonella_detected"].astype(str).str.lower().eq("détectée").mean() * 100 if "salmonella_detected" in data else 0
        nonconformity_rate = data["nonconformity_detected"].astype(str).str.lower().eq("oui").mean() * 100 if "nonconformity_detected" in data else 0
        st.subheader("📌 Vue générale")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Observations", total)
        a2.metric("Classes de risque", classes)
        a3.metric("Salmonella détectée", f"{salmonella_rate:.1f}%")
        a4.metric("Non-conformités", f"{nonconformity_rate:.1f}%")
        st.divider()
        if "expert_risk_label" in data:
            st.subheader("🎯 Distribution des niveaux de risque")
            dist = data["expert_risk_label"].value_counts().reindex(["Faible", "Modéré", "Élevé"], fill_value=0)
            dist_df = pd.DataFrame({"Niveau de risque": dist.index, "Nombre": dist.values})
            st.bar_chart(dist_df.set_index("Niveau de risque"))
            dist_df["Pourcentage"] = (dist_df["Nombre"] / total * 100).round(1)
            st.dataframe(dist_df, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("📐 Statistiques descriptives")
        labels = {
            "temperature_celsius": "Température moyenne (°C)",
            "storage_days": "Durée moyenne de stockage (jours)", "ph": "pH moyen",
            "total_viable_count": "Total Viable Count moyen",
            "enterobacteriaceae_count": "Enterobacteriaceae moyen",
            "coliform_count": "Coliformes moyen",
            "staphylococcus_aureus_count": "Staphylococcus aureus moyen",
        }
        rows = []
        for col, label in labels.items():
            if col in data:
                rows.append({
                    "Variable": label, "Moyenne": round(data[col].mean(), 2),
                    "Médiane": round(data[col].median(), 2),
                    "Minimum": round(data[col].min(), 2), "Maximum": round(data[col].max(), 2),
                })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🔬 Facteurs par niveau de risque")
        available = [c for c in numeric if c in data.columns]
        if "expert_risk_label" in data and available:
            means = data.groupby("expert_risk_label")[available].mean().reindex(["Faible", "Modéré", "Élevé"]).round(2)
            st.dataframe(means, use_container_width=True)
        else:
            st.info("Pas assez de données pour cette analyse.")
        st.divider()
        st.subheader("📈 Analyse exploratoire des corrélations")
        if "risk_numeric" in data:
            corr_rows = []
            for col in available:
                temp = data[[col, "risk_numeric"]].dropna()
                if len(temp) >= 2:
                    corr = temp[col].corr(temp["risk_numeric"])
                    if pd.notna(corr):
                        corr_rows.append({"Variable": col, "Corrélation avec le risque": round(corr, 3)})
            if corr_rows:
                corr_df = pd.DataFrame(corr_rows)
                corr_df["abs"] = corr_df["Corrélation avec le risque"].abs()
                st.dataframe(corr_df.sort_values("abs", ascending=False).drop(columns="abs"),
                             use_container_width=True, hide_index=True)
                st.info("Une corrélation indique une association statistique, pas une causalité.")
            else:
                st.info("Pas assez de données pour calculer les corrélations.")
        else:
            st.info("Les labels de risque sont nécessaires pour cette analyse.")
        st.divider()
        st.subheader("📊 Évolution des facteurs")
        chart_cols = [c for c in ["temperature_celsius", "storage_days", "ph"] if c in data]
        if chart_cols and "batch_id" in data:
            st.line_chart(data.set_index("batch_id")[chart_cols])
        st.divider()
        st.subheader("🧠 Interprétation FOODNEXA")
        st.write("""
        Cette analyse compare les caractéristiques des lots selon leur niveau de risque déclaré
        et recherche les variables présentant des associations statistiques. Elle reste exploratoire
        et ne constitue pas une validation scientifique.
        """)
        st.success("Prochaine étape : Feature Engineering → Train/Test → Machine Learning → Validation → Évaluation.")


# =====================================================
# HISTORY
# =====================================================

elif page == "📁 Historique":
    st.title("📁 Historique FOODNEXA")
    if history.empty:
        st.info("Aucune analyse enregistrée.")
    else:
        st.write(f"Nombre total d'analyses : **{len(history)}**")
        st.dataframe(history, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Télécharger le dataset CSV",
            data=history.to_csv(index=False).encode("utf-8-sig"),
            file_name="foodnexa_assessments.csv",
            mime="text/csv",
            use_container_width=True,
        )


# =====================================================
# RESEARCH PROTOTYPE
# =====================================================

elif page == "🧬 Research Prototype":
    st.title("🧬 FOODNEXA Research Prototype")
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
    st.dataframe(architecture, use_container_width=True, hide_index=True)
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
    st.dataframe(pipeline, use_container_width=True, hide_index=True)
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
