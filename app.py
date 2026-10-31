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
