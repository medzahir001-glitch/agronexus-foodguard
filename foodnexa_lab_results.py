"""FOODNEXA V23 — Laboratory Results Management.
Records measured laboratory observations and links them to traceability batches.
A blank/not-tested result is never interpreted as zero or a negative result.
"""
from __future__ import annotations
import json, os, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import streamlit as st

TABLE_NAME = "foodnexa_lab_results"
LOCAL_FILE = Path("foodnexa_lab_results.json")
TEST_GROUPS = ["Physico-chimique", "Microbiologique", "Contaminants", "Sensoriel", "Autre"]
RESULT_TYPES = ["Quantitatif", "Qualitatif", "Présence / Absence", "Non testé"]
STATUSES = ["À examiner", "Conforme selon la référence saisie", "Non conforme selon la référence saisie", "Résultat suspect / à confirmer", "Non applicable"]


def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _client():
    try: url, key = st.secrets.get("SUPABASE_URL"), st.secrets.get("SUPABASE_KEY")
    except Exception: url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not key: return None
    try:
        from supabase import create_client
        return create_client(str(url), str(key))
    except Exception: return None

def _normalize(x: dict[str, Any]):
    r = dict(x)
    for k in ("id", "batch_id", "batch_code", "product_name", "test_group", "test_name", "result_type", "result_value", "unit", "qualitative_result", "method_name", "method_reference", "laboratory_name", "analyst_name", "sample_reference", "sampling_date", "analysis_date", "detection_limit", "quantification_limit", "measurement_uncertainty", "reference_source", "reference_clause", "interpretation_status", "comments", "created_at"):
        r.setdefault(k, "")
    return r

