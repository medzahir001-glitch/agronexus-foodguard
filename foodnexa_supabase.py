"""
FOODNEXA - Supabase Database Connector
Secure server-side connection using Streamlit Secrets.

Required Streamlit Secrets:
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SERVER_SIDE_SECRET_KEY"
"""

from functools import lru_cache
from math import isfinite
from numbers import Real
from typing import Any, Optional

import streamlit as st
from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create and cache the Supabase client using Streamlit Secrets."""
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase configuration is missing. "
            "Add SUPABASE_URL and SUPABASE_KEY in Streamlit Cloud Secrets."
        )

    return create_client(str(url).strip(), str(key).strip())


def _clean_value(value: Any) -> Any:
    """Convert NumPy scalars and missing/non-finite values to JSON-safe values."""
    if value is None:
        return None

    # Convert NumPy scalar values (for example numpy.int64 / numpy.float64).
    if hasattr(value, "item") and callable(value.item):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    if value is None:
        return None

    # Handle NaN and positive/negative infinity.
    if isinstance(value, Real) and not isinstance(value, bool):
        try:
            if not isfinite(float(value)):
                return None
        except (TypeError, ValueError, OverflowError):
            return None

    # Handle dictionaries and collections recursively.
    if isinstance(value, dict):
        return {str(k): _clean_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_clean_value(item) for item in value]

    # Handle pandas.NA / pandas.NaT without importing pandas in this connector.
    try:
        missing = value is not value  # NaN fallback for uncommon scalar types
        if missing:
            return None
        if value.__class__.__name__ in {"NAType", "NaTType"}:
            return None
    except Exception:
        pass

    return value


def _clean_record(record: dict) -> dict:
    """Return a cleaned copy of a database record."""
    return {str(key): _clean_value(value) for key, value in record.items()}


def _first_row(result: Any, fallback: dict) -> dict:
    """Return the first Supabase response row, or the submitted payload."""
    return result.data[0] if getattr(result, "data", None) else fallback


def register_lot(
    batch_id: str,
    product_name: str,
    status: str = "Registered",
) -> dict:
    """Register a new lot or update an existing lot with the same batch_id."""
    batch_id = str(batch_id).strip() if batch_id is not None else ""
    product_name = str(product_name).strip() if product_name is not None else ""

    if not batch_id or not product_name:
        raise ValueError("batch_id and product_name are required.")

    payload = {
        "batch_id": batch_id,
        "product_name": product_name,
        "status": status,
    }

    result = (
        get_supabase_client()
        .table("lots")
        .upsert(payload, on_conflict="batch_id")
        .execute()
    )

    return _first_row(result, payload)


def save_risk_assessment(
    batch_id: str,
    product_name: str,
    risk_score: float,
    risk_level: str,
    confidence: Optional[float] = None,
    inputs: Optional[dict] = None,
    factor_scores: Optional[dict] = None,
    reasons: Optional[list] = None,
    recommendations: Optional[list] = None,
) -> dict:
    """Register the lot, then save one risk assessment."""
    batch_id = str(batch_id).strip() if batch_id is not None else ""
    product_name = str(product_name).strip() if product_name is not None else ""

    if not batch_id or not product_name:
        raise ValueError("batch_id and product_name are required.")

    register_lot(batch_id, product_name)

    payload = _clean_record({
        "batch_id": batch_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "inputs": inputs or {},
        "factor_scores": factor_scores or {},
        "reasons": reasons or [],
        "recommendations": recommendations or [],
    })

    result = (
        get_supabase_client()
        .table("risk_assessments")
        .insert(payload)
        .execute()
    )

    return _first_row(result, payload)


def save_research_observation(observation: dict) -> dict:
    """Insert or update one research observation using its unique batch_id."""
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dictionary.")

    observation = _clean_record(observation)

    if not observation.get("batch_id"):
        raise ValueError("Research observation requires batch_id.")

    allowed_fields = {
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
    }

    payload = {
        key: value
        for key, value in observation.items()
        if key in allowed_fields
    }

    result = (
        get_supabase_client()
        .table("research_observations")
        .upsert(payload, on_conflict="batch_id")
        .execute()
    )

    return _first_row(result, payload)


def save_research_dataset(records: list[dict]) -> int:
    """Save a list of research observations and return the saved count."""
    if not records:
        return 0

    saved_count = 0
    for record in records:
        save_research_observation(record)
        saved_count += 1

    return saved_count


def add_traceability_event(
    batch_id: str,
    event_type: str,
    event_description: str = "",
    responsible_person: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Add a traceability event to an already registered lot."""
    batch_id = str(batch_id).strip() if batch_id is not None else ""
    event_type = str(event_type).strip() if event_type is not None else ""

    if not batch_id or not event_type:
        raise ValueError("batch_id and event_type are required.")

    payload = _clean_record({
        "batch_id": batch_id,
        "event_type": event_type,
        "event_description": event_description,
        "responsible_person": responsible_person,
        "metadata": metadata or {},
    })

    result = (
        get_supabase_client()
        .table("traceability_events")
        .insert(payload)
        .execute()
    )

    return _first_row(result, payload)


def get_lots(limit: int = 100) -> list[dict]:
    """Retrieve registered lots, newest first."""
    result = (
        get_supabase_client()
        .table("lots")
        .select("*")
        .order("created_at", desc=True)
        .limit(max(1, int(limit)))
        .execute()
    )
    return result.data or []


def get_risk_assessments(
    batch_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Retrieve risk assessments, optionally filtered by batch_id."""
    query = (
        get_supabase_client()
        .table("risk_assessments")
        .select("*")
        .order("analysis_date", desc=True)
        .limit(max(1, int(limit)))
    )

    if batch_id:
        query = query.eq("batch_id", str(batch_id).strip())

    result = query.execute()
    return result.data or []


def get_research_observations(limit: int = 500) -> list[dict]:
    """Retrieve research observations, newest first."""
    result = (
        get_supabase_client()
        .table("research_observations")
        .select("*")
        .order("created_at", desc=True)
        .limit(max(1, int(limit)))
        .execute()
    )
    return result.data or []


def get_traceability_events(
    batch_id: str,
    limit: int = 200,
) -> list[dict]:
    """Retrieve traceability events for one batch."""
    if not batch_id:
        raise ValueError("batch_id is required.")

    result = (
        get_supabase_client()
        .table("traceability_events")
        .select("*")
        .eq("batch_id", str(batch_id).strip())
        .order("event_date", desc=True)
        .limit(max(1, int(limit)))
        .execute()
    )
    return result.data or []
