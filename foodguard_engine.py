"""FOODNEXA explainable dairy risk-screening engine.

This is a rule-based research prototype, not a validated predictive model or
regulatory decision system. Missing inputs remain missing and never become
zero, negative, or compliant results.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


FACTOR_MAX_SCORES = {
    "temperature": 35,
    "storage_duration": 20,
    "ph": 25,
    "cold_chain": 30,
    "hygiene": 25,
    "pasteurization": 20,
}


def _is_bool_or_missing(value: Any) -> bool:
    return value is None or isinstance(value, bool)


def validate_inputs(temperature, storage_days, ph, cold_chain_broken,
                    hygiene_controlled, pasteurized):
    errors = []
    for name, value, low, high in (
        ("temperature", temperature, -20, 60),
        ("storage_days", storage_days, 0, 365),
        ("ph", ph, 0, 14),
    ):
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            errors.append(f"{name} doit être une valeur numérique ou non renseignée.")
            continue
        if not low <= number <= high:
            errors.append(f"{name} doit être compris entre {low} et {high}.")

    for name, value in (
        ("cold_chain_broken", cold_chain_broken),
        ("hygiene_controlled", hygiene_controlled),
        ("pasteurized", pasteurized),
    ):
        if not _is_bool_or_missing(value):
            errors.append(f"{name} doit être vrai, faux ou non renseigné.")
    return errors


def analyze_temperature(temperature):
    if temperature is None:
        return None, "Non renseigné", "Température non fournie."
    if temperature > 8:
        return 35, "Élevé", "Température de stockage élevée selon les règles expérimentales du prototype."
    if temperature > 4:
        return 15, "Modéré", "Température supérieure à la cible expérimentale du prototype."
    return 0, "Faible", "Aucun signal de température détecté par les règles du prototype."


def analyze_storage_duration(storage_days):
    if storage_days is None:
        return None, "Non renseigné", "Durée de stockage non fournie."
    if storage_days > 7:
        return 20, "Élevé", "Durée de stockage longue selon les règles expérimentales du prototype."
    if storage_days > 3:
        return 10, "Modéré", "Durée de stockage relativement longue selon les règles du prototype."
    return 0, "Faible", "Aucun signal de durée de stockage détecté par le prototype."


def analyze_ph(ph):
    if ph is None:
        return None, "Non renseigné", "pH non fourni."
    if ph < 5.8:
        return 25, "Élevé", "pH bas pouvant indiquer une modification du produit; analyse complémentaire requise."
    if ph < 6.2:
        return 10, "Modéré", "pH légèrement inférieur à la valeur attendue dans le prototype."
    return 0, "Faible", "Aucun signal de pH détecté par le prototype."


def analyze_cold_chain(value):
    if value is None:
        return None, "Non renseigné", "État de la chaîne du froid non confirmé."
    if value:
        return 30, "Élevé", "Interruption déclarée de la chaîne du froid."
    return 0, "Faible", "Aucune interruption de chaîne du froid déclarée."


def analyze_hygiene(value):
    if value is None:
        return None, "Non renseigné", "État de maîtrise de l'hygiène non confirmé."
    if not value:
        return 25, "Élevé", "Conditions d'hygiène déclarées non maîtrisées."
    return 0, "Faible", "Conditions d'hygiène déclarées maîtrisées."


def analyze_pasteurization(value):
    if value is None:
        return None, "Non renseigné", "Statut de pasteurisation non confirmé."
    if not value:
        return 20, "Élevé", "Pasteurisation déclarée absente."
    return 0, "Faible", "Produit déclaré pasteurisé; le traitement n'est pas vérifié par ce champ."


def classify_risk(score):
    if score >= 70:
        return "Élevé"
    if score >= 35:
        return "Modéré"
    return "Faible"


def calculate_confidence(factors):
    """Backward-compatible name: this is data completeness, NOT probability."""
    if not factors:
        return 0.0
    available = sum(1 for factor in factors.values() if factor.get("data_available"))
    return round(available / len(factors) * 100, 1)


def generate_recommendations(factors):
    recommendations = []
    mapping = {
        "temperature": "Vérifier les enregistrements de température et la chaîne du froid.",
        "storage_duration": "Vérifier la date de production, la date limite et la durée réelle de stockage.",
        "ph": "Réaliser une vérification complémentaire du pH et les analyses qualité adaptées.",
        "cold_chain": "Évaluer la durée de l'interruption et isoler le lot selon la procédure qualité applicable.",
        "hygiene": "Réévaluer le nettoyage, la désinfection et les pratiques d'hygiène.",
        "pasteurization": "Vérifier les paramètres de traitement thermique et les enregistrements disponibles.",
    }
    for name, factor in factors.items():
        if factor.get("data_available") and (factor.get("score") or 0) > 0:
            recommendations.append(mapping.get(name, "Vérifier le facteur signalé."))
    missing = [name for name, factor in factors.items() if not factor.get("data_available")]
    if missing:
        recommendations.append(
            "Compléter les facteurs non renseignés avant toute interprétation globale du lot."
        )
    if not recommendations:
        recommendations.append(
            "Conserver les enregistrements et poursuivre la surveillance selon le plan de contrôle applicable."
        )
    return recommendations


def assess_dairy_food_safety_risk(
    temperature=None,
    storage_days=None,
    ph=None,
    cold_chain_broken=None,
    hygiene_controlled=None,
    pasteurized=None,
    batch_id="BATCH-001",
    product_name="Produit laitier",
):
    """Assess only supplied factors; never interpret an unknown factor as safe."""
    errors = validate_inputs(
        temperature, storage_days, ph,
        cold_chain_broken, hygiene_controlled, pasteurized,
    )
    if errors:
        return {"status": "ERROR", "errors": errors}

    numeric = {
        "temperature": None if temperature is None else float(temperature),
        "storage_duration": None if storage_days is None else float(storage_days),
        "ph": None if ph is None else float(ph),
    }
    analyzers = {
        "temperature": lambda: analyze_temperature(numeric["temperature"]),
        "storage_duration": lambda: analyze_storage_duration(numeric["storage_duration"]),
        "ph": lambda: analyze_ph(numeric["ph"]),
        "cold_chain": lambda: analyze_cold_chain(cold_chain_broken),
        "hygiene": lambda: analyze_hygiene(hygiene_controlled),
        "pasteurization": lambda: analyze_pasteurization(pasteurized),
    }

    factors = {}
    for name, analyzer in analyzers.items():
        score, level, reason = analyzer()
        factors[name] = {
            "score": score,
            "level": level,
            "reason": reason,
            "data_available": score is not None,
            "maximum_score": FACTOR_MAX_SCORES[name],
        }

    available_count = sum(1 for item in factors.values() if item["data_available"])
    total_count = len(factors)
    completeness = calculate_confidence(factors)
    observed_score = min(sum(item["score"] or 0 for item in factors.values()), 100)
    complete = available_count == total_count
    risk_score = observed_score if complete else None

    if complete:
        risk_level = classify_risk(observed_score)
    elif observed_score >= 70:
        risk_level = "Signal élevé — données incomplètes"
    elif observed_score >= 35:
        risk_level = "Signal modéré — données incomplètes"
    elif observed_score > 0:
        risk_level = "Signaux détectés — données incomplètes"
    else:
        risk_level = "Données insuffisantes"

    reasons = [
        item["reason"] for item in factors.values()
        if item["data_available"] and (item["score"] or 0) > 0
    ]
    recommendations = generate_recommendations(factors)

    return {
        "status": "SUCCESS",
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "batch_id": str(batch_id),
        "product_name": str(product_name),
        "risk_score": risk_score,
        "observed_score": observed_score,
        "raw_score": sum(item["score"] or 0 for item in factors.values()),
        "risk_level": risk_level,
        "data_completeness": completeness,
        # Legacy key retained only for compatibility; it is not a statistical confidence.
        "confidence": completeness,
        "analysis_complete": complete,
        "available_factors": available_count,
        "total_factors": total_count,
        "factors": factors,
        "reasons": reasons,
        "recommendations": recommendations,
        "disclaimer": (
            "Résultat expérimental fondé sur des règles explicables. Le score n'est ni une probabilité "
            "de danger ni une décision réglementaire. En présence de données incomplètes, aucun niveau "
            "global de risque n'est attribué. Ne remplace pas les analyses de laboratoire ni la décision qualité."
        ),
    }