def _local_read():
    try:
        raw = json.loads(LOCAL_FILE.read_text(encoding="utf-8"))
        rows = raw.get("results", []) if isinstance(raw, dict) else raw
        return [_normalize(x) for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
    except Exception: return []

def _local_write(rows):
    LOCAL_FILE.write_text(json.dumps({"version": 1, "results": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

def load_results():
    c = _client()
    if c:
        try:
            res = c.table(TABLE_NAME).select("*").order("created_at", desc=True).execute()
            return [_normalize(x) for x in (res.data or [])], "Supabase", None
        except Exception as e:
            return _local_read(), "JSON local (secours)", f"{type(e).__name__}: vérifier la migration SQL V23 et les permissions Supabase."
    return _local_read(), "JSON local", "Supabase non configuré pour les résultats de laboratoire."

def save_result(item):
    item = _normalize(item); item["updated_at"] = _now()
    c = _client(); error = None
    if c:
        try:
            c.table(TABLE_NAME).upsert(item, on_conflict="id").execute()
            rows = [x for x in _local_read() if x.get("id") != item["id"]] + [item]
            try: _local_write(rows)
            except Exception: pass
            return True, "Supabase", None
        except Exception as e: error = f"{type(e).__name__}: migration SQL V23 ou permissions à vérifier."
    else: error = "Supabase non configuré; sauvegarde locale uniquement."
    rows = [x for x in _local_read() if x.get("id") != item["id"]] + [item]
    try:
        _local_write(rows); return True, "JSON local", error
    except Exception as e: return False, "Aucun stockage", f"{type(e).__name__}: {e}"

def _frame(rows):
    return pd.DataFrame([{
        "Date analyse": r.get("analysis_date", ""), "Code lot": r.get("batch_code", ""),
        "Produit": r.get("product_name", ""), "Groupe": r.get("test_group", ""),
        "Analyse": r.get("test_name", ""), "Type résultat": r.get("result_type", ""),
        "Résultat": r.get("result_value", "") if r.get("result_type") == "Quantitatif" else r.get("qualitative_result", ""),
        "Unité": r.get("unit", ""), "Laboratoire": r.get("laboratory_name", ""),
        "Statut saisi": r.get("interpretation_status", ""),
    } for r in rows])

def render_lab_results():
    from foodnexa_traceability import load_batches
    batches, batch_storage, batch_error = load_batches()
    rows, storage, error = load_results()
    st.title("🧫 Laboratory Results Management")
    st.caption("Gestion des résultats d'analyses, méthodes, unités, laboratoires et rattachement aux lots FOODNEXA.")
    st.warning("Saisissez uniquement les résultats réellement mesurés. « Non testé », une valeur vide, zéro et un résultat négatif sont des états différents. Le statut d'interprétation est déclaré par l'utilisateur et ne constitue pas une validation réglementaire automatique.")
    linked_ids = {str(x.get("batch_id")) for x in rows if x.get("batch_id")}
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Résultats enregistrés", len(rows)); c2.metric("Lots disponibles", len(batches)); c3.metric("Lots avec analyses", len(linked_ids)); c4.metric("Laboratoires", len({str(x.get('laboratory_name')).strip().lower() for x in rows if x.get('laboratory_name')}))
    st.caption(f"Stockage résultats : **{storage}** · Traçabilité : **{batch_storage}**")
    if error: st.info(error)
    if batch_error: st.caption(batch_error)
    tab_add, tab_view, tab_search = st.tabs(["Ajouter un résultat", "Registre laboratoire", "Recherche / export"])
    with tab_add:
        st.subheader("Nouvelle fiche de résultat")
        opts = [""] + [str(b.get("id")) for b in batches]
        labels = {str(b.get("id")): f"{b.get('batch_code','')} — {b.get('product_name','')} ({b.get('current_status','')})" for b in batches}
        with st.form("fnx_lab_result_add", clear_on_submit=True):
            batch_id = st.selectbox("Lot FOODNEXA lié (recommandé)", opts, format_func=lambda v: "Aucun lot lié" if not v else labels.get(v,v))
            batch = next((b for b in batches if str(b.get("id")) == batch_id), {})
            if not batches: st.caption("Aucun lot V22 disponible. Vous pouvez enregistrer un résultat sans rattachement, ou créer d'abord un lot dans Batch Traceability.")
            p1,p2 = st.columns(2)
            product_manual = p1.text_input("Produit si aucun lot lié", value="" if batch_id else "")
            sample_ref = p2.text_input("Référence échantillon")
            p1,p2 = st.columns(2)
            group = p1.selectbox("Famille d'analyse", TEST_GROUPS)
            test_name = p2.text_input("Paramètre / analyse *", placeholder="Ex. Flore aérobie mésophile")
            p1,p2 = st.columns(2)
            result_type = p1.selectbox("Type de résultat", RESULT_TYPES)
            unit = p2.text_input("Unité", placeholder="UFC/g, mg/kg, pH…")
            numeric_value = None; qualitative = ""
            if result_type == "Quantitatif":
                numeric_value = st.number_input("Valeur mesurée", value=None, format="%.8g", placeholder="Saisir une valeur réellement mesurée", help="Le champ reste vide tant qu’aucune mesure n’est saisie. Zéro doit être saisi explicitement s’il s’agit du résultat mesuré.")
            elif result_type == "Qualitatif": qualitative = st.text_input("Résultat qualitatif", placeholder="Ex. Couleur jaune pâle")
            elif result_type == "Présence / Absence": qualitative = st.selectbox("Résultat", ["Sélectionner…", "Présence", "Absence", "Indéterminé"], index=0)
            else: st.caption("Aucune valeur ne sera enregistrée pour un test non réalisé.")
            p1,p2 = st.columns(2)
            lab = p1.text_input("Laboratoire")
            analyst = p2.text_input("Analyste")
            p1,p2 = st.columns(2)
            sampling_date = p1.text_input("Date de prélèvement (AAAA-MM-JJ)", placeholder="2026-11-17")
            analysis_date = p2.text_input("Date d'analyse (AAAA-MM-JJ)", placeholder="2026-11-17")
            method = st.text_input("Méthode d'analyse / équipement")
            method_ref = st.text_input("Référence de méthode (ISO, NM, interne…)")
            p1,p2 = st.columns(2)
            lod = p1.text_input("Limite de détection (LOD)")
            loq = p2.text_input("Limite de quantification (LOQ)")
            uncertainty = st.text_input("Incertitude de mesure")
            p1,p2 = st.columns(2)
            ref_source = p1.text_input("Source de la référence / spécification")
            ref_clause = p2.text_input("Clause / article / version")
            status = st.selectbox("Interprétation déclarée", STATUSES)
            comments = st.text_area("Commentaires / observations", height=80)
            submitted = st.form_submit_button("Enregistrer le résultat", type="primary", use_container_width=True)
        if submitted:
            if not test_name.strip():
                st.error("Le nom du paramètre / de l'analyse est obligatoire.")
            elif not batch_id and not product_manual.strip():
                st.error("Sélectionnez un lot ou renseignez le nom du produit.")
            elif result_type == "Quantitatif" and numeric_value is None:
                st.error("Aucune valeur quantitative saisie. Laissez le type sur « Non testé » si l'analyse n'a pas été réalisée.")
            elif result_type == "Quantitatif" and not unit.strip():
                st.error("L'unité est obligatoire pour un résultat quantitatif. Pour le pH, indiquez par exemple « sans unité ».")
            elif result_type == "Qualitatif" and not qualitative.strip():
                st.error("Saisissez le résultat qualitatif, ou choisissez Non testé.")
            elif result_type == "Présence / Absence" and qualitative == "Sélectionner…":
                st.error("Choisissez Présence, Absence ou Indéterminé; sinon sélectionnez Non testé.")
            else:
                from datetime import date
                try:
                    parsed_sampling = date.fromisoformat(sampling_date.strip()) if sampling_date.strip() else None
                    parsed_analysis = date.fromisoformat(analysis_date.strip()) if analysis_date.strip() else None
                    if parsed_sampling and parsed_analysis and parsed_analysis < parsed_sampling:
                        raise ValueError("La date d'analyse ne peut pas précéder la date de prélèvement.")
                    item = {
                        "id": str(uuid.uuid4()), "batch_id": batch_id or None,
                        "batch_code": batch.get("batch_code", "") if batch else "",
                        "product_name": batch.get("product_name", "") if batch else product_manual.strip(),
                        "test_group": group, "test_name": test_name.strip(), "result_type": result_type,
                        "result_value": float(numeric_value) if result_type == "Quantitatif" else None,
                        "unit": unit.strip(), "qualitative_result": "" if result_type == "Non testé" else qualitative.strip(),
                        "laboratory_name": lab.strip(), "analyst_name": analyst.strip(), "sample_reference": sample_ref.strip(),
                        "sampling_date": sampling_date.strip() or None, "analysis_date": analysis_date.strip() or None,
                        "method_name": method.strip(), "method_reference": method_ref.strip(),
                        "detection_limit": lod.strip(), "quantification_limit": loq.strip(), "measurement_uncertainty": uncertainty.strip(),
                        "reference_source": ref_source.strip(), "reference_clause": ref_clause.strip(),
                        "interpretation_status": "Non applicable" if result_type == "Non testé" else status,
                        "comments": comments.strip(), "created_at": _now(),
                    }
                    ok, mode, err = save_result(item)
                    if ok:
                        st.success(f"Résultat enregistré ({mode}).")
                        if err: st.warning(err)
                        st.rerun()
                    else: st.error(err or "Échec de l'enregistrement.")
                except ValueError as exc:
                    st.error(str(exc) or "Les dates doivent respecter le format AAAA-MM-JJ.")
    with tab_view:
        st.subheader("Registre des résultats")
        if rows:
            st.dataframe(_frame(rows), use_container_width=True, hide_index=True)
            csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button("Exporter tous les résultats (CSV)", csv, "foodnexa_lab_results.csv", "text/csv")
        else: st.info("Aucun résultat laboratoire enregistré pour le moment.")
    with tab_search:
        term = st.text_input("Rechercher par lot, produit, analyse, laboratoire ou échantillon")
        filtered = [r for r in rows if not term.strip() or term.lower() in " ".join(str(r.get(k,"")) for k in ("batch_code","product_name","test_name","laboratory_name","sample_reference")).lower()]
        st.write(f"{len(filtered)} résultat(s)")
        if filtered:
            st.dataframe(_frame(filtered), use_container_width=True, hide_index=True)
            data = pd.DataFrame(filtered).to_csv(index=False).encode("utf-8-sig")
            st.download_button("Exporter la recherche CSV", data, "foodnexa_lab_results_filtered.csv", "text/csv")
