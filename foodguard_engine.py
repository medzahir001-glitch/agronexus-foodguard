from datetime import datetime

def validate_inputs(
    temperature,
    storage_days,
    ph,
    cold_chain_broken,
    hygiene_controlled,
    pasteurized
):
    errors = []

    if not -10 <= temperature <= 60:
        errors.append("La température doit être comprise entre -10°C et 60°C.")

    if not 0 <= storage_days <= 365:
        errors.append("La durée de stockage doit être comprise entre 0 et 365 jours.")

    if not 0 <= ph <= 14:
        errors.append("Le pH doit être compris entre 0 et 14.")

    if not isinstance(cold_chain_broken, bool):
        errors.append("cold_chain_broken doit être booléen.")

    if not isinstance(hygiene_controlled, bool):
        errors.append("hygiene_controlled doit être booléen.")

    if not isinstance(pasteurized, bool):
        errors.append("pasteurized doit être booléen.")

    return errors


def analyze_temperature(temperature):
    if temperature > 8:
        return 35, "Élevé", "Température de stockage élevée"
    elif temperature > 4:
        return 15, "Modéré", "Température supérieure à la cible du prototype"
    else:
        return 0, "Faible", "Température acceptable selon les règles du prototype"


def analyze_storage_duration(storage_days):
    if storage_days > 7:
        return 20, "Élevé", "Durée de stockage longue"
    elif storage_days > 3:
        return 10, "Modéré", "Durée de stockage relativement longue"
    else:
        return 0, "Faible", "Durée de stockage courte"


def analyze_ph(ph):
    if ph < 5.8:
        return 25, "Élevé", "pH bas pouvant indiquer une modification du produit"
    elif ph < 6.2:
        return 10, "Modéré", "pH légèrement inférieur à la valeur attendue"
    else:
        return 0, "Faible", "Aucune anomalie de pH détectée par le prototype"


def analyze_cold_chain(cold_chain_broken):
    if cold_chain_broken:
        return 30, "Élevé", "Interruption déclarée de la chaîne du froid"
    return 0, "Faible", "Aucune interruption déclarée"


def analyze_hygiene(hygiene_controlled):
    if not hygiene_controlled:
        return 25, "Élevé", "Conditions d'hygiène non maîtrisées ou non confirmées"
    return 0, "Faible", "Conditions d'hygiène déclarées maîtrisées"


def analyze_pasteurization(pasteurized):
    if not pasteurized:
        return 20, "Élevé", "Pasteurisation absente ou non confirmée"
    return 0, "Faible", "Produit déclaré pasteurisé"


def classify_risk(score):
    if score >= 70:
        return "Élevé"
    elif score >= 35:
        return "Modéré"
    return "Faible"


def calculate_confidence(factors):
    """
    Estimation simple de confiance basée sur
    la disponibilité des informations.
    Ce n'est pas encore une probabilité statistique.
    """

    total_factors = len(factors)
    available_factors = sum(
        1 for factor in factors.values()
        if factor["data_available"]
    )

    confidence = (available_factors / total_factors) * 100

    return round(confidence, 1)


def generate_recommendations(factors):
    recommendations = []

    for name, factor in factors.items():

        if factor["score"] == 0:
            continue

        if name == "temperature":
            recommendations.append(
                "Vérifier les enregistrements de température et la chaîne du froid."
            )

        elif name == "storage_duration":
            recommendations.append(
                "Vérifier la date de production, la date limite et la durée réelle de stockage."
            )

        elif name == "ph":
            recommendations.append(
                "Réaliser une vérification complémentaire du pH et les analyses qualité adaptées."
            )

        elif name == "cold_chain":
            recommendations.append(
                "Isoler la quantité concernée et analyser la durée de l'interruption."
            )

        elif name == "hygiene":
            recommendations.append(
                "Réévaluer le nettoyage, la désinfection et les pratiques d'hygiène."
            )

        elif name == "pasteurization":
            recommendations.append(
                "Vérifier les paramètres de traitement thermique et les enregistrements disponibles."
            )

    if not recommendations:
        recommendations.append(
            "Continuer la surveillance et conserver les enregistrements de contrôle."
        )

    return recommendations


def assess_dairy_food_safety_risk(
    temperature,
    storage_days,
    ph,
    cold_chain_broken,
    hygiene_controlled,
    pasteurized,
    batch_id="BATCH-001",
    product_name="Produit laitier"
):
    errors = validate_inputs(
        temperature,
        storage_days,
        ph,
        cold_chain_broken,
        hygiene_controlled,
        pasteurized
    )

    if errors:
        return {
            "status": "ERROR",
            "errors": errors
        }

    factors = {}

    temp_score, temp_level, temp_reason = analyze_temperature(temperature)
    factors["temperature"] = {
        "score": temp_score,
        "level": temp_level,
        "reason": temp_reason,
        "data_available": True
    }

    storage_score, storage_level, storage_reason = analyze_storage_duration(
        storage_days
    )
    factors["storage_duration"] = {
        "score": storage_score,
        "level": storage_level,
        "reason": storage_reason,
        "data_available": True
    }

    ph_score, ph_level, ph_reason = analyze_ph(ph)
    factors["ph"] = {
        "score": ph_score,
        "level": ph_level,
        "reason": ph_reason,
        "data_available": True
    }

    cold_score, cold_level, cold_reason = analyze_cold_chain(
        cold_chain_broken
    )
    factors["cold_chain"] = {
        "score": cold_score,
        "level": cold_level,
        "reason": cold_reason,
        "data_available": True
    }

    hygiene_score, hygiene_level, hygiene_reason = analyze_hygiene(
        hygiene_controlled
    )
    factors["hygiene"] = {
        "score": hygiene_score,
        "level": hygiene_level,
        "reason": hygiene_reason,
        "data_available": True
    }

    pasteurization_score, pasteurization_level, pasteurization_reason = (
        analyze_pasteurization(pasteurized)
    )
    factors["pasteurization"] = {
        "score": pasteurization_score,
        "level": pasteurization_level,
        "reason": pasteurization_reason,
        "data_available": True
    }

    raw_score = sum(
        factor["score"]
        for factor in factors.values()
    )

    final_score = min(raw_score, 100)
    final_level = classify_risk(final_score)

    reasons = [
        factor["reason"]
        for factor in factors.values()
        if factor["score"] > 0
    ]

    recommendations = generate_recommendations(factors)
    confidence = calculate_confidence(factors)

    return {
        "status": "SUCCESS",
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "batch_id": batch_id,
        "product_name": product_name,
        "risk_score": final_score,
        "raw_score": raw_score,
        "risk_level": final_level,
        "confidence": confidence,
        "factors": factors,
        "reasons": reasons,
        "recommendations": recommendations,
        "disclaimer": (
            "Résultat expérimental d'aide à la décision. "
            "Ne remplace pas les analyses de laboratoire ni la décision du responsable qualité."
        )
    }


