
import streamlit as st
import pandas as pd
import os

DATA_FILE = "foodnexa_research_dataset.csv"

COLUMNS = [
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
    "expert_risk_label",
]


def load_dataset():
    if os.path.exists(DATA_FILE):
        try:
            data = pd.read_csv(DATA_FILE)
            for column in COLUMNS:
                if column not in data.columns:
                    data[column] = pd.NA
            return data[COLUMNS]
        except Exception:
            st.error("Impossible de lire le dataset.")
            st.stop()

    return pd.DataFrame(columns=COLUMNS)


st.title("🧪 FOODNEXA — Research Data")
st.caption(
    "Enregistrement structuré des données de qualité "
    "et des résultats de laboratoire."
)

st.info(
    "Saisissez uniquement des résultats réellement mesurés. "
    "Laissez les champs inconnus vides. Ne présentez pas "
    "des données synthétiques comme des résultats réels."
)

with st.form("research_data_form"):

    st.subheader("1. Identification et conditions")

    batch_id = st.text_input("Numéro de lot")
    product_name = st.text_input(
        "Produit",
        value="Lait pasteurisé"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        temperature = st.number_input(
            "Température (°C)",
            min_value=-20.0,
            max_value=50.0,
            value=4.0,
            step=0.1
        )

    with c2:
        storage_days = st.number_input(
            "Durée de stockage (jours)",
            min_value=0,
            max_value=365,
            value=2
        )

    with c3:
        ph = st.number_input(
            "pH",
            min_value=0.0,
            max_value=14.0,
            value=6.6,
            step=0.1
        )

    cold_chain = st.selectbox(
        "Rupture de la chaîne du froid",
        ["Inconnue", "Non", "Oui"]
    )

    hygiene = st.selectbox(
        "Hygiène maîtrisée",
        ["Inconnue", "Oui", "Non"]
    )

    pasteurized = st.selectbox(
        "Produit pasteurisé",
        ["Inconnue", "Oui", "Non"]
    )

    st.subheader("2. Résultats microbiologiques")

    st.caption(
        "Indiquez les valeurs mesurées par le laboratoire. "
        "Laissez vide si le test n'a pas été réalisé."
    )

    total_count = st.text_input(
        "Flore totale (UFC/mL ou unité du rapport)"
    )

    enterobacteriaceae = st.text_input(
        "Enterobacteriaceae (unité du rapport)"
    )

    coliforms = st.text_input(
        "Coliformes (unité du rapport)"
    )

    staph = st.text_input(
        "Staphylococcus aureus (unité du rapport)"
    )

    salmonella = st.selectbox(
        "Résultat Salmonella",
        ["Non testé", "Non détectée", "Détectée"]
    )

    st.subheader("3. Évaluation documentée")

    sensory = st.selectbox(
        "Évaluation sensorielle",
        ["Non évaluée", "Conforme", "Non conforme"]
    )

    nonconformity = st.selectbox(
        "Non-conformité confirmée",
        ["Inconnue", "Non", "Oui"]
    )

    expert_label = st.selectbox(
        "Classification du responsable qualité",
        ["Non attribuée", "Faible", "Modéré", "Élevé"]
    )

    submitted = st.form_submit_button(
        "💾 Enregistrer les données",
        use_container_width=True
    )


if submitted:

    if not batch_id.strip() or not product_name.strip():
        st.error("Le numéro de lot et le produit sont obligatoires.")

    else:
        def optional_number(value, field_name):
            value = value.strip()
            if not value:
                return None
            try:
                number = float(value.replace(",", "."))
                if number < 0:
                    raise ValueError
                return number
            except ValueError:
                raise ValueError(
                    f"Valeur invalide pour : {field_name}"
                )

        try:
            row = {
                "batch_id": batch_id.strip(),
                "product_name": product_name.strip(),
                "temperature_celsius": temperature,
                "storage_days": storage_days,
                "ph": ph,
                "cold_chain_broken": {
                    "Inconnue": None,
                    "Non": False,
                    "Oui": True
                }[cold_chain],
                "hygiene_controlled": {
                    "Inconnue": None,
                    "Oui": True,
                    "Non": False
                }[hygiene],
                "pasteurized": {
                    "Inconnue": None,
                    "Oui": True,
                    "Non": False
                }[pasteurized],
                "total_viable_count": optional_number(
                    total_count, "Flore totale"
                ),
                "enterobacteriaceae_count": optional_number(
                    enterobacteriaceae, "Enterobacteriaceae"
                ),
                "coliform_count": optional_number(
                    coliforms, "Coliformes"
                ),
                "staphylococcus_aureus_count": optional_number(
                    staph, "Staphylococcus aureus"
                ),
                "salmonella_detected": {
                    "Non testé": None,
                    "Non détectée": False,
                    "Détectée": True
                }[salmonella],
                "sensory_status": {
                    "Non évaluée": None,
                    "Conforme": "Conforme",
                    "Non conforme": "Non conforme"
                }[sensory],
                "nonconformity_detected": {
                    "Inconnue": None,
                    "Non": False,
                    "Oui": True
                }[nonconformity],
                "expert_risk_label": {
                    "Non attribuée": None,
                    "Faible": "Faible",
                    "Modéré": "Modéré",
                    "Élevé": "Élevé"
                }[expert_label],
            }

            existing = load_dataset()

            # Prevent accidental duplicate batch records.
            if (
                not existing.empty
                and existing["batch_id"].astype(str).eq(
                    batch_id.strip()
                ).any()
            ):
                st.error(
                    "Ce numéro de lot existe déjà dans le dataset. "
                    "Utilisez un identifiant unique pour chaque "
                    "nouvel enregistrement."
                )
            else:
                updated = pd.concat(
                    [existing, pd.DataFrame([row])],
                    ignore_index=True
                )

                updated.to_csv(
                    DATA_FILE,
                    index=False,
                    encoding="utf-8-sig"
                )

                st.success(
                    "Enregistrement ajouté au dataset de recherche."
                )

        except ValueError as error:
            st.error(str(error))


st.divider()
st.subheader("📊 Dataset de recherche")

dataset = load_dataset()

st.write(f"Nombre d'enregistrements : {len(dataset)}")

st.dataframe(
    dataset,
    use_container_width=True,
    hide_index=True
)

st.download_button(
    "⬇️ Télécharger le dataset CSV",
    data=dataset.to_csv(index=False).encode("utf-8-sig"),
    file_name="foodnexa_research_dataset.csv",
    mime="text/csv",
    use_container_width=True
)

st.warning(
    "Les données de ce prototype ne constituent pas une "
    "validation scientifique ou réglementaire. Les critères "
    "microbiologiques applicables doivent être définis selon "
    "le produit, la méthode d'analyse et la réglementation "
    "pertinente. Les résultats de laboratoire et les décisions "
    "de sécurité doivent être vérifiés par des professionnels."
)
