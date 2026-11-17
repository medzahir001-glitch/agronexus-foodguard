"""FOODNEXA Product Intelligence Library — V21.

Product profiles and configurable test plans. Regulatory limits are never
invented: a criterion can only be enabled for interpretation after the user
records its source and clause. Supabase is the durable backend; a local JSON
backup is used as a fallback when the new table is not yet available.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

TABLE_NAME = "foodnexa_product_profiles"
LOCAL_FILE = Path("foodnexa_product_library.json")

CATEGORIES = [
    "Produits laitiers",
    "Produits végétaux",
    "Céréales et farines",
    "Viandes et volailles",
    "Poissons et produits de la mer",
    "Boissons",
    "Huiles et matières grasses",
    "Autres produits alimentaires",
]

INTENDED_USES = [
    "Prêt à consommer",
    "À cuire / à transformer avant consommation",
    "Ingrédient destiné à une transformation",
    "Boisson",
    "Usage à préciser",
]


def _template(test_id: str, category: str, domain: str, name: str,
              unit: str, condition: str, method_hint: str,
              scope: str = "Spécifique au produit") -> dict[str, Any]:
    return {
        "test_id": test_id,
        "category": category,
        "domain": domain,
        "test_name": name,
        "unit": unit,
        "method": "À préciser — méthode validée adaptée au produit",
        "method_hint": method_hint,
        "applicability": condition,
        "scope": scope,
        "frequency": "À définir dans le plan HACCP / plan de contrôle",
        "limit_criterion": "",
        "reference_title": "",
        "reference_clause": "",
        "source_url": "",
        "notes": "",
        "decision_enabled": False,
        "status": "Proposé — à confirmer",
    }


# The entries below are screening suggestions, not claims that every test is
# legally mandatory. Applicability depends on product, process, intended use,
# market, sampling plan and the current applicable requirements.
TEST_TEMPLATES: list[dict[str, Any]] = [
    # Cross-category operational controls (not a universal laboratory panel)
    _template("cross_traceability", "Transversal", "Traçabilité", "Vérification de la traçabilité et de l'étiquetage", "Checklist", "Tous les produits; adapter aux obligations et au conditionnement", "Vérification documentaire: lot, fournisseur, dates, étiquette et enregistrements", "Contrôle transversal"),
    _template("cross_storage_temp", "Transversal", "Procédé / stockage", "Température à réception et au stockage", "°C", "Produits pour lesquels la température est un paramètre de conservation", "Mesure avec instrument étalonné; préciser le point et le moment de mesure", "Contrôle transversal conditionnel"),
    _template("cross_pack_integrity", "Transversal", "Emballage", "Intégrité de l'emballage / fermeture", "Checklist", "Produits conditionnés; adapter au type d'emballage", "Inspection visuelle et/ou essai d'intégrité adapté au conditionnement", "Contrôle transversal conditionnel"),
    _template("cross_sensory", "Transversal", "Sensoriel", "Évaluation sensorielle", "Grille / score", "Tous produits selon spécification; définir les attributs pertinents", "Grille sensorielle, conditions d'évaluation et panel documentés", "Contrôle transversal conditionnel"),

    # Dairy
    _template("dairy_ph", "Produits laitiers", "Physico-chimique", "pH", "pH", "Lait, produits fermentés, fromages et autres produits lorsque pertinent", "pH-mètre étalonné; température de mesure enregistrée"),
    _template("dairy_acidity", "Produits laitiers", "Physico-chimique", "Acidité titrable", "Unité selon méthode", "Lait et produits laitiers selon spécification", "Titrage selon méthode de laboratoire validée"),
    _template("dairy_fat", "Produits laitiers", "Physico-chimique", "Matières grasses", "% ou g/100 g", "Selon type de produit et déclaration nutritionnelle", "Méthode gravimétrique / instrumentale validée"),
    _template("dairy_protein", "Produits laitiers", "Physico-chimique", "Protéines", "% ou g/100 g", "Selon type de produit et spécification", "Méthode validée (ex. Kjeldahl / Dumas selon laboratoire)"),
    _template("dairy_tvc", "Produits laitiers", "Microbiologique", "Flore aérobie mésophile (TVC)", "UFC/g ou UFC/mL", "Selon catégorie de produit, traitement et durée de vie", "Dénombrement selon méthode reconnue et matrice adaptée"),
    _template("dairy_enterobacteria", "Produits laitiers", "Microbiologique", "Enterobacteriaceae", "UFC/g ou UFC/mL", "Selon produit et étape de contrôle", "Dénombrement selon méthode reconnue"),
    _template("dairy_ecoli", "Produits laitiers", "Microbiologique", "Escherichia coli", "UFC/g ou UFC/mL", "Selon produit, hygiène du procédé et usage prévu", "Dénombrement / détection selon méthode validée"),
    _template("dairy_staph", "Produits laitiers", "Microbiologique", "Staphylococcus aureus", "UFC/g ou UFC/mL", "Produits laitiers concernés par le risque et le procédé", "Dénombrement selon méthode validée"),
    _template("dairy_salmonella", "Produits laitiers", "Microbiologique", "Salmonella spp.", "Détection / présence-absence", "Selon type de produit et exigences applicables", "Détection selon méthode validée; préciser masse/volume analysé"),
    _template("dairy_listeria", "Produits laitiers", "Microbiologique", "Listeria monocytogenes", "Détection / UFC/g", "Notamment produits prêts à consommer selon risque et catégorie", "Détection ou dénombrement selon plan d'échantillonnage applicable"),
    _template("dairy_yeast_mould", "Produits laitiers", "Microbiologique", "Levures et moisissures", "UFC/g ou UFC/mL", "Produits fermentés, fromages et produits concernés", "Dénombrement selon méthode validée"),
    _template("dairy_afm1", "Produits laitiers", "Contaminants", "Aflatoxine M1", "µg/kg ou unité de méthode", "Lait et produits dérivés selon matière première et exigences du marché", "Méthode analytique validée (ex. LC-MS/MS ou immuno-essai confirmé)"),
    _template("dairy_pasteurization", "Produits laitiers", "Procédé", "Enregistrement temps / température de pasteurisation", "°C et s/min", "Produits déclarés pasteurisés; vérifier le procédé validé", "Enregistrement instrumenté et validation du barème thermique"),

    # Plant foods
    _template("veg_pesticides", "Produits végétaux", "Contaminants", "Résidus de pesticides ciblés", "mg/kg ou µg/kg", "Selon culture, origine, substance active et marché de destination", "Plan multi-résidus / méthode ciblée validée; préciser analytes"),
    _template("veg_nitrate", "Produits végétaux", "Contaminants", "Nitrates", "mg/kg", "Certaines catégories végétales (ex. légumes concernés) selon marché", "Méthode analytique validée; identifier la matrice"),
    _template("veg_tvc", "Produits végétaux", "Microbiologique", "Flore aérobie mésophile (TVC)", "UFC/g", "Selon produit frais, transformé et plan d'hygiène", "Dénombrement selon méthode validée"),
    _template("veg_ecoli", "Produits végétaux", "Microbiologique", "Escherichia coli", "UFC/g", "Particulièrement produits prêts à consommer et produits lavés/découpés", "Dénombrement / détection selon méthode validée"),
    _template("veg_salmonella", "Produits végétaux", "Microbiologique", "Salmonella spp.", "Détection / présence-absence", "Selon produit, origine, usage cru et exigences applicables", "Détection selon méthode validée; préciser masse analysée"),
    _template("veg_listeria", "Produits végétaux", "Microbiologique", "Listeria monocytogenes", "Détection / UFC/g", "Produits végétaux prêts à consommer selon risque", "Détection ou dénombrement selon méthode validée"),
    _template("veg_brix", "Produits végétaux", "Physico-chimique", "Extrait soluble / Brix", "°Bx", "Jus, purées et produits où le Brix est un critère de formulation", "Réfractomètre étalonné; température/correction documentée"),
    _template("veg_ph", "Produits végétaux", "Physico-chimique", "pH", "pH", "Produits végétaux transformés, acidifiés ou fermentés", "pH-mètre étalonné"),
    _template("veg_wash", "Produits végétaux", "Procédé", "Contrôle de l'eau / solution de lavage", "Selon paramètre", "Si une étape de lavage/désinfection est utilisée", "Mesure du paramètre de maîtrise défini (ex. concentration, pH, ORP)"),

    # Cereals and flours
    _template("cereal_moisture", "Céréales et farines", "Physico-chimique", "Humidité", "%", "Grains, farines et produits céréaliers selon spécification", "Méthode gravimétrique ou instrumentale validée"),
    _template("cereal_aw", "Céréales et farines", "Physico-chimique", "Activité de l'eau (aw)", "aw", "Produits céréaliers transformés où la stabilité dépend de l'aw", "Appareil aw étalonné; équilibre et température documentés"),
    _template("cereal_ash", "Céréales et farines", "Physico-chimique", "Cendres", "%", "Farines et produits où la qualité/minéralisation est spécifiée", "Méthode gravimétrique validée"),
    _template("cereal_protein", "Céréales et farines", "Physico-chimique", "Protéines", "% ou g/100 g", "Selon céréale et spécification; notamment qualité boulangère", "Méthode validée (Kjeldahl / Dumas selon laboratoire)"),
    _template("cereal_gluten", "Céréales et farines", "Physico-chimique", "Gluten (humide/sec)", "%", "Farines de blé et produits pour lesquels le gluten est pertinent", "Méthode dédiée validée"),
    _template("cereal_mycotoxin", "Céréales et farines", "Contaminants", "Mycotoxines ciblées (DON, aflatoxines, OTA, ZEA)", "µg/kg", "Analytes à sélectionner selon céréale, origine, stockage et marché", "LC-MS/MS ou méthode de dépistage confirmée; préciser chaque analyte"),
    _template("cereal_metals", "Céréales et farines", "Contaminants", "Métaux ciblés (Pb, Cd, As)", "mg/kg ou µg/kg", "Selon céréale, origine, risque et exigences applicables", "ICP-MS / méthode accréditée; préciser les éléments"),
    _template("cereal_pests", "Céréales et farines", "Sensoriel / stockage", "Inspection des infestations et corps étrangers", "Checklist", "Grains, farines et produits stockés", "Inspection représentative, tamisage ou méthode adaptée"),

    # Meat and poultry
    _template("meat_ph", "Viandes et volailles", "Physico-chimique", "pH", "pH", "Selon espèce, muscle, délai post-abattage et spécification", "pH-mètre avec sonde adaptée; temps/température documentés"),
    _template("meat_tvc", "Viandes et volailles", "Microbiologique", "Flore aérobie mésophile (TVC)", "UFC/g", "Selon type de viande, découpe, préparation et durée de vie", "Dénombrement selon méthode validée"),
    _template("meat_salmonella", "Viandes et volailles", "Microbiologique", "Salmonella spp.", "Détection / présence-absence", "Particulièrement volailles et catégories définies par le plan de contrôle", "Détection selon méthode validée et plan d'échantillonnage"),
    _template("meat_campy", "Viandes et volailles", "Microbiologique", "Campylobacter spp.", "UFC/g ou détection", "Volaille et produits concernés selon réglementation/plan", "Dénombrement ou détection selon méthode validée"),
    _template("meat_ecoli", "Viandes et volailles", "Microbiologique", "E. coli / STEC ciblés", "UFC/g ou détection", "Selon espèce, viande hachée, produit cru ou prêt à consommer", "Méthode de dénombrement/détection ciblée"),
    _template("meat_listeria", "Viandes et volailles", "Microbiologique", "Listeria monocytogenes", "Détection / UFC/g", "Viandes transformées prêtes à consommer selon catégorie et risque", "Détection ou dénombrement selon méthode validée"),
    _template("meat_residues", "Viandes et volailles", "Contaminants", "Résidus vétérinaires ciblés", "µg/kg", "Selon espèce, substance, origine et programme de surveillance", "Méthode multi-résidus / ciblée validée; préciser analytes"),
    _template("meat_nitrite", "Viandes et volailles", "Contaminants / formulation", "Nitrites / nitrates ajoutés ou résiduels", "mg/kg", "Produits de charcuterie lorsque utilisés/pertinents", "Méthode analytique validée; examiner formulation et réglementation"),

    # Seafood
    _template("seafood_temp", "Poissons et produits de la mer", "Procédé / stockage", "Température du produit et de conservation", "°C", "Produits frais, réfrigérés, congelés ou décongelés selon catégorie", "Mesure au point pertinent avec instrument étalonné"),
    _template("seafood_histamine", "Poissons et produits de la mer", "Contaminants", "Histamine", "mg/kg", "Espèces et produits susceptibles selon espèce et chaîne temps-température", "Méthode chromatographique ou méthode validée équivalente"),
    _template("seafood_vibrio", "Poissons et produits de la mer", "Microbiologique", "Vibrio spp. ciblés", "UFC/g ou détection", "Certains coquillages et produits de la mer selon origine/usage", "Espèce ciblée et méthode validée à préciser"),
    _template("seafood_salmonella", "Poissons et produits de la mer", "Microbiologique", "Salmonella spp.", "Détection / présence-absence", "Selon produit, transformation et exigences applicables", "Détection selon méthode validée"),
    _template("seafood_listeria", "Poissons et produits de la mer", "Microbiologique", "Listeria monocytogenes", "Détection / UFC/g", "Poissons fumés et autres produits prêts à consommer selon risque", "Détection ou dénombrement selon méthode validée"),
    _template("seafood_biotoxins", "Poissons et produits de la mer", "Contaminants", "Biotoxines marines ciblées", "Selon toxine / méthode", "Bivalves et produits concernés selon zone de récolte et surveillance officielle", "Analyte et méthode spécifique à préciser"),
    _template("seafood_metals", "Poissons et produits de la mer", "Contaminants", "Métaux (Hg, Cd, Pb) ciblés", "mg/kg ou µg/kg", "Selon espèce, taille, zone de pêche et marché", "ICP-MS / méthode accréditée; préciser chaque élément"),

    # Beverages
    _template("bev_ph", "Boissons", "Physico-chimique", "pH", "pH", "Boissons où le pH intervient dans la formulation/stabilité", "pH-mètre étalonné"),
    _template("bev_brix", "Boissons", "Physico-chimique", "Brix", "°Bx", "Jus, nectars, sirops et boissons sucrées selon spécification", "Réfractomètre étalonné"),
    _template("bev_acidity", "Boissons", "Physico-chimique", "Acidité titrable", "Unité selon méthode", "Boissons acidifiées, jus et boissons fermentées selon cahier des charges", "Titrage selon méthode validée"),
    _template("bev_tvc", "Boissons", "Microbiologique", "Flore aérobie mésophile (TVC)", "UFC/mL", "Selon type de boisson et procédé", "Dénombrement selon méthode validée"),
    _template("bev_yeast", "Boissons", "Microbiologique", "Levures et moisissures", "UFC/mL", "Jus et boissons non stériles/fermentées selon risque", "Dénombrement selon méthode validée"),
    _template("bev_preservatives", "Boissons", "Contaminants / formulation", "Conservateurs ciblés", "mg/L", "Seulement si utilisés ou attendus dans la formulation", "Méthode validée; préciser substance"),
    _template("bev_process", "Boissons", "Procédé", "Barème thermique / remplissage", "°C et s/min", "Boissons pasteurisées, stérilisées ou remplies à chaud", "Enregistrement temps-température et vérification du procédé"),

    # Oils and fats
    _template("oil_acid", "Huiles et matières grasses", "Physico-chimique", "Indice d'acide / acidité libre", "mg KOH/g ou % acide oléique", "Huiles et matières grasses selon type et spécification", "Titrage selon méthode validée"),
    _template("oil_peroxide", "Huiles et matières grasses", "Physico-chimique", "Indice de peroxyde", "meq O2/kg", "Huiles et matières grasses selon type et spécification", "Méthode iodométrique / instrumentale validée"),
    _template("oil_anisidine", "Huiles et matières grasses", "Physico-chimique", "Indice d'anisidine", "Sans unité", "Selon huile, étude d'oxydation et spécification", "Méthode spectrophotométrique validée"),
    _template("oil_profile", "Huiles et matières grasses", "Authenticité / composition", "Profil en acides gras", "% des acides gras", "Authenticité, identité et conformité de la composition", "GC-FID / méthode validée"),
    _template("oil_pahs", "Huiles et matières grasses", "Contaminants", "Hydrocarbures aromatiques polycycliques ciblés", "µg/kg", "Selon huile, matière première et procédé de séchage/raffinage", "GC-MS / méthode accréditée; préciser les composés"),
    _template("oil_3mcpd", "Huiles et matières grasses", "Contaminants", "3-MCPD et esters de glycidol ciblés", "µg/kg", "Selon huile raffinée et catégorie de produit", "Méthode LC-MS/MS ou méthode validée adaptée"),
]

TEMPLATE_BY_ID = {item["test_id"]: item for item in TEST_TEMPLATES}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_json_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            pass
    return []


def _normalize_profile(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["id"] = str(result.get("id") or uuid.uuid4())
    result["tests"] = _safe_json_list(result.get("tests"))
    result.setdefault("product_description", "")
    result.setdefault("intended_use", "Usage à préciser")
    result.setdefault("processing_profile", "")
    result.setdefault("storage_conditions", "")
    result.setdefault("shelf_life", "")
    result.setdefault("packaging", "")
    result.setdefault("target_market", "Maroc — exigences à confirmer")
    result.setdefault("created_at", _now())
    result.setdefault("updated_at", _now())
    return result


def _local_read() -> list[dict[str, Any]]:
    if not LOCAL_FILE.exists():
        return []
    try:
        payload = json.loads(LOCAL_FILE.read_text(encoding="utf-8"))
        rows = payload.get("profiles", []) if isinstance(payload, dict) else payload
        if isinstance(rows, list):
            return [_normalize_profile(row) for row in rows if isinstance(row, dict)]
    except Exception:
        return []
    return []


def _local_write(profiles: list[dict[str, Any]]) -> None:
    LOCAL_FILE.write_text(
        json.dumps({"version": 1, "profiles": profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _supabase_client():
    """Use existing server-side Streamlit secrets; never expose the key."""
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(str(url), str(key))
    except Exception:
        return None


def load_profiles() -> tuple[list[dict[str, Any]], str, str | None]:
    client = _supabase_client()
    if client is not None:
        try:
            response = (
                client.table(TABLE_NAME)
                .select("*")
                .order("product_name")
                .execute()
            )
            rows = response.data or []
            return [_normalize_profile(row) for row in rows], "Supabase", None
        except Exception as exc:
            local = _local_read()
            return local, "JSON local (secours)", f"{type(exc).__name__}: table ou accès Supabase à vérifier"
    local = _local_read()
    return local, "JSON local", "Connexion Supabase non configurée pour cette bibliothèque"


def save_profile(profile: dict[str, Any]) -> tuple[bool, str, str | None]:
    clean = _normalize_profile(profile)
    clean["updated_at"] = _now()
    client = _supabase_client()
    if client is not None:
        try:
            client.table(TABLE_NAME).upsert(clean, on_conflict="id").execute()
            # Keep an exportable local mirror, without making it the source of truth.
            current = _local_read()
            merged = [p for p in current if str(p.get("id")) != clean["id"]]
            merged.append(clean)
            try:
                _local_write(merged)
            except Exception:
                pass
            return True, "Supabase", None
        except Exception as exc:
            # Local fallback so a user can keep working before applying the SQL migration.
            current = _local_read()
            merged = [p for p in current if str(p.get("id")) != clean["id"]]
            merged.append(clean)
            try:
                _local_write(merged)
                return True, "JSON local (secours)", f"{type(exc).__name__}: migration SQL requise ou accès Supabase à vérifier"
            except Exception as local_exc:
                return False, "Aucun stockage", f"{type(local_exc).__name__}"
    current = _local_read()
    merged = [p for p in current if str(p.get("id")) != clean["id"]]
    merged.append(clean)
    try:
        _local_write(merged)
        return True, "JSON local", "Configurer Supabase et exécuter la migration pour une conservation durable."
    except Exception as exc:
        return False, "Aucun stockage", f"{type(exc).__name__}"


def bulk_import_profiles(rows: list[dict[str, Any]]) -> tuple[int, str, str | None]:
    normalized = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("product_name") or not row.get("product_category"):
            continue
        normalized.append(_normalize_profile(row))
    if not normalized:
        return 0, "Aucun import", "Aucun profil valide dans le fichier."

    client = _supabase_client()
    if client is not None:
        try:
            client.table(TABLE_NAME).upsert(normalized, on_conflict="id").execute()
            return len(normalized), "Supabase", None
        except Exception as exc:
            error = f"{type(exc).__name__}: migration SQL requise ou accès Supabase à vérifier"
    else:
        error = "Supabase non configuré; import local uniquement."

    current = {p["id"]: p for p in _local_read()}
    for row in normalized:
        current[row["id"]] = row
    try:
        _local_write(list(current.values()))
        return len(normalized), "JSON local", error
    except Exception as exc:
        return 0, "Aucun stockage", f"{type(exc).__name__}"


def _test_label(test: dict[str, Any]) -> str:
    return f"{test.get('domain', 'Autre')} — {test.get('test_name', 'Test')} [{test.get('unit', 'unité à définir')}]"


def _merge_selected_tests(selected_ids: list[str], old_tests: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    old_by_id = {str(test.get("test_id")): test for test in old_tests}
    merged = []
    for test_id in selected_ids:
        if test_id in old_by_id:
            merged.append(dict(old_by_id[test_id]))
        elif test_id in TEMPLATE_BY_ID:
            item = dict(TEMPLATE_BY_ID[test_id])
            # Applicability remains explicitly unconfirmed until reviewed by the user.
            item["status"] = "Proposé — à confirmer"
            merged.append(item)
    return merged


def _profile_frame(profiles: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for profile in profiles:
        tests = profile.get("tests", [])
        rows.append({
            "Produit": profile.get("product_name", "—"),
            "Catégorie": profile.get("product_category", "—"),
            "Usage prévu": profile.get("intended_use", "—"),
            "Tests associés": len(tests),
            "Tests avec source": sum(1 for t in tests if t.get("reference_title") and t.get("reference_clause")),
            "Mis à jour": str(profile.get("updated_at", ""))[:10] or "—",
        })
    return pd.DataFrame(rows)


def render_product_library() -> None:
    """Render the interactive product catalogue and product-specific test plans."""
    profiles, storage_mode, storage_error = load_profiles()

    st.title("📚 Product Intelligence Library")
    st.caption("Catalogue structuré des produits, paramètres de contrôle et références applicables.")
    st.info(
        "Les tests affichés sont des suggestions de sélection, pas une liste universelle ni une déclaration d'obligation légale. "
        "Aucune limite réglementaire n'est préremplie. Toute interprétation conforme/non conforme exige une source, une clause, "
        "une matrice et une méthode adaptées au produit et au marché."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Profils produits", len(profiles))
    m2.metric("Catégories", len({p.get('product_category') for p in profiles}))
    m3.metric("Tests associés", sum(len(p.get("tests", [])) for p in profiles))
    m4.metric("Tests avec source", sum(1 for p in profiles for t in p.get("tests", []) if t.get("reference_title") and t.get("reference_clause")))

    st.caption(f"Stockage actuel : **{storage_mode}**")
    if storage_error:
        st.warning(
            f"{storage_error}. Les modifications sont conservées dans un JSON local de secours quand cela est possible. "
            "Pour un stockage durable sur Streamlit Cloud, exécutez la migration SQL V21 puis vérifiez SUPABASE_URL et SUPABASE_KEY dans Secrets."
        )

    tab_catalog, tab_profile, tab_plan, tab_transfer = st.tabs([
        "Catalogue", "Créer / modifier", "Plan de contrôle", "Import / export"
    ])

    with tab_catalog:
        st.subheader("Catalogue des profils produits")
        category_filter = st.selectbox("Filtrer par catégorie", ["Toutes les catégories"] + CATEGORIES, key="pil_filter_category")
        visible_profiles = [p for p in profiles if category_filter == "Toutes les catégories" or p.get("product_category") == category_filter]
        if visible_profiles:
            st.dataframe(_profile_frame(visible_profiles), use_container_width=True, hide_index=True)
            selected_profile_id = st.selectbox(
                "Consulter un produit",
                options=[p["id"] for p in visible_profiles],
                format_func=lambda pid: next((p.get("product_name", pid) for p in visible_profiles if p["id"] == pid), pid),
                key="pil_catalog_selected",
            )
            selected_profile = next(p for p in visible_profiles if p["id"] == selected_profile_id)
            st.markdown(f"#### {selected_profile.get('product_name', 'Produit')}")
            detail1, detail2, detail3 = st.columns(3)
            detail1.write(f"**Catégorie :** {selected_profile.get('product_category', '—')}")
            detail2.write(f"**Usage :** {selected_profile.get('intended_use', '—')}")
            detail3.write(f"**Marché :** {selected_profile.get('target_market', '—')}")
            st.write(f"**Description :** {selected_profile.get('product_description') or '—'}")
            st.write(f"**Procédé :** {selected_profile.get('processing_profile') or '—'}")
            st.write(f"**Stockage :** {selected_profile.get('storage_conditions') or '—'}")
            st.write(f"**Durée de vie :** {selected_profile.get('shelf_life') or '—'}")
            if selected_profile.get("tests"):
                test_rows = [{
                    "Domaine": t.get("domain", "—"),
                    "Test": t.get("test_name", "—"),
                    "Unité": t.get("unit", "—"),
                    "Applicabilité": t.get("applicability", "À confirmer"),
                    "Critère": t.get("limit_criterion") or "Non défini",
                    "Référence": t.get("reference_title") or "Non renseignée",
                    "Statut": t.get("status", "Proposé — à confirmer"),
                } for t in selected_profile["tests"]]
                st.dataframe(pd.DataFrame(test_rows), use_container_width=True, hide_index=True)
            else:
                st.warning("Aucun test n'est encore associé à ce profil. Utilisez Créer / modifier ou Plan de contrôle.")
        else:
            st.info("Le catalogue des profils est vide. Créez votre premier profil dans l'onglet Créer / modifier.")

        st.markdown("#### Référentiel des tests proposés")
        template_category = st.selectbox("Catégorie de test", ["Transversal"] + CATEGORIES, key="pil_template_category")
        templates = [t for t in TEST_TEMPLATES if t["category"] == template_category]
        if templates:
            template_rows = [{
                "Domaine": t["domain"],
                "Test proposé": t["test_name"],
                "Unité indicative": t["unit"],
                "Quand l'envisager": t["applicability"],
                "Portée": t["scope"],
            } for t in templates]
            st.dataframe(pd.DataFrame(template_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("Aucun test de catégorie spécifique n'est défini dans cette première version.")

        st.markdown("#### Références officielles à vérifier — marché marocain")
        st.markdown(
            "- [ONSSA — Critères microbiologiques](https://www.onssa.gov.ma/reglementation-transversale-criteres-microbiologiques/) : "
            "l'ONSSA signale la modification de l'arrêté 293-19 par l'arrêté 2234-25, publié au Bulletin Officiel n°7466 du 18/12/2025. "
            "La matrice, le stade d'application et le plan d'échantillonnage doivent être vérifiés avant toute saisie de limite.\n\n"
            "- [ONSSA — Conformité des produits](https://www.onssa.gov.ma/reglementation/reglementation-transversale/conformite-des-produits/) : "
            "point d'accès aux textes sur les résidus phytosanitaires, contaminants, résidus pharmaceutiques, additifs et étiquetage.\n\n"
            "- [ISO — Microbiologie de la chaîne alimentaire](https://www.iso.org/sectors/food-agriculture/microbiology-of-food) : "
            "répertoire des méthodes et références microbiologiques; choisir la méthode correspondant à la matrice et au paramètre."
        )
        st.caption("Ces liens sont des points d'accès documentaires, pas une validation automatique de la conformité d'un produit.")

    with tab_profile:
        st.subheader("Créer ou modifier un profil produit")
        mode = st.radio("Action", ["Créer un profil", "Modifier un profil"], horizontal=True, key="pil_profile_mode")
        current = None
        if mode == "Modifier un profil":
            if not profiles:
                st.warning("Aucun profil à modifier. Créez d'abord un produit.")
            else:
                current_id = st.selectbox(
                    "Profil à modifier",
                    options=[p["id"] for p in profiles],
                    format_func=lambda pid: next((p.get("product_name", pid) for p in profiles if p["id"] == pid), pid),
                    key="pil_edit_profile_id",
                )
                current = next(p for p in profiles if p["id"] == current_id)

        default_category = current.get("product_category") if current else CATEGORIES[0]
        category_index = CATEGORIES.index(default_category) if default_category in CATEGORIES else 0
        with st.form("pil_product_profile_form", clear_on_submit=False):
            product_name = st.text_input("Nom du produit *", value=current.get("product_name", "") if current else "Lait pasteurisé", placeholder="Ex. Lait pasteurisé entier")
            product_category = st.selectbox("Catégorie *", CATEGORIES, index=category_index)
            product_description = st.text_area("Description / caractéristiques", value=current.get("product_description", "") if current else "", placeholder="Composition, variété, teneur en matière grasse, format...")
            intended_use = st.selectbox("Usage prévu", INTENDED_USES, index=INTENDED_USES.index(current.get("intended_use")) if current and current.get("intended_use") in INTENDED_USES else len(INTENDED_USES)-1)
            processing_profile = st.text_input("Procédé principal", value=current.get("processing_profile", "") if current else "", placeholder="Ex. Pasteurisation, fermentation, découpe, séchage...")
            storage_conditions = st.text_input("Conditions de stockage", value=current.get("storage_conditions", "") if current else "", placeholder="Décrire la condition attendue; ne pas inventer de seuil")
            shelf_life = st.text_input("Durée de vie / DLC", value=current.get("shelf_life", "") if current else "", placeholder="Ex. durée définie par validation du fabricant")
            packaging = st.text_input("Type d'emballage", value=current.get("packaging", "") if current else "", placeholder="Ex. bouteille PET, sachet, boîte, sous vide...")
            target_market = st.text_input("Marché / pays de destination", value=current.get("target_market", "Maroc — exigences à confirmer") if current else "Maroc — exigences à confirmer")

            old_tests = current.get("tests", []) if current else []
            templates_for_category = [t for t in TEST_TEMPLATES if t["category"] in {"Transversal", product_category}]
            old_by_id = {str(t.get("test_id")): t for t in old_tests if t.get("test_id")}
            options_map = {t["test_id"]: t for t in templates_for_category}
            for old in old_tests:
                if old.get("test_id") and old["test_id"] not in options_map:
                    options_map[old["test_id"]] = old
            option_ids = list(options_map)
            default_ids = [tid for tid in old_by_id if tid in option_ids]
            selected_test_ids = st.multiselect(
                "Tests proposés à associer au produit",
                options=option_ids,
                default=default_ids,
                format_func=lambda tid: _test_label(options_map[tid]),
                help="Sélectionnez uniquement les tests pertinents pour la matrice, le procédé et l'usage prévu. Les éléments proposés restent à confirmer.",
            )
            st.caption("Aucun seuil numérique n'est fourni par défaut. Les tests sélectionnés seront initialisés avec un statut 'à confirmer'.")
            submitted = st.form_submit_button("💾 Enregistrer le profil produit", type="primary", use_container_width=True)

        if submitted:
            if not product_name.strip():
                st.error("Le nom du produit est obligatoire.")
            else:
                duplicate = next((p for p in profiles
                                  if p.get("product_category") == product_category
                                  and str(p.get("product_name", "")).strip().casefold() == product_name.strip().casefold()
                                  and (current is None or str(p.get("id")) != str(current.get("id")))), None)
                if duplicate:
                    st.error("Un profil portant déjà ce nom existe dans cette catégorie. Utilisez Modifier un profil.")
                    st.stop()
                now = _now()
                chosen_tests = _merge_selected_tests(selected_test_ids, old_tests, product_category)
                profile = {
                    "id": current["id"] if current else str(uuid.uuid4()),
                    "product_name": product_name.strip(),
                    "product_category": product_category,
                    "product_description": product_description.strip(),
                    "intended_use": intended_use,
                    "processing_profile": processing_profile.strip(),
                    "storage_conditions": storage_conditions.strip(),
                    "shelf_life": shelf_life.strip(),
                    "packaging": packaging.strip(),
                    "target_market": target_market.strip() or "À préciser",
                    "tests": chosen_tests,
                    "created_at": current.get("created_at", now) if current else now,
                    "updated_at": now,
                }
                ok, backend, error = save_profile(profile)
                if ok:
                    st.success(f"Profil enregistré dans {backend}.")
                    if error:
                        st.warning(error)
                    st.rerun()
                else:
                    st.error(f"Enregistrement impossible : {error}")

    with tab_plan:
        st.subheader("Plan de contrôle par produit")
        if not profiles:
            st.info("Créez un profil produit avant de configurer son plan de contrôle.")
        else:
            plan_product_id = st.selectbox(
                "Produit",
                options=[p["id"] for p in profiles],
                format_func=lambda pid: next((p.get("product_name", pid) for p in profiles if p["id"] == pid), pid),
                key="pil_plan_product_id",
            )
            plan_profile = next(p for p in profiles if p["id"] == plan_product_id)
            tests = list(plan_profile.get("tests", []))
            if tests:
                test_table = [{
                    "Domaine": t.get("domain", "—"),
                    "Test": t.get("test_name", "—"),
                    "Unité": t.get("unit", "—"),
                    "Critère": t.get("limit_criterion") or "Non défini",
                    "Source": t.get("reference_title") or "Non renseignée",
                    "Clause": t.get("reference_clause") or "—",
                    "Décision activée": "Oui" if t.get("decision_enabled") else "Non",
                } for t in tests]
                st.dataframe(pd.DataFrame(test_table), use_container_width=True, hide_index=True)

                test_index = st.selectbox(
                    "Test à configurer",
                    options=list(range(len(tests))),
                    format_func=lambda i: _test_label(tests[i]),
                    key="pil_edit_test_index",
                )
                selected_test = dict(tests[test_index])
                with st.form("pil_test_config_form"):
                    method = st.text_input("Méthode d'analyse", value=selected_test.get("method", ""))
                    unit = st.text_input("Unité", value=selected_test.get("unit", ""))
                    applicability = st.text_input("Applicabilité / condition", value=selected_test.get("applicability", ""))
                    frequency = st.text_input("Fréquence du contrôle", value=selected_test.get("frequency", ""))
                    limit_criterion = st.text_input("Limite / critère exact (laisser vide tant que non sourcé)", value=selected_test.get("limit_criterion", ""), placeholder="Ne pas saisir de seuil sans référence vérifiée")
                    reference_title = st.text_input("Titre de la norme / règlement / cahier des charges", value=selected_test.get("reference_title", ""))
                    reference_clause = st.text_input("Article / clause / annexe / tableau", value=selected_test.get("reference_clause", ""))
                    source_url = st.text_input("Lien de la source officielle (facultatif)", value=selected_test.get("source_url", ""))
                    notes = st.text_area("Notes / précisions de matrice", value=selected_test.get("notes", ""))
                    decision_enabled = st.checkbox("Autoriser une interprétation automatique selon ce critère", value=bool(selected_test.get("decision_enabled", False)))
                    save_test = st.form_submit_button("Enregistrer la configuration du test", type="primary", use_container_width=True)
                if save_test:
                    if decision_enabled and not (limit_criterion.strip() and reference_title.strip() and reference_clause.strip()):
                        st.error("Pour activer une interprétation automatique, renseignez le critère exact, la référence et sa clause.")
                    else:
                        selected_test.update({
                            "method": method.strip(), "unit": unit.strip(), "applicability": applicability.strip(),
                            "frequency": frequency.strip(), "limit_criterion": limit_criterion.strip(),
                            "reference_title": reference_title.strip(), "reference_clause": reference_clause.strip(),
                            "source_url": source_url.strip(), "notes": notes.strip(),
                            "decision_enabled": bool(decision_enabled),
                            "status": "Référencé — à valider" if reference_title.strip() and reference_clause.strip() else "Proposé — à confirmer",
                        })
                        tests[test_index] = selected_test
                        plan_profile["tests"] = tests
                        ok, backend, error = save_profile(plan_profile)
                        if ok:
                            st.success(f"Configuration sauvegardée dans {backend}.")
                            if error:
                                st.warning(error)
                            st.rerun()
                        else:
                            st.error(f"Enregistrement impossible : {error}")
            else:
                st.warning("Aucun test associé. Ajoutez des tests via Créer / modifier.")

            st.markdown("#### Ajouter un test personnalisé")
            with st.form("pil_custom_test_form"):
                custom_name = st.text_input("Nom du test")
                custom_domain = st.selectbox("Domaine", ["Physico-chimique", "Microbiologique", "Contaminants", "Procédé", "Sensoriel", "Emballage", "Traçabilité", "Authenticité / composition"])
                custom_unit = st.text_input("Unité")
                custom_method = st.text_input("Méthode (ou 'à préciser')")
                custom_condition = st.text_input("Condition d'applicabilité")
                add_custom = st.form_submit_button("Ajouter ce test au produit", use_container_width=True)
            if add_custom:
                if not custom_name.strip():
                    st.error("Le nom du test est obligatoire.")
                else:
                    custom_test = {
                        "test_id": "custom_" + uuid.uuid4().hex,
                        "category": plan_profile.get("product_category"),
                        "domain": custom_domain,
                        "test_name": custom_name.strip(),
                        "unit": custom_unit.strip() or "À préciser",
                        "method": custom_method.strip() or "À préciser",
                        "method_hint": "Méthode à documenter",
                        "applicability": custom_condition.strip() or "À confirmer",
                        "scope": "Test personnalisé",
                        "frequency": "À définir",
                        "limit_criterion": "",
                        "reference_title": "",
                        "reference_clause": "",
                        "source_url": "",
                        "notes": "",
                        "decision_enabled": False,
                        "status": "Personnalisé — à documenter",
                    }
                    plan_profile["tests"] = tests + [custom_test]
                    ok, backend, error = save_profile(plan_profile)
                    if ok:
                        st.success(f"Test ajouté et profil sauvegardé dans {backend}.")
                        if error:
                            st.warning(error)
                        st.rerun()
                    else:
                        st.error(f"Ajout impossible : {error}")

    with tab_transfer:
        st.subheader("Sauvegarde et transfert du catalogue")
        export_payload = json.dumps({"version": 1, "profiles": profiles}, ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ Télécharger la bibliothèque (JSON)",
            data=export_payload,
            file_name="foodnexa_product_library_backup.json",
            mime="application/json",
            use_container_width=True,
        )
        uploaded = st.file_uploader("Importer une sauvegarde JSON FOODNEXA", type=["json"], key="pil_import_json")
        if uploaded is not None:
            if st.button("Importer les profils", type="primary", key="pil_import_button"):
                try:
                    payload = json.loads(uploaded.getvalue().decode("utf-8"))
                    rows = payload.get("profiles", []) if isinstance(payload, dict) else payload
                    count, backend, error = bulk_import_profiles(rows if isinstance(rows, list) else [])
                    if count:
                        st.success(f"{count} profil(s) importé(s) dans {backend}.")
                        if error:
                            st.warning(error)
                        st.rerun()
                    else:
                        st.error(error or "Aucun profil n'a été importé.")
                except Exception as exc:
                    st.error(f"Fichier JSON invalide : {type(exc).__name__}")

    st.divider()
    st.caption(
        "FOODNEXA — Les propositions du catalogue servent à structurer le plan de contrôle. "
        "La sélection finale, les méthodes, les fréquences et les limites doivent être validées "
        "par les exigences applicables, le responsable qualité et/ou le laboratoire compétent."
    )
