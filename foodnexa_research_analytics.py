import pandas as pd
import numpy as np


RISK_ORDER = {
    "Faible": 0,
    "Modéré": 1,
    "Élevé": 2
}


def prepare_research_data(df):
    """
    Prepare FOODNEXA research dataset for analytics.
    """

    data = df.copy()

    numeric_columns = [
        "temperature_celsius",
        "storage_days",
        "ph",
        "total_viable_count",
        "enterobacteriaceae_count",
        "coliform_count",
        "staphylococcus_aureus_count"
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

    if "expert_risk_label" in data.columns:
        data["risk_numeric"] = data[
            "expert_risk_label"
        ].map(RISK_ORDER)

    return data


def calculate_basic_statistics(df):
    """
    Calculate basic descriptive statistics.
    """

    data = prepare_research_data(df)

    if data.empty:
        return {}

    statistics = {
        "observations": len(data)
    }

    numeric_columns = [
        "temperature_celsius",
        "storage_days",
        "ph",
        "total_viable_count",
        "enterobacteriaceae_count",
        "coliform_count",
        "staphylococcus_aureus_count"
    ]

    for column in numeric_columns:

        if column in data.columns:

            values = pd.to_numeric(
                data[column],
                errors="coerce"
            )

            statistics[f"{column}_mean"] = round(
                values.mean(),
                2
            )

            statistics[f"{column}_median"] = round(
                values.median(),
                2
            )

    return statistics


def calculate_risk_distribution(df):
    """
    Calculate distribution of expert risk labels.
    """

    data = prepare_research_data(df)

    if "expert_risk_label" not in data.columns:
        return pd.DataFrame(
            columns=["Risk Level", "Nombre"]
        )

    distribution = (
        data["expert_risk_label"]
        .value_counts()
        .reindex(
            ["Faible", "Modéré", "Élevé"],
            fill_value=0
        )
        .reset_index()
    )

    distribution.columns = [
        "Risk Level",
        "Nombre"
    ]

    return distribution


def calculate_risk_percentages(df):
    """
    Calculate risk percentages.
    """

    distribution = calculate_risk_distribution(df)

    total = distribution["Nombre"].sum()

    if total == 0:
        distribution["Pourcentage"] = 0.0

    else:
        distribution["Pourcentage"] = (
            distribution["Nombre"] / total * 100
        ).round(1)

    return distribution


def calculate_factor_means_by_risk(df):
    """
    Compare average numerical factors
    between risk classes.
    """

    data = prepare_research_data(df)

    required_columns = [
        "expert_risk_label",
        "temperature_celsius",
        "storage_days",
        "ph",
        "total_viable_count",
        "enterobacteriaceae_count",
        "coliform_count",
        "staphylococcus_aureus_count"
    ]

    available = [
        column
        for column in required_columns
        if column in data.columns
    ]

    if "expert_risk_label" not in available:
        return pd.DataFrame()

    factor_columns = [
        column
        for column in available
        if column != "expert_risk_label"
    ]

    if not factor_columns:
        return pd.DataFrame()

    result = (
        data
        .groupby("expert_risk_label")[
            factor_columns
        ]
        .mean()
        .reindex(
            ["Faible", "Modéré", "Élevé"]
        )
        .round(2)
    )

    return result


def calculate_correlations(df):
    """
    Calculate correlations between numerical variables
    and the expert risk label.

    This is exploratory analysis only.
    It is not proof of causality.
    """

    data = prepare_research_data(df)

    if "risk_numeric" not in data.columns:
        return pd.DataFrame()

    numeric_columns = [
        "temperature_celsius",
        "storage_days",
        "ph",
        "total_viable_count",
        "enterobacteriaceae_count",
        "coliform_count",
        "staphylococcus_aureus_count"
    ]

    available = [
        column
        for column in numeric_columns
        if column in data.columns
    ]

    if not available:
        return pd.DataFrame()

    correlations = []

    for column in available:

        temp = data[
            [column, "risk_numeric"]
        ].dropna()

        if len(temp) >= 2:

            correlation = temp[
                column
            ].corr(
                temp["risk_numeric"]
            )

            correlations.append(
                {
                    "Variable": column,
                    "Corrélation avec le risque": (
                        round(correlation, 3)
                        if pd.notna(correlation)
                        else np.nan
                    )
                }
            )

    result = pd.DataFrame(
        correlations
    )

    if not result.empty:

        result["Force absolue"] = (
            result[
                "Corrélation avec le risque"
            ].abs()
        )

        result = result.sort_values(
            "Force absolue",
            ascending=False
        ).drop(
            columns=["Force absolue"]
        )

    return result


def calculate_salmonella_rate(df):
    """
    Calculate percentage of observations
    where Salmonella was detected.
    """

    data = prepare_research_data(df)

    if "salmonella_detected" not in data.columns:
        return 0.0

    total = len(data)

    if total == 0:
        return 0.0

    detected = (
        data["salmonella_detected"]
        .astype(str)
        .str.strip()
        .str.lower()
        == "détectée"
    ).sum()

    return round(
        detected / total * 100,
        1
    )


def calculate_nonconformity_rate(df):
    """
    Calculate percentage of observations
    marked as non-conforming.
    """

    data = prepare_research_data(df)

    if "nonconformity_detected" not in data.columns:
        return 0.0

    total = len(data)

    if total == 0:
        return 0.0

    detected = (
        data["nonconformity_detected"]
        .astype(str)
        .str.strip()
        .str.lower()
        == "oui"
    ).sum()

    return round(
        detected / total * 100,
        1
    )


def generate_research_analytics(df):
    """
    Main FOODNEXA Research Analytics function.
    """

    data = prepare_research_data(df)

    if data.empty:
        return {
            "status": "EMPTY",
            "message": "Aucune observation disponible."
        }

    statistics = calculate_basic_statistics(
        data
    )

    distribution = calculate_risk_distribution(
        data
    )

    percentages = calculate_risk_percentages(
        data
    )

    factor_means = calculate_factor_means_by_risk(
        data
    )

    correlations = calculate_correlations(
        data
    )

    salmonella_rate = calculate_salmonella_rate(
        data
    )

    nonconformity_rate = (
        calculate_nonconformity_rate(
            data
        )
    )

    return {
        "status": "SUCCESS",
        "observations": len(data),
        "statistics": statistics,
        "risk_distribution": distribution,
        "risk_percentages": percentages,
        "factor_means_by_risk": factor_means,
        "correlations": correlations,
        "salmonella_rate": salmonella_rate,
        "nonconformity_rate": nonconformity_rate
    }
