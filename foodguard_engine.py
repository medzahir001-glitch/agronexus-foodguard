"""
FOODNEXA Risk Engine V2 — explainable dairy risk-screening prototype.

IMPORTANT:
- Research / screening prototype only; not a validated predictive model.
- Scores are rule-based indicators, not probabilities of contamination or illness.
- Thresholds below are provisional prototype rules and require product-specific
  scientific review, laboratory evidence, and expert validation before operational use.
- Missing inputs remain missing. An overall risk score is issued only when all
  six factors are available.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Callable

ENGINE_VERSION = "2.0.0"

# Maximum rule-points per factor. These are prototype weights, not validated
# epidemiological or regulatory weights.
FACTOR_MAX_SCORES = {
    "temperature": 35,
    "storage_duration": 20,
    "ph": 25,
    "cold_chain": 30,
    "hygiene": 25,
    "pasteurization": 20,
}
TOTAL_MAX_SCORE = sum(FACTOR_MAX_SCORES.values())  # 155

# Legacy raw-point boundaries retained for backward comparability.
# They are converted to normalized percentages; they are NOT validated limits.
RAW_MODERATE_THRESHOLD = 35
RAW_HIGH_THRESHOLD = 70
MODERATE_THRESHOLD_PERCENT = round(
    RAW_MODERATE_THRESHOLD / TOTAL_MAX_SCORE * 100, 2
)
HIGH_THRESHOLD_PERCENT = round(
    RAW_HIGH_THRESHOLD / TOTAL_MAX_SCORE * 100, 2
)


def _to_number(name: str, value: Any, low: float, high: float,
               errors: list[str]) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        errors.append(f"{name} doit être une valeur numérique, pas un booléen.")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        errors.append(f"{name} doit être une valeur numérique ou non renseignée.")
        return None
    if not isfinite(number):
        errors.append(f"{name} doit être une valeur numérique finie.")
        return None
    if not low <= number <= high:
        errors.append(f"{name} doit être compris entre {low} et {high}.")
        return None
    return number


def validate_inputs(temperature, storage_days, ph, cold_chain_broken,
                    hygiene_controlled, pasteurized):
    errors: list[str] = []
    _to_number("temperature", temperature, -20, 60, errors)
    _to_number("storage_days", storage_days, 0, 365, errors)
    _to_number("ph", ph, 0, 14, errors)

    for name, value in (
        ("cold_chain_broken", cold_chain_broken),
        ("hygiene_controlled", hygiene_controlled),
        ("pasteurized", pasteurized),
    ):
        if value is not None and not isinstance(value, bool):
            errors.append(f"{name} doit être vrai, faux ou non renseigné.")
    return errors


def _factor(score: int | None, level: str, reason: str, name: str) -> dict:
    available = score is not None
    maximum = FACTOR_MAX_SCORES[name]
    return {
        "score": score,
        "level": level,
        "reason": reason,
        "data_available": available,
        "maximum_score": maximum,
        "weight_percent": round(maximum / TOTAL_MAX_SCORE * 100, 2),
        "evidence_type": "user_input",
    }


def analyze_temperature(temperature):
    if temperature is None:
        return None, "Non renseigné", "Température non fournie."
    value = float(temperature)
    if value > 8:
        return 35, "Élevé", (
            "Température supérieure à 8°C selon la règle expérimentale "
            "actuelle du prototype; durée d'exposition à vérifier."
        )
    if value > 4:
        return 15, "Modéré", (
            "Température supérieure à la cible expérimentale de 4°C; "
            "durée d'exposition à vérifier."
        )
    return 0, "Faible", (
        "Aucun signal de température détecté par la règle actuelle du prototype; "
        "cela ne prouve pas la sécurité du produit."
    )


def analyze_storage_duration(storage_days):
    if storage_days is None:
        return None, "Non renseigné", "Durée de stockage non fournie."
    value = float(storage_days)
    if value > 7:
        return 20, "Élevé", (
            "Durée supérieure à 7 jours selon la règle expérimentale actuelle; "
            "la date limite et les conditions réelles doivent être vérifiées."
        )
    if value > 3:
        return 10, "Modéré", (
            "Durée supérieure à 3 jours selon la règle expérimentale actuelle; "
            "la date limite et les conditions réelles doivent être vérifiées."
        )
    return 0, "Faible", (
        "Aucun signal de durée détecté par la règle actuelle; "
        "la conformité à la date limite n'est pas vérifiée."
    )


def analyze_ph(ph):
    if ph is None:
        return None, "Non renseigné", "pH non fourni."
    value = float(ph)
    if value < 5.8:
        return 25, "Élevé", (
            "pH inférieur à 5,8 selon la règle expérimentale du prototype; "
            "interprétation à confirmer selon le produit et la méthode."
        )
    if value < 6.2:
        return 10, "Modéré", (
            "pH entre 5,8 et 6,2 selon la règle expérimentale du prototype; "
            "interprétation à confirmer selon le produit et la méthode."
        )
    return 0, "Faible", (
        "Aucun signal de pH détecté par la règle actuelle; "
        "cela ne démontre pas la conformité du produit."
    )


def analyze_cold_chain(value):
    if value is None:
        return None, "Non renseigné", "État de la chaîne du froid non confirmé."
    if value:
        return 30, "Élevé", "Interruption de la chaîne du froid déclarée."
    return 0, "Faible", (
        "Aucune interruption déclarée; cette information repose sur une déclaration "
        "et non sur un enregistrement continu."
    )


def analyze_hygiene(value):
    if value is None:
        return None, "Non renseigné", "État de maîtrise de l'hygiène non confirmé."
    if not value:
        return 25, "Élevé", "Conditions d'hygiène déclarées non maîtrisées."
    return 0, "Faible", (
        "Conditions d'hygiène déclarées maîtrisées; preuve documentaire ou audit "
        "non vérifié par ce champ."
    )


def analyze_pasteurization(value):
    if value is None:
        return None, "Non renseigné", "Statut de pasteurisation non confirmé."
    if not value:
        return 20, "Élevé", "Pasteurisation déclarée absente."
    return 0, "Faible", (
        "Produit déclaré pasteurisé; le couple temps-température et les "
        "enregistrements du traitement ne sont pas vérifiés par ce champ."
    )


def classify_risk(score: float) -> str:
    """Classify a normalized 0–100 score using provisional legacy-equivalent bands."""
    if score >= HIGH_THRESHOLD_PERCENT:
        return "Élevé"
    if score >= MODERATE_THRESHOLD_PERCENT:
        return "Modéré"
    return "Faible"


def calculate_data_completeness(factors: dict) -> float:
    if not factors:
        return 0.0
    available = sum(1 for item in factors.values() if item.get("data_available"))
    return round(available / len(factors) * 100, 1)


def calculate_confidence(factors: dict):
    """Deprecated compatibility helper. Completeness is not statistical confidence."""
    return None


def generate_recommendations(factors: dict) -> list[str]:
    recommendations: list[str] = []
    mapping = {
        "temperature": "Vérifier les enregistrements de température et la durée d'exposition.",
        "storage_duration": "Vérifier la date de production, la date limite et la durée réelle de stockage.",
        "ph": "Vérifier la mesure du pH, la méthode utilisée et les spécifications du produit.",
        "cold_chain": "Évaluer la durée de l'interruption et appliquer la procédure de maîtrise du lot.",
        "hygiene": "Réévaluer le nettoyage, la désinfection et les preuves de maîtrise de l'hygiène.",
        "pasteurization": "Vérifier les paramètres temps-température et les enregistrements du traitement.",
    }
    for name, item in factors.items():
        if item.get("data_available") and (item.get("score") or 0) > 0:
            recommendations.append(mapping.get(name, "Vérifier le facteur signalé."))

    missing = [
        name for name, item in factors.items()
        if not item.get("data_available")
    ]
    if missing:
        recommendations.append(
            "Compléter les facteurs non renseignés avant toute interprétation globale du lot."
        )
    if not recommendations:
        recommendations.append(
            "Conserver les preuves de contrôle et poursuivre la surveillance selon le plan applicable."
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
    """Return an explainable prototype assessment; no claim of validated prediction."""
    errors = validate_inputs(
        temperature, storage_days, ph,
        cold_chain_broken, hygiene_controlled, pasteurized,
    )
    if errors:
        return {"status": "ERROR", "errors": errors}

    numeric = {
        "temperature": _to_number("temperature", temperature, -20, 60, []),
        "storage_duration": _to_number("storage_days", storage_days, 0, 365, []),
        "ph": _to_number("ph", ph, 0, 14, []),
    }

    analyzers: dict[str, Callable] = {
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
        factors[name] = _factor(score, level, reason, name)

    available_count = sum(
        1 for item in factors.values() if item["data_available"]
    )
    total_count = len(factors)
    completeness = calculate_data_completeness(factors)
    raw_score = sum(
        item["score"] or 0 for item in factors.values()
    )
    complete = available_count == total_count

    # A global score is only calculated when all six factors are supplied.
    # Normalization uses the fixed total maximum (155), not a clipped raw sum.
    risk_score = (
        round(raw_score / TOTAL_MAX_SCORE * 100, 1)
        if complete else None
    )

    if complete:
        risk_level = classify_risk(risk_score)
        analysis_status = "Complete"
    else:
        if raw_score >= RAW_HIGH_THRESHOLD:
            risk_level = "Signal élevé — données incomplètes"
        elif raw_score >= RAW_MODERATE_THRESHOLD:
            risk_level = "Signal modéré — données incomplètes"
        elif raw_score > 0:
            risk_level = "Signaux détectés — données incomplètes"
        else:
            risk_level = "Données insuffisantes"
        analysis_status = "Données incomplètes"

    reasons = [
        item["reason"] for item in factors.values()
        if item["data_available"] and (item["score"] or 0) > 0
    ]
    if reasons and not complete:
        signal_summary = (
            "Des signaux ont été détectés parmi les facteurs renseignés, mais les données "
            "restent incomplètes; elles ne permettent pas de calculer un score global."
        )
    elif reasons:
        signal_summary = (
            "Des signaux associés aux facteurs renseignés ont été détectés. "
            "Ils nécessitent une vérification selon les procédures qualité applicables."
        )
    elif complete:
        signal_summary = (
            "Aucun signal n'a été détecté par les règles actuelles du prototype. "
            "Cela ne constitue pas une preuve de sécurité ou de conformité."
        )
    else:
        signal_summary = (
            "Les données disponibles ne permettent ni de confirmer ni d'exclure "
            "un signal de risque."
        )

    recommendations = generate_recommendations(factors)

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "analysis_date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "batch_id": str(batch_id),
        "product_name": str(product_name),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "analysis_status": analysis_status,
        "analysis_complete": complete,
        "raw_score": raw_score,
        "maximum_raw_score": TOTAL_MAX_SCORE,
        "observed_score": raw_score,  # legacy key: raw points, not normalized score
        "data_completeness": completeness,
        "confidence": None,  # no statistical confidence estimate is implemented
        "available_factors": available_count,
        "total_factors": total_count,
        "factors": factors,
        "reasons": reasons,
        "signal_summary": signal_summary,
        "recommendations": recommendations,
        "scoring_method": (
            "risk_score = raw_score / 155 * 100; "
            "calculated only when all six factors are available"
        ),
        "classification_thresholds": {
            "moderate_from_percent": MODERATE_THRESHOLD_PERCENT,
            "high_from_percent": HIGH_THRESHOLD_PERCENT,
            "basis": (
                "Provisional prototype bands converted from legacy raw-point "
                "boundaries; not scientifically validated."
            ),
        },
        "disclaimer": (
            "Prototype expérimental de screening fondé sur des règles explicables. "
            "Le score n'est ni une probabilité de danger ni une décision réglementaire. "
            "Les seuils et pondérations sont provisoires et nécessitent une validation "
            "scientifique, produit-spécifique et experte. Les déclarations utilisateur "
            "ne remplacent pas les mesures, enregistrements, analyses de laboratoire "
            "ou décisions qualité."
        ),
    }
