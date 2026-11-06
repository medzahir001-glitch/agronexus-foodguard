"""
FOODNEXA - Supabase Database Connector
Server-side connection using Streamlit Secrets.

Required Streamlit Secrets:
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SERVER_SIDE_SECRET_KEY"

Use a server-side secret key only on Streamlit Cloud. Never expose it in the
browser, GitHub source code, screenshots, or public repositories.
"""

from functools import lru_cache
from math import isfinite
from numbers import Real
from typing import Any, Optional

import streamlit as st
from supabase import Client, create_client


def _config_value(name: str) -> str:
    try:
        value = st.secrets.get(name)
    except Exception as exc:
        raise RuntimeError(
            "Impossible de lire les Streamlit Secrets. Vérifiez les paramètres "
            "SUPABASE_URL et SUPABASE_KEY dans Streamlit Cloud."
        ) from exc
    return str(value).strip() if value else ""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Create and cache a Supabase client from Streamlit Secrets."""
    url = _config_value("SUPABASE_URL")
    key = _config_value("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "Configuration Supabase absente : ajoutez SUPABASE_URL et "
            "SUPABASE_KEY dans Streamlit Cloud → App settings → Secrets."
        )

    if not url.startswith("https://") or not url.endswith(".supabase.co"):
        raise ValueError(
            "SUPABASE_URL invalide. Utilisez uniquement l'URL du projet, "
            "au format https://<project-ref>.supabase.co, sans /rest/v1/."
        )

    if "/rest/v1" in url:
        raise ValueError(
            "SUPABASE_URL ne doit pas contenir /rest/v1/. "
            "Utilisez l'URL racine du projet Supabase."
        )

    try:
        return create_client(url, key)
    except Exception as exc:
        # Do not include the key or request headers in the raised message.
        raise RuntimeError(
            "Impossible d'initialiser le client Supabase. Vérifiez l'URL "
            "du projet et la clé serveur dans Streamlit Secrets."
        ) from exc


def _clean_value(value: Any) -> Any:
    """Convert NumPy/Pandas scalar values and non-finite numbers to JSON-safe values."""
    if value is None:
        return None

    if hasattr(value, "item") and callable(value.item):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    if value is None:
        return None

    if isinstance(value, Real) and not isinstance(value, bool):
        try:
            if not isfinite(float(value)):
                return None
        except (TypeError, ValueError, OverflowError):
            return None

    if isinstance(value, dict):
        return {str(k): _clean_value(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_clean_value(item) for item in value]

    if value.__class__.__name__ in {"NAType", "NaTType"}:
        return None

    return value


def _clean_record(record: dict) -> dict:
    return {str(key): _clean_value(value) for key, value in record.items()}


def _first_row(result: Any, fallback: dict) -> dict:
    data = getattr(result, "data", None)
    return data[0] if data else fallback


def test_supabase_connection() -> dict:
    """Perform a minimal read to test credentials, network, and table access."""
    result = get_supabase_client().table("lots").select("batch_id").limit(1).execute()
    return {"connected": True, "rows_returned": len(result.data or [])}


def register_lot(batch_id: str, product_name: str, status: str = "Registered") -> dict:
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
        get_supabase_client().table("lots")
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
    batch_id = str(batch_id).strip() if batch_id is not None else ""
    product_name = str(product_name).strip() if product_name is not None else ""
    if not batch_id or not product_name:
        raise ValueError("batch_id and product_name are required.")

    # Keep each step separate so the exception identifies the failing operation.
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

    result = get_supabase_client().table("risk_assessments").insert(payload).execute()
    return _first_row(result, payload)


def save_research_observation(observation: dict) -> dict:
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dictionary.")

    observation = _clean_record(observation)
    if not observation.get("batch_id"):
        raise ValueError("Research observation requires batch_id.")

    allowed_fields = {
        "batch_id", "product_name", "temperature_celsius", "storage_days", "ph",
        "cold_chain_broken", "hygiene_controlled", "pasteurized",
        "total_viable_count", "enterobacteriaceae_count", "coliform_count",
        "staphylococcus_aureus_count", "salmonella_detected", "sensory_status",
        "nonconformity_detected", "expert_risk_label", "product_category",
        "sample_reference", "supplier", "sampling_date", "analysis_date",
        "laboratory", "analyst", "process_data", "physicochemical_results",
        "microbiological_results", "contaminant_results", "sensory_results",
        "packaging_results", "analysis_units", "analysis_methods",
        "applicable_limits_reference", "notes",
    }
    payload = {key: value for key, value in observation.items() if key in allowed_fields}

    result = (
        get_supabase_client().table("research_observations")
        .upsert(payload, on_conflict="batch_id")
        .execute()
    )
    return _first_row(result, payload)


def save_research_dataset(records: list[dict]) -> int:
    if not records:
        return 0
    for record in records:
        save_research_observation(record)
    return len(records)


def add_traceability_event(
    batch_id: str,
    event_type: str,
    event_description: str = "",
    responsible_person: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
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
    result = get_supabase_client().table("traceability_events").insert(payload).execute()
    return _first_row(result, payload)


def get_lots(limit: int = 100) -> list[dict]:
    result = (
        get_supabase_client().table("lots").select("*")
        .order("created_at", desc=True).limit(max(1, int(limit))).execute()
    )
    return result.data or []


def get_risk_assessments(batch_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    query = (
        get_supabase_client().table("risk_assessments").select("*")
        .order("analysis_date", desc=True).limit(max(1, int(limit)))
    )
    if batch_id:
        query = query.eq("batch_id", str(batch_id).strip())
    result = query.execute()
    return result.data or []


def get_research_observations(limit: int = 500) -> list[dict]:
    result = (
        get_supabase_client().table("research_observations").select("*")
        .order("created_at", desc=True).limit(max(1, int(limit))).execute()
    )
    return result.data or []


def get_traceability_events(batch_id: str, limit: int = 200) -> list[dict]:
    if not batch_id:
        raise ValueError("batch_id is required.")
    result = (
        get_supabase_client().table("traceability_events").select("*")
        .eq("batch_id", str(batch_id).strip())
        .order("event_date", desc=True).limit(max(1, int(limit))).execute()
    )
    return result.data or []
