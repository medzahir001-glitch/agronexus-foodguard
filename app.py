        # ==========================================
        # SAVE ANALYSIS TO SUPABASE
        # ==========================================

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
                    "pasteurized": bool(pasteurized)
                },
                factor_scores={
                    name: factor["score"]
                    for name, factor in report["factors"].items()
                },
                reasons=report["reasons"],
                recommendations=report["recommendations"]
            )

            st.success("☁️ Analyse enregistrée dans Supabase.")

        except Exception:
            st.warning(
                "⚠️ Analyse enregistrée localement, "
                "mais l'enregistrement Supabase a échoué. "
                "Vérifiez les paramètres Secrets."
            )
