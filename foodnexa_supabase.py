"""
FOODNEXA Supabase connector aligned with the five verified public tables.
No destructive operations are performed.
"""
from __future__ import annotations

from functools import lru_cache
from math import isfinite
from numbers import Real
from typing import Any, Optional
from uuid import uuid4
import json

import streamlit as st
from supabase import Client, create_client

TABLE_RESEARCH = "research_observations"
TABLE_RISK = "risk_assessments"
TABLE_PROFILES = "foodnexa_product_profiles"
TABLE_TRACEABILITY = "foodnexa_traceability_batches"
TABLE_LAB = "foodnexa_lab_results"


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        url = key = None
    if not url or not key:
        raise RuntimeError(
            "Configuration Supabase absente. Vérifiez SUPABASE_URL et SUPABASE_KEY "
            "dans Streamlit Cloud → Settings → Secrets."
        )
    return create_client(str(url).strip(), str(key).strip())


def _clean_value(value: Any) -> Any:
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
        return [_clean_value(v) for v in value]
    if value.__class__.__name__ in {"NAType", "NaTType"}:
        return None
    return value


def _clean_record(record: dict) -> dict:
    return {str(k): _clean_value(v) for k, v in record.items()}


def _first_row(result: Any, fallback: dict) -> dict:
    data = getattr(result, "data", None) or []
    return data[0] if data else fallback


def _text_value(value: Any) -> Optional[str]:
    value = _clean_value(value)
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def register_lot(batch_id: str, product_name: str, status: str = "En attente") -> dict:
    """Compatibility helper backed by the real traceability table."""
    code = str(batch_id or "").strip()
    product = str(product_name or "").strip()
    if not code or not product:
        raise ValueError("batch_id et product_name sont obligatoires.")
    payload = {
        "batch_code": code,
        "product_name": product,
        "current_status": status or "En attente",
    }
    result = (
        get_supabase_client()
        .table(TABLE_TRACEABILITY)
        .upsert(payload, on_conflict="batch_code")
        .execute()
    )
    return _first_row(result, payload)


def save_risk_assessment(
    batch_id: str,
    product_name: str,
    risk_score: Optional[float],
    risk_level: Optional[str],
    confidence: Optional[float] = None,
    inputs: Optional[dict] = None,
    factor_scores: Optional[dict] = None,
    reasons: Optional[list] = None,
    recommendations: Optional[list] = None,
    data_completeness: Optional[float] = None,
    analysis_status: str = "Complete",
) -> dict:
    code = str(batch_id or "").strip()
    product = str(product_name or "").strip()
    if not code or not product:
        raise ValueError("batch_id et product_name sont obligatoires.")

    # Best-effort lot registration. Risk persistence must not depend on it.
    try:
        register_lot(code, product)
    except Exception:
        pass

    # The verified risk_assessments table has no product_name column.
    payload = _clean_record({
        "batch_id": code,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "confidence": confidence,
        "data_completeness": data_completeness,
        "analysis_status": analysis_status,
        "inputs": inputs or {},
        "factor_scores": factor_scores or {},
        "reasons": reasons or [],
        "recommendations": recommendations or [],
    })
    result = get_supabase_client().table(TABLE_RISK).insert(payload).execute()
    return _first_row(result, payload)


def save_research_observation(observation: dict) -> dict:
    """Insert one distinct observation; do not upsert by batch_id."""
    if not isinstance(observation, dict):
        raise TypeError("observation doit être un dictionnaire.")
    item = _clean_record(observation)
    batch_code = str(item.get("batch_id") or "").strip()
    if not batch_code:
        raise ValueError("Research observation requires batch_id.")

    allowed = {
        "observation_id", "traceability_batch_id", "batch_id", "product_name",
        "temperature_celsius", "storage_days", "ph", "cold_chain_broken",
        "hygiene_controlled", "pasteurized", "total_viable_count",
        "enterobacteriaceae_count", "coliform_count",
        "staphylococcus_aureus_count", "salmonella_detected", "sensory_status",
        "nonconformity_detected", "expert_risk_label", "product_category",
        "sample_reference", "supplier", "sampling_date", "analysis_date",
        "laboratory", "analyst", "process_data", "physicochemical_results",
        "microbiological_results", "contaminant_results", "sensory_results",
        "packaging_results", "analysis_units", "analysis_methods",
        "applicable_limits_reference", "notes",
    }
    payload = {k: v for k, v in item.items() if k in allowed}
    payload["batch_id"] = batch_code
    payload["observation_id"] = str(item.get("observation_id") or uuid4())
    if item.get("traceability_batch_id"):
        payload["traceability_batch_id"] = str(item["traceability_batch_id"])

    # These six columns are NOT NULL JSONB objects in the verified schema.
    for field in (
        "process_data", "physicochemical_results", "microbiological_results",
        "contaminant_results", "sensory_results", "packaging_results",
    ):
        value = payload.get(field)
        if value is None:
            payload[field] = {}
        elif not isinstance(value, dict):
            raise TypeError(f"{field} doit être un objet JSON (dictionnaire).")

    # The verified schema defines these two columns as TEXT, not JSONB.
    for field in ("analysis_units", "analysis_methods"):
        if field in payload:
            payload[field] = _text_value(payload[field])

    result = get_supabase_client().table(TABLE_RESEARCH).insert(payload).execute()
    return _first_row(result, payload)


