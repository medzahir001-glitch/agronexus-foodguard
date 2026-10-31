
"""
FOODNEXA - Supabase Database Connector
Secure server-side connection using Streamlit Secrets.
"""

from functools import lru_cache
from typing import Any, Optional

import streamlit as st
from supabase import Client, create_client


def get_supabase_client() -> Client:
    """Create and cache the Supabase client using Streamlit Secrets."""

    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Supabase configuration is missing. "
            "Add SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets."
        )

    return create_client(url, key)


def _clean_record(record: dict) -> dict:
    """Convert common missing values to None before database insertion."""
    cleaned = {}

    for key, value in record.items():
        if hasattr(value, "item"):
            try:
                value = value.item()
            except (ValueError, TypeError):
                pass

        if value is None:
            cleaned[key] = None
        elif isinstance(value, float) and value != value:
            cleaned[key] = None
        else:
            cleaned[key] = value

    return cleaned


def register_lot(
    batch_id: str,
    product_name: str,
    status: str = "Registered",
) -> dict:
    """Register or update a lot."""
    if not batch_id or not product_name:
        raise ValueError("batch_id and product_name are required.")

    client = get_supabase_client()

    payload = {
        "batch_id": batch_id,
        "product_name": product_name,
        "status": status,
    }

    result = (
        client.table("lots")
        .upsert(payload, on_conflict="batch_id")
        .execute()
    )

    return result.data[0] if result.data else payload


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
    """Register the lot, then save its risk assessment."""

    register_lot(batch_id, product_name)

    payload = {
        "batch_id": batch_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "inputs": inputs or {},
        "factor_scores": factor_scores or {},
        "reasons": reasons or [],
        "recommendations": recommendations or [],
    }

    result = (
        get_supabase_client()
        .table("risk_assessments")
        .insert(_clean_record(payload))
        .execute()
    )

    return result.data[0] if result.data else payload


def save_research_observation(observation: dict) -> dict:
    """Insert or update one research observation."""

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

    return result.data[0] if result.data else payload


def save_research_dataset(records: list[dict]) -> int:
    """Save a list of research observations. Returns saved row count."""

    if not records:
        return 0

    client = get_supabase_client()
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
    """Add a traceability event to an existing lot."""

    if not batch_id or not event_type:
        raise ValueError("batch_id and event_type are required.")

    payload = {
        "batch_id": batch_id,
        "event_type": event_type,
        "event_description": event_description,
        "responsible_person": responsible_person,
        "metadata": metadata or {},
    }

    result = (
        get_supabase_client()
        .table("traceability_events")
        .insert(_clean_record(payload))
        .execute()
    )

    return result.data[0] if result.data else payload


def get_lots(limit: int = 100) -> list[dict]:
    """Retrieve registered lots."""
    result = (
        get_supabase_client()
        .table("lots")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_risk_assessments(
    batch_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Retrieve risk assessments, optionally filtered by batch."""

    query = (
        get_supabase_client()
        .table("risk_assessments")
        .select("*")
        .order("analysis_date", desc=True)
        .limit(limit)
    )

    if batch_id:
        query = query.eq("batch_id", batch_id)

    result = query.execute()
    return result.data or []


def get_research_observations(limit: int = 500) -> list[dict]:
    """Retrieve research observations."""

    result = (
        get_supabase_client()
        .table("research_observations")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_traceability_events(
    batch_id: str,
    limit: int = 200,
) -> list[dict]:
    """Retrieve traceability events for one lot."""

    result = (
        get_supabase_client()
        .table("traceability_events")
        .select("*")
        .eq("batch_id", batch_id)
        .order("event_date", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []
