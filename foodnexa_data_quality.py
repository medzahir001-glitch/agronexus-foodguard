import pandas as pd


# =====================================================
# FOODNEXA DATA QUALITY ENGINE
# =====================================================


REQUIRED_COLUMNS = [
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
    "expert_risk_label"
]


NUMERIC_COLUMNS = [
    "temperature_celsius",
    "storage_days",
    "ph",
    "total_viable_count",
    "enterobacteriaceae_count",
    "coliform_count",
    "staphylococcus_aureus_count"
]


def check_required_columns(df):
    """
    Vérifie la présence des colonnes nécessaires.
    """

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    return missing_columns


def check_missing_values(df):
    """
    Calcule les valeurs manquantes par colonne.
    """

    missing = df.isna().sum()

    return missing[missing > 0].to_dict()


def check_duplicates(df):
    """
    Détecte les lignes dupliquées.
    """

    return int(
        df.duplicated().sum()
    )


def check_numeric_ranges(df):
    """
    Vérifie les plages physiques/logiques
    des principales variables.
    """

    issues = []


    if "temperature_celsius" in df.columns:

        invalid_temperature = df[
            (df["temperature_celsius"] < -50)
            |
            (df["temperature_celsius"] > 60)
        ]

        if not invalid_temperature.empty:

            issues.append(
                f"{len(invalid_temperature)} valeur(s) "
                "de température hors plage."
            )


    if "storage_days" in df.columns:

        invalid_storage = df[
            df["storage_days"] < 0
        ]

        if not invalid_storage.empty:

            issues.append(
                f"{len(invalid_storage)} durée(s) "
                "de stockage négative(s)."
            )


    if "ph" in df.columns:

        invalid_ph = df[
            (df["ph"] < 0)
            |
            (df["ph"] > 14)
        ]

        if not invalid_ph.empty:

            issues.append(
                f"{len(invalid_ph)} valeur(s) "
                "de pH hors plage 0-14."
            )


    for column in [
        "total_viable_count",
        "enterobacteriaceae_count",
        "coliform_count",
        "staphylococcus_aureus_count"
    ]:

        if column in df.columns:

            invalid_values = df[
                df[column] < 0
            ]

            if not invalid_values.empty:

                issues.append(
                    f"{len(invalid_values)} valeur(s) "
                    f"négative(s) dans {column}."
                )


    return issues


def convert_numeric_columns(df):
    """
    Convertit les variables quantitatives
    vers un format numérique.
    """

    result = df.copy()


    for column in NUMERIC_COLUMNS:

        if column in result.columns:

            result[column] = pd.to_numeric(
                result[column],
                errors="coerce"
            )


    return result


def calculate_data_quality_score(df):
    """
    Calcule un score simple de qualité des données.

    Ce score est un indicateur technique du dataset,
    pas un score de sécurité alimentaire.
    """

    if df.empty:

        return 0.0


    total_cells = (
        len(df)
        *
        len(df.columns)
    )


    if total_cells == 0:

        return 0.0


    missing_cells = int(
        df.isna().sum().sum()
    )


    missing_ratio = (
        missing_cells
        /
        total_cells
    )


    score = (
        100
        *
        (1 - missing_ratio)
    )


    return round(
        max(0, score),
        2
    )


def generate_quality_report(df):
    """
    Génère un rapport complet de qualité.
    """

    working_df = convert_numeric_columns(
        df
    )


    missing_columns = check_required_columns(
        working_df
    )


    missing_values = check_missing_values(
        working_df
    )


    duplicates = check_duplicates(
        working_df
    )


    range_issues = check_numeric_ranges(
        working_df
    )


    quality_score = calculate_data_quality_score(
        working_df
    )


    if (
        not missing_columns
        and not missing_values
        and duplicates == 0
        and not range_issues
    ):

        status = "GOOD"

    else:

        status = "REVIEW"


    return {

        "status":
            status,

        "rows":
            len(working_df),

        "columns":
            len(working_df.columns),

        "quality_score":
            quality_score,

        "missing_columns":
            missing_columns,

        "missing_values":
            missing_values,

        "duplicates":
            duplicates,

        "range_issues":
            range_issues
    }