def save_research_dataset(records: list[dict]) -> int:
    count = 0
    for record in records or []:
        save_research_observation(record)
        count += 1
    return count


def get_lots(limit: int = 100) -> list[dict]:
    """Legacy app API, now reading the current traceability register."""
    result = (
        get_supabase_client()
        .table(TABLE_TRACEABILITY)
        .select("*")
        .order("created_at", desc=True)
        .limit(max(1, int(limit)))
        .execute()
    )
    return result.data or []


def get_risk_assessments(batch_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    query = (
        get_supabase_client()
        .table(TABLE_RISK)
        .select("*")
        .order("analysis_date", desc=True)
        .limit(max(1, int(limit)))
    )
    if batch_id:
        query = query.eq("batch_id", str(batch_id).strip())
    return query.execute().data or []


def get_all_risk_assessments(page_size: int = 500, max_records: int = 20000) -> list[dict]:
    page_size = max(1, min(int(page_size), 1000))
    max_records = max(1, int(max_records))
    client = get_supabase_client()
    rows, start = [], 0
    while len(rows) < max_records:
        end = min(start + page_size - 1, max_records - 1)
        page = (
            client.table(TABLE_RISK).select("*")
            .order("analysis_date", desc=True).range(start, end).execute().data or []
        )
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows[:max_records]


def get_research_observations(limit: int = 500) -> list[dict]:
    result = (
        get_supabase_client().table(TABLE_RESEARCH).select("*")
        .order("created_at", desc=True).limit(max(1, int(limit))).execute()
    )
    return result.data or []


def get_all_research_observations(page_size: int = 500, max_records: int = 20000) -> list[dict]:
    page_size = max(1, min(int(page_size), 1000))
    max_records = max(1, int(max_records))
    client = get_supabase_client()
    rows, start = [], 0
    while len(rows) < max_records:
        end = min(start + page_size - 1, max_records - 1)
        page = (
            client.table(TABLE_RESEARCH).select("*")
            .order("created_at", desc=True).range(start, end).execute().data or []
        )
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows[:max_records]


def add_traceability_event(
    batch_id: str,
    event_type: str,
    event_description: str = "",
    responsible_person: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Append an event to the events JSONB array on the matching traceability lot."""
    code, kind = str(batch_id or "").strip(), str(event_type or "").strip()
    if not code or not kind:
        raise ValueError("batch_id et event_type sont obligatoires.")
    client = get_supabase_client()
    found = (
        client.table(TABLE_TRACEABILITY).select("id,events")
        .eq("batch_code", code).limit(1).execute().data or []
    )
    if not found:
        raise ValueError(f"Lot introuvable dans la traçabilité : {code}")
    events = found[0].get("events") or []
    if not isinstance(events, list):
        events = []
    events.append(_clean_record({
        "event_id": str(uuid4()),
        "event_type": kind,
        "event_description": event_description,
        "responsible_person": responsible_person,
        "metadata": metadata or {},
    }))
    result = (
        client.table(TABLE_TRACEABILITY).update({"events": events})
        .eq("id", found[0]["id"]).execute()
    )
    return _first_row(result, {"batch_code": code, "events": events})


def get_traceability_events(batch_id: str, limit: int = 200) -> list[dict]:
    code = str(batch_id or "").strip()
    if not code:
        raise ValueError("batch_id est obligatoire.")
    rows = (
        get_supabase_client().table(TABLE_TRACEABILITY).select("events")
        .eq("batch_code", code).limit(1).execute().data or []
    )
    if not rows:
        return []
    events = rows[0].get("events") or []
    return list(reversed(events[-max(1, int(limit)):])) if isinstance(events, list) else []


def test_supabase_connection() -> dict:
    """Read-only check of all five verified FOODNEXA tables."""
    client = get_supabase_client()
    tables = (
        TABLE_RESEARCH, TABLE_RISK, TABLE_PROFILES, TABLE_TRACEABILITY, TABLE_LAB
    )
    total_rows = 0
    for table in tables:
        result = client.table(table).select("id").limit(1).execute()
        total_rows += len(result.data or [])
    return {
        "connected": True,
        "rows_returned": total_rows,
        "tables_checked": list(tables),
        "tables_count": len(tables),
    }
