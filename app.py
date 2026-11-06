import os
import streamlit as st
import pandas as pd
import re

from foodguard_engine import assess_dairy_food_safety_risk
from foodnexa_data_quality import generate_quality_report
from foodnexa_research_analytics import generate_research_analytics, prepare_research_data
from foodnexa_supabase import (
    save_risk_assessment,
    save_research_observation,
    get_research_observations,
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


def flatten_research_for_analytics(frame):
    """Expand V2 JSONB/CSV domains into the flat columns used by analytics V2."""
    import json

    data = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(frame)
    nested_maps = {
        "physicochemical_results": {},
        "microbiological_results": {
            "escherichia_coli_count": "e_coli_count",
            "yeasts_moulds_count": "yeast_mould_count",
            "listeria_count": "listeria_monocytogenes_count",
        },
        "contaminant_results": {},
        "process_data": {
            "process_temperature_celsius": "processing_temperature_celsius",
            "process_time_minutes": "processing_time_minutes",
        },
        "packaging_results": {"net_weight_g": "net_weight"},
    }
    for source, renames in nested_maps.items():
        if source not in data.columns:
            continue
        expanded = []
        for raw in data[source]:
            if isinstance(raw, dict):
                obj = raw
            elif isinstance(raw, str) and raw.strip():
                try:
                    obj = json.loads(raw)
                except (ValueError, TypeError):
                    obj = {}
            else:
                obj = {}
            if not isinstance(obj, dict):
                obj = {}
            expanded.append({renames.get(k, k): v for k, v in obj.items()})
        for key in sorted({k for obj in expanded for k in obj}):
            if key not in data.columns:
                data[key] = [obj.get(key) for obj in expanded]
            else:
                data[key] = data[key].where(data[key].notna(), [obj.get(key) for obj in expanded])
    if "product_category" not in data.columns:
        data["product_category"] = "Non renseignée"
    else:
        data["product_category"] = data["product_category"].fillna("Non renseignée")
    return data


def show_error(title, error):
    """Display useful Supabase/PostgREST diagnostics without exposing credentials."""
    st.error(title)
    st.caption(f"Type d'erreur : {type(error).__name__}")

    # Supabase PostgREST errors expose these fields. Never print request headers,
    # URLs containing tokens, or Streamlit Secrets.
    fields = (
        ("Code", getattr(error, "code", None)),
        ("Message", getattr(error, "message", None)),
        ("Détails", getattr(error, "details", None)),
        ("Indice", getattr(error, "hint", None)),
    )
    shown = False
    for label, value in fields:
        if value:
            st.write(f"**{label} :** {value}")
            shown = True

    if not shown:
        # Exception text can be useful for local validation errors; redact common
        # secret formats defensively before showing it.
        message = str(error)
        message = re.sub(r"sb_(?:secret|publishable)_[A-Za-z0-9_-]+", "[SECRET MASQUÉ]", message)
        message = re.sub(r"eyJ[A-Za-z0-9._-]{20,}", "[TOKEN MASQUÉ]", message)
        st.caption(message[:1200] if message else "Aucun détail supplémentaire disponible.")


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
    st.caption("FOODNEXA Research Intelligence V2.1")


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
                     width="stretch", hide_index=True)


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
                 width="stretch", type="primary"):
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
            show_error("Une erreur est survenue pendant l'analyse.", error)
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
        st.dataframe(pd.DataFrame(factor_data), width="stretch", hide_index=True)

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
    st.title("🧪 FOODNEXA Research Data V2")
    st.write("Collecte multi-produits des résultats physico-chimiques, microbiologiques, sensoriels et technologiques.")
    st.info("Saisissez uniquement les résultats réellement mesurés. Les champs sont facultatifs sauf l'identifiant du lot et le produit. Les limites de conformité doivent être documentées selon le produit, la méthode et la réglementation applicable.")

    def optional_float(label, key, help_text=None):
        raw = st.text_input(label, key=key, help=help_text, placeholder="Laisser vide si non analysé")
        if not raw.strip():
            return None
        try:
            value = float(raw.strip().replace(",", "."))
            if not pd.notna(value):
                raise ValueError
            return value
        except ValueError:
            st.error(f"Valeur numérique invalide : {label}")
            return "__INVALID__"

    with st.form("research_data_v2_form"):
        st.subheader("1. Identification et traçabilité")
        a, b, c = st.columns(3)
        with a:
            research_batch_id = st.text_input("ID du lot *", key="research_v2_batch")
            research_product = st.text_input("Nom du produit *", value="Lait pasteurisé", key="research_v2_product")
            product_category = st.selectbox("Catégorie", ["Produits laitiers", "Céréales et farines", "Fruits et légumes", "Huiles et matières grasses", "Viandes et poissons", "Boulangerie", "Boissons", "Autre"], key="research_v2_category")
        with b:
            supplier = st.text_input("Fournisseur", key="research_v2_supplier")
            sampling_date = st.date_input("Date de prélèvement", key="research_v2_sampling_date")
            analysis_date = st.date_input("Date d'analyse", key="research_v2_analysis_date")
        with c:
            sample_reference = st.text_input("Référence échantillon", key="research_v2_sample")
            laboratory = st.text_input("Laboratoire / source", key="research_v2_lab")
            analyst = st.text_input("Analyste / responsable", key="research_v2_analyst")

        st.subheader("2. Conditions de conservation et procédé")
        x1, x2, x3 = st.columns(3)
        with x1:
            temperature = optional_float("Température (°C)", "research_v2_temp")
            storage_days = optional_float("Durée stockage (jours)", "research_v2_storage")
            ph = optional_float("pH", "research_v2_ph")
        with x2:
            cold_chain = st.selectbox("Rupture chaîne du froid", ["Non renseigné", "Non", "Oui"], key="research_v2_cold")
            hygiene = st.selectbox("Hygiène maîtrisée", ["Non renseigné", "Oui", "Non"], key="research_v2_hygiene")
            pasteurized = st.selectbox("Traitement thermique", ["Non renseigné", "Pasteurisé", "Stérilisé", "UHT", "Aucun / autre"], key="research_v2_heat")
        with x3:
            process_temp = optional_float("Température procédé (°C)", "research_v2_process_temp")
            process_time = optional_float("Durée procédé (min)", "research_v2_process_time")
            brix = optional_float("Brix (°Bx)", "research_v2_brix")

        st.subheader("3. Analyses physico-chimiques")
        st.caption("Valeurs facultatives : renseignez la valeur et l'unité du rapport laboratoire.")
        phys_labels = {
            "moisture_percent": "Humidité (%)",
            "dry_matter_percent": "Matière sèche (%)",
            "ash_percent": "Cendres (%)",
            "protein_percent": "Protéines (%)",
            "fat_percent": "Matières grasses (%)",
            "titratable_acidity": "Acidité titrable",
            "density": "Densité",
            "conductivity": "Conductivité",
            "viscosity": "Viscosité",
            "salt_percent": "Sel (%)",
            "peroxide_value": "Indice de peroxyde",
            "free_fatty_acidity": "Acidité grasse / AGL",
        }
        physicochemical = {}
        cols = st.columns(3)
        for i, (key, label) in enumerate(phys_labels.items()):
            with cols[i % 3]:
                physicochemical[key] = optional_float(label, f"research_v2_phys_{key}")

        st.subheader("4. Analyses microbiologiques")
        micro_labels = {
            "total_viable_count": "Flore totale",
            "enterobacteriaceae_count": "Enterobacteriaceae",
            "coliform_count": "Coliformes",
            "e_coli_count": "E. coli",
            "yeast_mould_count": "Levures et moisissures",
            "staphylococcus_aureus_count": "Staphylococcus aureus",
            "bacillus_cereus_count": "Bacillus cereus",
            "listeria_monocytogenes_count": "Listeria monocytogenes",
        }
        microbiology = {}
        cols = st.columns(3)
        for i, (key, label) in enumerate(micro_labels.items()):
            with cols[i % 3]:
                microbiology[key] = optional_float(f"{label} (UFC/g, UFC/mL ou unité rapport)", f"research_v2_micro_{key}")
        pathogen = st.selectbox("Salmonella", ["Non analysée", "Non détectée", "Détectée"], key="research_v2_salmonella")

        st.subheader("5. Sensoriel, contaminants et emballage")
        d1, d2 = st.columns(2)
        with d1:
            sensory_status = st.selectbox("Évaluation sensorielle", ["Non évaluée", "Conforme", "Non conforme"], key="research_v2_sensory")
            sensory_notes = st.text_area("Notes sensorielles (odeur, goût, couleur, texture)", key="research_v2_sensory_notes")
            pesticide = optional_float("Résidus pesticides", "research_v2_pesticide")
            lead = optional_float("Plomb (mg/kg ou unité rapport)", "research_v2_lead")
            cadmium = optional_float("Cadmium (mg/kg ou unité rapport)", "research_v2_cadmium")
            mercury = optional_float("Mercure (mg/kg ou unité rapport)", "research_v2_mercury")
            arsenic = optional_float("Arsenic (mg/kg ou unité rapport)", "research_v2_arsenic")
            aflatoxin = optional_float("Aflatoxines", "research_v2_aflatoxin")
            mycotoxin = optional_float("Autres mycotoxines", "research_v2_mycotoxin")
        with d2:
            packaging_integrity = st.selectbox("Intégrité emballage", ["Non évaluée", "Conforme", "Non conforme"], key="research_v2_packaging")
            net_weight = optional_float("Poids net mesuré (g)", "research_v2_weight")
            seal_integrity_score = optional_float("Score intégrité scellage", "research_v2_seal_score")
            vacuum_level = optional_float("Niveau de vide (unité rapport)", "research_v2_vacuum")
            seal_check = st.selectbox("Contrôle scellage", ["Non évalué", "Conforme", "Non conforme"], key="research_v2_seal")
            nonconformity = st.selectbox("Non-conformité confirmée", ["Non évaluée", "Non", "Oui"], key="research_v2_nonconf")
            expert_label = st.selectbox("Classification expert qualité", ["Non attribuée", "Faible", "Modéré", "Élevé"], key="research_v2_risk")

        st.subheader("6. Méthodes, unités et références")
        units = st.text_input("Unités complémentaires / précisions", placeholder="Ex. UFC/g, mg/kg, g/100g…", key="research_v2_units")
        methods = st.text_input("Méthodes d'analyse / normes utilisées", placeholder="Ex. ISO, méthode interne, référence laboratoire…", key="research_v2_methods")
        limits = st.text_area("Limites / critères applicables et source", placeholder="Indiquer valeur limite, unité, produit concerné et référence réglementaire ou spécification.", key="research_v2_limits")
        notes = st.text_area("Commentaires complémentaires", key="research_v2_notes")
        submitted = st.form_submit_button("💾 ENREGISTRER L'OBSERVATION V2", type="primary", use_container_width=True)

    if submitted:
        numeric_values = [temperature, storage_days, ph, process_temp, process_time, brix,
                          *physicochemical.values(), *microbiology.values(), pesticide,
                          lead, cadmium, mercury, arsenic, aflatoxin, mycotoxin,
                          net_weight, seal_integrity_score, vacuum_level]
        if not research_batch_id.strip() or not research_product.strip():
            st.error("L'identifiant du lot et le nom du produit sont obligatoires.")
        elif "__INVALID__" in numeric_values:
            st.error("Corrigez les valeurs numériques signalées.")
        else:
            observation = {
                "batch_id": research_batch_id.strip(),
                "product_name": research_product.strip(),
                "product_category": product_category,
                "sample_reference": sample_reference or None,
                "supplier": supplier or None,
                "sampling_date": str(sampling_date),
                "analysis_date": str(analysis_date),
                "laboratory": laboratory or None,
                "analyst": analyst or None,
                "temperature_celsius": temperature,
                "storage_days": storage_days,
                "ph": ph,
                "cold_chain_broken": {"Non renseigné": None, "Non": False, "Oui": True}[cold_chain],
                "hygiene_controlled": {"Non renseigné": None, "Oui": True, "Non": False}[hygiene],
                "pasteurized": {"Non renseigné": None, "Pasteurisé": True, "Stérilisé": True, "UHT": True, "Aucun / autre": False}[pasteurized],
                "process_data": {"processing_temperature_celsius": process_temp, "processing_time_minutes": process_time, "brix": brix},
                "physicochemical_results": {k:v for k,v in physicochemical.items() if v is not None},
                "microbiological_results": {k:v for k,v in microbiology.items() if v is not None},
                "contaminant_results": {"pesticide_residue": pesticide, "lead": lead, "cadmium": cadmium, "mercury": mercury, "arsenic": arsenic, "aflatoxin": aflatoxin, "mycotoxin": mycotoxin},
                "sensory_results": {"status": sensory_status, "notes": sensory_notes or None},
                "packaging_results": {"integrity": packaging_integrity, "net_weight": net_weight, "seal_integrity_score": seal_integrity_score, "vacuum_level": vacuum_level, "seal_check": seal_check},
                "salmonella_detected": {"Non analysée": None, "Non détectée": False, "Détectée": True}[pathogen],
                "sensory_status": None if sensory_status == "Non évaluée" else sensory_status,
                "nonconformity_detected": {"Non évaluée": None, "Non": False, "Oui": True}[nonconformity],
                "expert_risk_label": None if expert_label == "Non attribuée" else expert_label,
                "analysis_units": units or None,
                "analysis_methods": methods or None,
                "applicable_limits_reference": limits or None,
                "notes": notes or None,
            }
            import json
            csv_row = {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
                for key, value in observation.items()
            }
            try:
                old = load_csv(RESEARCH_CSV_FILE)
                if not old.empty and "batch_id" in old.columns:
                    old = old[old["batch_id"].astype(str) != research_batch_id.strip()]
                updated = pd.concat([old, pd.DataFrame([csv_row])], ignore_index=True)
                updated.to_csv(RESEARCH_CSV_FILE, index=False, encoding="utf-8-sig")
                st.success("Observation enregistrée dans le dataset CSV.")
            except Exception as error:
                show_error("Échec de sauvegarde CSV.", error)
            try:
                save_research_observation(observation)
                st.success("Observation enregistrée dans Supabase.")
            except Exception as error:
                show_error("CSV conservé, mais sauvegarde Supabase échouée. Vérifiez la migration SQL V2.", error)

    st.divider()
    st.subheader("📊 Research Dataset")
    research_view = load_csv(RESEARCH_CSV_FILE)
    if not research_view.empty:
        st.metric("Observations", len(research_view))
        st.dataframe(research_view, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Télécharger Research Dataset CSV", research_view.to_csv(index=False).encode("utf-8-sig"), "foodnexa_research_dataset.csv", "text/csv", use_container_width=True)
    else:
        st.info("Aucune observation enregistrée pour le moment.")
    st.warning("Les champs avancés sont dépendants du produit et de la méthode. FOODNEXA ne déclare pas automatiquement la conformité sans limite documentée et référence applicable.")


elif page == "📊 Research Analytics":
    st.title("📊 FOODNEXA Research Intelligence")
    st.write("Analyse descriptive multi-domaines des observations alimentaires, par catégorie de produit.")
    st.warning("Analyses exploratoires uniquement : elles ne prouvent pas la conformité, ne démontrent pas de causalité et ne remplacent pas les analyses de laboratoire.")

    local_data = load_csv(RESEARCH_CSV_FILE)
    cloud_data = pd.DataFrame()
    try:
        cloud_rows = get_research_observations(limit=1000)
        if cloud_rows:
            cloud_data = pd.DataFrame(cloud_rows)
    except Exception:
        st.caption("Lecture Supabase indisponible pour cette session ; affichage des données CSV locales.")

    if not cloud_data.empty and "batch_id" in cloud_data.columns:
        if not local_data.empty and "batch_id" in local_data.columns:
            local_data = local_data[~local_data["batch_id"].astype(str).isin(cloud_data["batch_id"].astype(str))]
        data = pd.concat([cloud_data, local_data], ignore_index=True, sort=False)
    else:
        data = local_data

    if data.empty:
        st.info("Aucune observation disponible. Ajoutez d'abord des données dans Research Data.")
    else:
        analytics_input = flatten_research_for_analytics(data)
        prepared = prepare_research_data(analytics_input)
        categories = ["Toutes"] + sorted(prepared["product_category"].dropna().astype(str).unique().tolist())
        selected_category = st.selectbox("Filtrer par catégorie de produit", categories)
        if selected_category != "Toutes":
            prepared = prepared[prepared["product_category"].astype(str) == selected_category]
        result = generate_research_analytics(prepared)

        c1, c2, c3 = st.columns(3)
        c1.metric("Observations", result["observations"])
        c2.metric("Catégories", int(prepared["product_category"].nunique()))
        c3.metric("Lots distincts", int(prepared["batch_id"].nunique()) if "batch_id" in prepared else result["observations"])

        st.subheader("1. Répartition par catégorie")
        st.dataframe(result["category_summary"], use_container_width=True, hide_index=True)

        st.subheader("2. Statistiques par domaine d'analyse")
        group_labels = {
            "physicochemical": "Physico-chimie",
            "microbiological": "Microbiologie",
            "contaminants": "Contaminants",
            "process": "Procédé",
            "packaging": "Emballage",
        }
        if result["group_statistics"]:
            for group, stats in result["group_statistics"].items():
                with st.expander(group_labels.get(group, group), expanded=True):
                    st.dataframe(stats, use_container_width=True)
        else:
            st.info("Aucun résultat quantitatif mesuré. Les champs vides ne sont jamais considérés comme zéro.")

        st.subheader("3. Répartition des classes de risque expert")
        st.dataframe(result["risk_percentages"], use_container_width=True, hide_index=True)
        if int(result["risk_distribution"]["Nombre"].sum()) > 0:
            st.bar_chart(result["risk_distribution"].set_index("Risk Level")["Nombre"])

        st.subheader("4. Indicateurs microbiologiques et qualité")
        salmonella = result["salmonella_rate"]
        nonconf = result["nonconformity_rate"]
        q1, q2 = st.columns(2)
        q1.metric("Salmonella détectée", f"{salmonella:.1f}%" if pd.notna(salmonella) else "Non disponible")
        q2.metric("Non-conformité", f"{nonconf:.1f}%" if pd.notna(nonconf) else "Non disponible")
        st.caption("Les taux sont calculés uniquement sur les résultats renseignés. Les tests non réalisés sont exclus du dénominateur.")

        st.subheader("5. Données manquantes")
        if not result["missingness"].empty:
            st.dataframe(result["missingness"], use_container_width=True, hide_index=True)

        st.subheader("6. Corrélations exploratoires avec la classe de risque")
        if not result["correlations"].empty:
            st.dataframe(result["correlations"], use_container_width=True, hide_index=True)
            st.caption("Les corrélations sur de petits échantillons sont instables et ne démontrent pas une relation causale.")
        else:
            st.info("Au moins trois observations avec valeurs et classes variables sont nécessaires pour calculer une corrélation.")

        export_data = prepared.drop(columns=[c for c in prepared.columns if c.endswith("__parsed")], errors="ignore")
        st.download_button("⬇️ Télécharger les données filtrées", export_data.to_csv(index=False).encode("utf-8-sig"), "foodnexa_research_analytics_export.csv", "text/csv", use_container_width=True)


# =====================================================
# HISTORY
# =====================================================

elif page == "📁 Historique":
    st.title("📁 Historique FOODNEXA")
    if history.empty:
        st.info("Aucune analyse enregistrée.")
    else:
        st.write(f"Nombre total d'analyses : **{len(history)}**")
        st.dataframe(history, width="stretch", hide_index=True)
        st.download_button(
            "⬇️ Télécharger le dataset CSV",
            data=history.to_csv(index=False).encode("utf-8-sig"),
            file_name="foodnexa_assessments.csv",
            mime="text/csv",
            width="stretch",
        )


# =====================================================
# RESEARCH PROTOTYPE
# =====================================================

elif page == "🧬 Research Prototype":
    st.title("🧬 FOODNEXA Research Prototype")
    with st.expander("☁️ Diagnostic de connexion Supabase"):
        if st.button("Tester la connexion Supabase", key="test_supabase_connection"):
            try:
                from foodnexa_supabase import test_supabase_connection
                test_result = test_supabase_connection()
                st.success("Connexion Supabase établie. La table lots est accessible.")
                st.caption(f"Lignes retournées : {test_result['rows_returned']}")
            except Exception as error:
                show_error("Le test de connexion Supabase a échoué.", error)
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
    st.dataframe(architecture, width="stretch", hide_index=True)
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
    st.dataframe(pipeline, width="stretch", hide_index=True)
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
