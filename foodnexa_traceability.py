"""FOODNEXA Batch Traceability V22.

Operational lot register and traceability event log. This module records
information supplied by users; it does not certify legal compliance or
replace a validated recall procedure.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

TABLE_NAME = "foodnexa_traceability_batches"
LOCAL_FILE = Path("foodnexa_traceability.json")
EVENT_TYPES = [
    "Création du lot", "Réception", "Contrôle qualité", "Stockage",
    "Transfert", "Transformation", "Expédition", "Livraison",
    "Blocage / quarantaine", "Libération", "Autre",
]
STATUSES = ["En attente", "En stock", "En cours de contrôle", "Libéré", "Bloqué / quarantaine", "Expédié", "Clôturé"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_events(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = []
    if not isinstance(value, list):
        return []
    return [dict(x) for x in value if isinstance(x, dict)]


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["id"] = str(item.get("id") or uuid.uuid4())
    item["events"] = _safe_events(item.get("events"))
    for key in (
        "product_profile_id", "product_name", "product_category", "supplier_name",
        "supplier_batch_code", "origin_country", "quantity", "quantity_unit", "receiving_temperature_c",
        "destination", "storage_conditions", "current_status", "notes",
        "created_at", "updated_at",
    ):
        item.setdefault(key, "")
    for date_key in ("received_date", "production_date", "expiry_date"):
        item.setdefault(date_key, None)
    item.setdefault("current_status", "En attente")
    item.setdefault("created_at", _now())
    item.setdefault("updated_at", _now())
    return item


def _local_read() -> list[dict[str, Any]]:
    if not LOCAL_FILE.exists():
        return []
    try:
        raw = json.loads(LOCAL_FILE.read_text(encoding="utf-8"))
        rows = raw.get("batches", []) if isinstance(raw, dict) else raw
        return [_normalize(x) for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
    except Exception:
        return []


def _local_write(rows: list[dict[str, Any]]) -> None:
    LOCAL_FILE.write_text(json.dumps({"version": 1, "batches": rows}, ensure_ascii=False, indent=2), encoding="utf-8")


def _client():
    try:
        url, key = st.secrets.get("SUPABASE_URL"), st.secrets.get("SUPABASE_KEY")
    except Exception:
        url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(str(url), str(key))
    except Exception:
        return None


def load_batches() -> tuple[list[dict[str, Any]], str, str | None]:
    client = _client()
    if client:
        try:
            response = client.table(TABLE_NAME).select("*").order("created_at", desc=True).execute()
            return [_normalize(x) for x in (response.data or [])], "Supabase", None
        except Exception as exc:
            return _local_read(), "JSON local (secours)", f"{type(exc).__name__}: vérifier la migration SQL V22 et les accès Supabase"
    return _local_read(), "JSON local", "Supabase non configuré pour le module de traçabilité."


def save_batch(batch: dict[str, Any]) -> tuple[bool, str, str | None]:
    item = _normalize(batch)
    item["updated_at"] = _now()
    client = _client()
    if client:
        try:
            client.table(TABLE_NAME).upsert(item, on_conflict="id").execute()
            current = [x for x in _local_read() if x["id"] != item["id"]]
            current.append(item)
            try:
                _local_write(current)
            except Exception:
                pass
            return True, "Supabase", None
        except Exception as exc:
            error = f"{type(exc).__name__}: migration SQL V22 ou accès à vérifier"
    else:
        error = "Supabase non configuré; sauvegarde locale uniquement."
    current = [x for x in _local_read() if x["id"] != item["id"]]
    current.append(item)
    try:
        _local_write(current)
        return True, "JSON local", error
    except Exception as exc:
        return False, "Aucun stockage", f"{type(exc).__name__}: {exc}"


def _date_text(value: str) -> str | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError("Les dates doivent être au format AAAA-MM-JJ.")


def _completeness(batch: dict[str, Any]) -> tuple[int, int]:
    required = ["batch_code", "product_name", "supplier_name", "supplier_batch_code", "received_date", "destination"]
    return sum(bool(str(batch.get(k, "")).strip()) for k in required), len(required)


def _batch_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Code lot": x.get("batch_code", ""),
        "Produit": x.get("product_name", ""),
        "Fournisseur": x.get("supplier_name", ""),
        "Lot fournisseur": x.get("supplier_batch_code", ""),
        "Réception": x.get("received_date", ""),
        "Expiration": x.get("expiry_date", ""),
        "Statut": x.get("current_status", ""),
        "Événements": len(x.get("events", [])),
    } for x in rows])


def render_traceability() -> None:
    from foodnexa_product_library import CATEGORIES, load_profiles

    batches, storage_mode, storage_error = load_batches()
    profiles, _, _ = load_profiles()
    st.title("🔗 Batch Traceability")
    st.caption("Registre des lots, fournisseurs, mouvements et événements de traçabilité.")
    st.info("Ce module conserve les informations déclarées par l'utilisateur. Il aide à retrouver les lots et leurs événements, mais ne constitue pas à lui seul une procédure de rappel validée ni une preuve de conformité réglementaire.")

    total_events = sum(len(x.get("events", [])) for x in batches)
    blocked = sum(x.get("current_status") == "Bloqué / quarantaine" for x in batches)
    suppliers = len({str(x.get("supplier_name", "")).strip().lower() for x in batches if str(x.get("supplier_name", "")).strip()})
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Lots enregistrés", len(batches))
    k2.metric("Fournisseurs", suppliers)
    k3.metric("Événements", total_events)
    k4.metric("Lots bloqués", blocked)
    st.caption(f"Stockage : **{storage_mode}**")
    if storage_error:
        st.warning(storage_error + " Une sauvegarde JSON locale est utilisée si possible; sur Streamlit Cloud, appliquer la migration V22 pour une conservation durable.")

    tab_overview, tab_new, tab_detail, tab_search = st.tabs(["Vue d'ensemble", "Enregistrer un lot", "Détail & événements", "Recherche / traçabilité"])

    with tab_overview:
        st.subheader("Registre des lots")
        if batches:
            st.dataframe(_batch_frame(batches), use_container_width=True, hide_index=True)
            export = pd.DataFrame([{
                **{k: v for k, v in x.items() if k != "events"},
                "events_json": json.dumps(x.get("events", []), ensure_ascii=False),
            } for x in batches]).to_csv(index=False).encode("utf-8-sig")
            st.download_button("Télécharger le registre CSV", export, "foodnexa_traceability_register.csv", "text/csv")
        else:
            st.info("Aucun lot enregistré. Créez le premier lot dans l'onglet Enregistrer un lot.")

    with tab_new:
        st.subheader("Créer une fiche de lot")
        profile_labels = {str(p.get("id")): f"{p.get('product_name', 'Produit')} — {p.get('product_category', '')}" for p in profiles}
        with st.form("fnx_trace_new_batch", clear_on_submit=True):
            profile_options = [""] + list(profile_labels.keys())
            selected_profile = st.selectbox("Profil produit (facultatif)", profile_options, format_func=lambda x: "Sans profil lié" if not x else profile_labels.get(x, x))
            if not selected_profile:
                manual_product_name = st.text_input("Nom du produit *")
                manual_product_category = st.selectbox("Catégorie du produit", CATEGORIES)
            else:
                manual_product_name = ""
                manual_product_category = ""
            col1, col2 = st.columns(2)
            batch_code = col1.text_input("Code lot FOODNEXA *", placeholder="Ex. LOT-2026-001")
            supplier = col2.text_input("Fournisseur *")
            supplier_batch = col1.text_input("Code lot fournisseur *")
            origin = col2.text_input("Origine / pays")
            received = col1.text_input("Date de réception (AAAA-MM-JJ) *", placeholder="2026-11-17")
            production = col2.text_input("Date de production (AAAA-MM-JJ)", placeholder="2026-11-16")
            expiry = col1.text_input("Date limite / expiration (AAAA-MM-JJ)", placeholder="2026-11-30")
            destination = col2.text_input("Destination / site de stockage *")
            q1, q2 = st.columns(2)
            quantity = q1.number_input("Quantité", min_value=0.0, value=0.0, step=1.0)
            unit = q2.selectbox("Unité", ["kg", "g", "L", "mL", "unités", "cartons", "palettes", "Autre"])
            temp = st.text_input("Température à réception (°C)", placeholder="Ex. 4.0")
            storage = st.text_input("Conditions de stockage", placeholder="Ex. Réfrigéré — consigne documentée")
            status = st.selectbox("Statut initial", STATUSES, index=0)
            notes = st.text_area("Notes / référence documentaire", height=80)
            submitted = st.form_submit_button("Enregistrer le lot", type="primary", use_container_width=True)
        if submitted:
            try:
                if not batch_code.strip() or not supplier.strip() or not supplier_batch.strip() or not received.strip() or not destination.strip() or (not selected_profile and not manual_product_name.strip()):
                    st.error("Complétez les champs obligatoires marqués *.")
                elif any(str(x.get("batch_code", "")).strip().lower() == batch_code.strip().lower() for x in batches):
                    st.error("Ce code lot FOODNEXA existe déjà. Utilisez un code unique.")
                else:
                    profile = next((p for p in profiles if str(p.get("id")) == selected_profile), None)
                    if temp.strip():
                        float(temp)
                    item = {
                        "id": str(uuid.uuid4()), "batch_code": batch_code.strip(),
                        "product_profile_id": selected_profile or "",
                        "product_name": profile.get("product_name", "") if profile else manual_product_name.strip(),
                        "product_category": profile.get("product_category", "") if profile else manual_product_category,
                        "supplier_name": supplier.strip(), "supplier_batch_code": supplier_batch.strip(),
                        "origin_country": origin.strip(), "received_date": _date_text(received),
                        "production_date": _date_text(production), "expiry_date": _date_text(expiry),
                        "quantity": quantity, "quantity_unit": unit,
                        "receiving_temperature_c": temp.strip(), "destination": destination.strip(),
                        "storage_conditions": storage.strip(), "current_status": status,
                        "notes": notes.strip(),
                        "events": [{"event_id": str(uuid.uuid4()), "event_type": "Création du lot", "event_date": _now(), "location": destination.strip(), "actor": "Utilisateur FOODNEXA", "notes": "Fiche de lot créée."}],
                    }
                    ok, backend, error = save_batch(item)
                    if ok:
                        st.success(f"Lot enregistré dans {backend}.")
                        if error:
                            st.warning(error)
                        st.rerun()
                    else:
                        st.error(f"Échec de sauvegarde : {error}")
            except ValueError as exc:
                st.error(str(exc) if "AAAA-MM-JJ" in str(exc) else "Valeur numérique ou date invalide. Vérifiez les champs.")

    with tab_detail:
        st.subheader("Consulter un lot et ajouter un événement")
        if not batches:
            st.info("Enregistrez un lot pour activer cette section.")
        else:
            ids = [x["id"] for x in batches]
            chosen = st.selectbox("Sélectionner le lot", ids, format_func=lambda x: next((f"{b.get('batch_code')} — {b.get('product_name')}" for b in batches if b["id"] == x), x), key="fnx_trace_detail_id")
            item = next(x for x in batches if x["id"] == chosen)
            filled, total = _completeness(item)
            st.markdown(f"#### {item.get('batch_code')} — {item.get('product_name')}")
            st.progress(filled / total, text=f"Complétude des champs de traçabilité : {filled}/{total} ({round(filled / total * 100)}%) — indicateur documentaire, pas un score de conformité")
            a, b, c = st.columns(3)
            a.write(f"**Fournisseur :** {item.get('supplier_name') or '—'}")
            b.write(f"**Lot fournisseur :** {item.get('supplier_batch_code') or '—'}")
            c.write(f"**Statut :** {item.get('current_status') or '—'}")
            a.write(f"**Réception :** {item.get('received_date') or '—'}")
            b.write(f"**Expiration :** {item.get('expiry_date') or '—'}")
            c.write(f"**Destination :** {item.get('destination') or '—'}")
            st.markdown("##### Historique chronologique")
            events = sorted(item.get("events", []), key=lambda e: str(e.get("event_date", "")))
            if events:
                st.dataframe(pd.DataFrame([{"Date / heure": e.get("event_date", ""), "Événement": e.get("event_type", ""), "Lieu": e.get("location", ""), "Responsable": e.get("actor", ""), "Notes": e.get("notes", "")} for e in events]), use_container_width=True, hide_index=True)
            else:
                st.caption("Aucun événement supplémentaire.")
            with st.form("fnx_trace_add_event"):
                st.markdown("##### Ajouter un événement")
                e1, e2 = st.columns(2)
                event_type = e1.selectbox("Type d'événement", EVENT_TYPES)
                new_status = e2.selectbox("Nouveau statut", ["Ne pas modifier"] + STATUSES)
                location = st.text_input("Lieu / site")
                actor = st.text_input("Responsable / opérateur")
                event_temp = st.text_input("Température observée (°C), si pertinente")
                event_notes = st.text_area("Détails / référence", height=70)
                add_event = st.form_submit_button("Ajouter à l'historique", use_container_width=True)
            if add_event:
                if event_temp.strip():
                    try:
                        float(event_temp)
                    except ValueError:
                        st.error("La température doit être numérique.")
                        st.stop()
                new_event = {"event_id": str(uuid.uuid4()), "event_type": event_type, "event_date": _now(), "location": location.strip(), "actor": actor.strip(), "temperature_c": event_temp.strip(), "notes": event_notes.strip()}
                item["events"] = item.get("events", []) + [new_event]
                if new_status != "Ne pas modifier":
                    item["current_status"] = new_status
                ok, backend, error = save_batch(item)
                if ok:
                    st.success(f"Événement ajouté et enregistré dans {backend}.")
                    if error:
                        st.warning(error)
                    st.rerun()
                else:
                    st.error(f"Enregistrement impossible : {error}")

    with tab_search:
        st.subheader("Recherche et périmètre de traçabilité")
        query = st.text_input("Rechercher par code lot, produit, fournisseur ou lot fournisseur", key="fnx_trace_search")
        status_filter = st.selectbox("Filtrer par statut", ["Tous"] + STATUSES, key="fnx_trace_status_filter")
        filtered = [x for x in batches if (status_filter == "Tous" or x.get("current_status") == status_filter)]
        if query.strip():
            q = query.strip().lower()
            filtered = [x for x in filtered if any(q in str(x.get(k, "")).lower() for k in ("batch_code", "product_name", "supplier_name", "supplier_batch_code", "origin_country", "destination"))]
        st.caption(f"Résultats : {len(filtered)} lot(s)")
        if filtered:
            st.dataframe(_batch_frame(filtered), use_container_width=True, hide_index=True)
            st.download_button("Exporter les résultats de recherche", _batch_frame(filtered).to_csv(index=False).encode("utf-8-sig"), "foodnexa_traceability_search.csv", "text/csv")
        else:
            st.info("Aucun lot correspondant aux filtres.")

    st.divider()
    st.caption("FOODNEXA V22 — Traçabilité opérationnelle. La qualité des données dépend des informations et justificatifs saisis par les utilisateurs.")
