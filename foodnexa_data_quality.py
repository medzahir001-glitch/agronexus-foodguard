
import math
import pandas as pd


# =========================================================
# FOODNEXA - DATA QUALITY ENGINE V2
# Product-aware data quality and analytical coverage
# =========================================================

VERSION = "2.0"

REQUIRED_COLUMNS = [
    "batch_id",
    "product_name",
]

TRACEABILITY_COLUMNS = [
    "product_category",
    "sample_reference",
    "supplier",
    "sampling_date",
    "analysis_date",
    "laboratory",
    "analyst",
]

DOCUMENTATION_COLUMNS = [
    "analysis_units",
    "analysis_methods",
    "applicable_limits_reference",
]

DOMAIN_FIELDS = {
    "Physicochemical": [
        "temperature_celsius", "storage_days", "ph",
        "humidity", "dry_matter", "ash", "protein",
        "fat", "titratable_acidity", "density",
        "conductivity", "viscosity", "brix", "salt",
        "particle_size",
    ],
    "Microbiological": [
        "total_viable_count", "enterobacteriaceae_count",
        "coliform_count", "e_coli_count",
        "yeast_mould_count", "staphylococcus_aureus_count",
        "bacillus_cereus_count", "listeria_detected",
        "salmonella_detected",
    ],
    "Contaminants": [
        "pesticide_residues", "lead", "cadmium",
        "mercury", "arsenic", "aflatoxins", "mycotoxins",
    ],
    "Process": [
        "processing_temperature", "processing_time",
        "cooling_temperature", "cooling_time",
        "cold_chain_broken", "hygiene_controlled",
        "pasteurized",
    ],
    "Sensory": [
        "sensory_status",
    ],
    "Packaging": [
        "net_weight", "seal_integrity", "vacuum",
    ],
}

# Initial product profiles.
# These define analytical coverage priorities, not legal limits.
PRODUCT_PROFILES = {
    "dairy": {
        "keywords": [
            "lait", "milk", "yaourt", "yogurt",
            "fromage", "cheese", "produit laitier",
            "produits laitiers", "dairy",
        ],
        "priority": {
            "Physicochemical": [
                "temperature_celsius",
                "ph",
                "density",
                "fat",
                "protein",
                "titratable_acidity",
            ],
            "Microbiological": [
                "total_viable_count",
                "enterobacteriaceae_count",
                "coliform_count",
                "salmonella_detected",
            ],
            "Process": [
                "processing_temperature",
                "processing_time",
                "cooling_temperature",
                "cold_chain_broken",
            ],
            "Sensory": [
                "sensory_status",
            ],
            "Packaging": [
                "seal_integrity",
            ],
        },
    },
    "default": {
        "keywords": [],
        "priority": {},
    },
}

# Technical plausibility checks only.
# These are NOT regulatory or product acceptance limits.
NUMERIC_RANGES = {
    "temperature_celsius": (-80, 150),
    "storage_days": (0, 10000),
    "ph": (0, 14),
    "humidity": (0, 100),
    "dry_matter": (0, 100),
    "ash": (0, 100),
    "protein": (0, 100),
    "fat": (0, 100),
    "total_viable_count": (0, 1e15),
    "enterobacteriaceae_count": (0, 1e15),
    "coliform_count": (0, 1e15),
    "e_coli_count": (0, 1e15),
    "yeast_mould_count": (0, 1e15),
    "staphylococcus_aureus_count": (0, 1e15),
    "bacillus_cereus_count": (0, 1e15),
    "lead": (0, 1e9),
    "cadmium": (0, 1e9),
    "mercury": (0, 1e9),
    "arsenic": (0, 1e9),
    "brix": (0, 100),
    "salt": (0, 100),
}


# =========================================================
# DATA PREPARATION
# =========================================================

def _is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        return value.strip().lower() in {
            "",
            "none",
            "nan",
            "nat",
            "not tested",
            "not_tested",
            "n/a",
            "na",
        }

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _flatten_record(record):
    """
    Makes JSONB analytical sections accessible as columns.
    Existing top-level values take priority.
    """

    result = dict(record)

    json_sections = [
        "process_data",
        "physicochemical_results",
        "microbiological_results",
        "contaminant_results",
        "sensory_results",
        "packaging_results",
    ]

    for section in json_sections:
        values = result.get(section)

        if isinstance(values, dict):
            for key, value in values.items():
                if key not in result or _is_missing(result.get(key)):
                    result[key] = value

    return result


def _prepare_dataframe(data):
    if isinstance(data, pd.DataFrame):
        df = data.copy()

    elif isinstance(data, dict):
        df = pd.DataFrame([data])

    elif isinstance(data, list):
        df = pd.DataFrame(data)

    else:
        return pd.DataFrame()

    if df.empty:
        return df

    records = [
        _flatten_record(record)
        for record in df.to_dict(orient="records")
    ]

    return pd.DataFrame(records)


# =========================================================
# PRODUCT PROFILE
# =========================================================

def get_product_profile(product_name, product_category=""):
    text = (
        f"{product_name or ''} {product_category or ''}"
    ).lower()

    for profile_name, profile in PRODUCT_PROFILES.items():

        if profile_name == "default":
            continue

        if any(
            keyword in text
            for keyword in profile["keywords"]
        ):
            return profile_name, profile

    return "default", PRODUCT_PROFILES["default"]


# =========================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =========================================================

def check_required_columns(df):
    return [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]


def check_missing_values(df):
    missing = df.isna().sum()
    return missing[missing > 0].to_dict()


def check_duplicates(df):
    if df.empty:
        return 0

    return int(df.duplicated(keep="first").sum())


def convert_numeric_columns(df):
    result = df.copy()

    for column in NUMERIC_RANGES:

        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    return result


# =========================================================
# VALIDATION
# =========================================================

def check_numeric_ranges(df):
    issues = []

    for column, limits in NUMERIC_RANGES.items():

        if column not in df.columns:
            continue

        minimum, maximum = limits

        for index, value in df[column].items():

            if _is_missing(value):
                continue

            try:
                number = float(value)

                if not math.isfinite(number):
                    raise ValueError

            except (TypeError, ValueError, OverflowError):
                issues.append(
                    f"Ligne {index + 1}: valeur non numérique "
                    f"dans {column}."
                )
                continue

            if number < minimum or number > maximum:
                issues.append(
                    f"Ligne {index + 1}: valeur hors plage "
                    f"technique dans {column} ({number})."
                )

    return issues


def _get_coverage(record, fields):

    if not fields:
        return {
            "tested": 0,
            "not_tested": 0,
            "total": 0,
            "coverage_percent": None,
        }

    tested = sum(
        1
        for field in fields
        if not _is_missing(record.get(field))
    )

    total = len(fields)

    return {
        "tested": tested,
        "not_tested": total - tested,
        "total": total,
        "coverage_percent": round(
            tested / total * 100,
            1,
        ),
    }


# =========================================================
# DATA QUALITY SCORING
# =========================================================

def evaluate_observation(record):

    profile_name, profile = get_product_profile(
        record.get("product_name"),
        record.get("product_category"),
    )

    identity = _get_coverage(
        record,
        REQUIRED_COLUMNS,
    )

    traceability = _get_coverage(
        record,
        TRACEABILITY_COLUMNS,
    )

    documentation = _get_coverage(
        record,
        DOCUMENTATION_COLUMNS,
    )

    priority_fields = []

    for fields in profile["priority"].values():
        priority_fields.extend(fields)

    if priority_fields:
        analytical = _get_coverage(
            record,
            priority_fields,
        )
    else:
        all_fields = [
            field
            for fields in DOMAIN_FIELDS.values()
            for field in fields
        ]

        analytical = _get_coverage(
            record,
            all_fields,
        )

    # Weighted technical quality score.
    # Identity: 20%
    # Traceability: 20%
    # Analytical coverage: 45%
    # Documentation: 15%

    identity_score = identity["coverage_percent"]
    trace_score = traceability["coverage_percent"]
    analytical_score = analytical["coverage_percent"]
    documentation_score = documentation["coverage_percent"]

    score = (
        identity_score * 0.20
        + trace_score * 0.20
        + analytical_score * 0.45
        + documentation_score * 0.15
    )

    technical_issues = []

    for field, (minimum, maximum) in NUMERIC_RANGES.items():

        value = record.get(field)

        if _is_missing(value):
            continue

        try:
            number = float(value)

            if not math.isfinite(number):
                raise ValueError

        except (TypeError, ValueError, OverflowError):
            technical_issues.append({
                "field": field,
                "issue": "Non-numeric or invalid value",
                "value": str(value),
            })
            continue

        if number < minimum or number > maximum:
            technical_issues.append({
                "field": field,
                "issue": "Outside technical plausibility range",
                "value": number,
            })

    # Small quality penalty for technical data issues.
    if technical_issues:
        score *= max(
            0.5,
            1 - 0.05 * len(technical_issues),
        )

    return {
        "quality_score": round(score, 1),
        "profile": profile_name,
        "identity": identity,
        "traceability": traceability,
        "documentation": documentation,
        "analytical_coverage": analytical,
        "technical_issues": technical_issues,
    }


def calculate_data_quality_score(df):
    if df.empty:
        return 0.0

    records = df.to_dict(orient="records")

    scores = [
        evaluate_observation(record)["quality_score"]
        for record in records
    ]

    return round(sum(scores) / len(scores), 2)


# =========================================================
# DOMAIN COVERAGE
# =========================================================

def calculate_domain_coverage(df):

    results = {}

    for domain, fields in DOMAIN_FIELDS.items():

        tested = 0
        possible = len(df) * len(fields)

        for record in df.to_dict(orient="records"):

            tested += sum(
                1
                for field in fields
                if not _is_missing(record.get(field))
            )

        results[domain] = {
            "tested": tested,
            "not_tested": possible - tested,
            "total": possible,
            "coverage_percent": round(
                tested / possible * 100,
                1,
            ) if possible else 0,
        }

    return results


# =========================================================
# MAIN REPORT
# =========================================================

def generate_quality_report(df):
    """
    FOODNEXA Data Quality Engine V2.

    Accepts a DataFrame, dictionary or list of dictionaries.

    Missing analytical results remain Not tested.
    Missing results are never converted into zero.
    """

    working_df = _prepare_dataframe(df)

    if working_df.empty:

        return {
            "version": VERSION,
            "status": "NO_DATA",
            "observations": 0,
            "rows": 0,
            "columns": 0,
            "quality_score": 0.0,
            "duplicate_count": 0,
            "duplicates": 0,
            "missing_columns": REQUIRED_COLUMNS.copy(),
            "missing_values": {},
            "range_issues": [],
            "domain_coverage": {},
            "record_details": [],
            "not_tested_count": 0,
            "technical_issues": [],
        }

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

    records = working_df.to_dict(orient="records")

    details = [
        evaluate_observation(record)
        for record in records
    ]

    quality_score = round(
        sum(
            item["quality_score"]
            for item in details
        ) / len(details),
        1,
    )

    domain_coverage = calculate_domain_coverage(
        working_df
    )

    not_tested_count = sum(
        item["analytical_coverage"]["not_tested"]
        for item in details
    )

    technical_issues = []

    for index, detail in enumerate(details, start=1):

        for issue in detail["technical_issues"]:

            technical_issues.append({
                "observation": index,
                **issue,
            })

    # Status describes data quality, not food safety.
    if (
        not missing_columns
        and duplicates == 0
        and not range_issues
        and quality_score >= 85
    ):
        status = "GOOD"

    elif quality_score >= 60 and not range_issues:
        status = "ACCEPTABLE_WITH_REVIEW"

    else:
        status = "REVIEW"

    # Compatibility keys are retained for the existing app.
    return {
        "version": VERSION,
        "status": status,

        "observations": len(working_df),
        "rows": len(working_df),
        "columns": len(working_df.columns),

        "quality_score": quality_score,

        "duplicate_count": duplicates,
        "duplicates": duplicates,

        "missing_columns": missing_columns,
        "missing_values": missing_values,

        "range_issues": range_issues,
        "technical_issues": technical_issues,

        "domain_coverage": domain_coverage,

        "record_details": details,

        "not_tested_count": not_tested_count,

        "identity_score": round(
            sum(x["identity"]["coverage_percent"] for x in details)
            / len(details),
            1,
        ),

        "traceability_score": round(
            sum(x["traceability"]["coverage_percent"] for x in details)
            / len(details),
            1,
        ),

        "analytical_coverage_score": round(
            sum(x["analytical_coverage"]["coverage_percent"] for x in details)
            / len(details),
            1,
        ),

        "documentation_score": round(
            sum(x["documentation"]["coverage_percent"] for x in details)
            / len(details),
            1,
        ),

        "methodology": {
            "identity_weight": 20,
            "traceability_weight": 20,
            "analytical_coverage_weight": 45,
            "documentation_weight": 15,
            "missing_values_policy": "NOT_TESTED",
            "duplicate_policy": "EXACT_ROW_DUPLICATES",
        },
    }
