"""
FOODNEXA - Interactive Streamlit Dashboard
Replacement for the static HTML/iframe dashboard.

Keeps the existing app.py contract:
render_dashboard(history_data, research_data, quality_report, pipeline_status)

This module only reads the supplied data. It does not modify CSV or Supabase records.
"""

import math
import pandas as pd
import streamlit as st


def _frame(value):
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value.copy()
    try:
        return pd.DataFrame(value)
    except Exception:
        return pd.DataFrame()


def _find_column(frame, candidates):
    if frame.empty:
        return None
    lookup = {str(col).strip().casefold(): col for col in frame.columns}
    for candidate in candidates:
        found = lookup.get(candidate.casefold())
        if found is not None:
            return found
    return None


def _missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in {"", "nan", "none", "null", "n/a", "nat"}
    try:
        result = pd.isna(value)
        if getattr(result, "ndim", 0) == 0:
            return bool(result)
    except (TypeError, ValueError):
        pass
    return False


def _risk_label(value):
    if _missing(value):
        return "Non renseigné"
    raw = str(value).strip().casefold()
    if raw in {"faible", "low", "low risk", "faible risque"}:
        return "Faible"
    if raw in {"modéré", "modere", "moderate", "medium", "risque modéré"}:
        return "Modéré"
    if raw in {"élevé", "eleve", "high", "high risk", "risque élevé"}:
        return "Élevé"
    return str(value).strip()


def _quality_score(report):
    if not isinstance(report, dict):
        return None
    candidates = [
        report.get("quality_score"),
        report.get("overall_score"),
        report.get("score"),
        report.get("quality_percentage"),
    ]
    # Support a nested summary if the quality engine returns one.
    for key in ("summary", "metrics", "quality"):
        nested = report.get(key)
        if isinstance(nested, dict):
            candidates.extend([
                nested.get("quality_score"),
                nested.get("overall_score"),
                nested.get("score"),
                nested.get("quality_percentage"),
            ])
    for candidate in candidates:
        try:
            number = float(candidate)
            if math.isfinite(number):
                if 0 <= number <= 1:
                    number *= 100
                return max(0.0, min(100.0, number))
        except (TypeError, ValueError):
            continue
    return None


def _quality_issues(report):
    if not isinstance(report, dict):
        return []
    issues = report.get("issues", [])
    if isinstance(issues, dict):
        issues = list(issues.values())
    if not isinstance(issues, (list, tuple)):
        return []
    result = []
    for item in issues:
        if isinstance(item, dict):
            message = (
                item.get("message")
                or item.get("issue")
                or item.get("Problème")
                or item.get("type")
                or "Point à vérifier"
            )
        else:
            message = item
        if not _missing(message):
            result.append(str(message))
    return result[:15]


def _duplicates(frame):
    if frame.empty:
        return 0
    try:
        return int(frame.astype("string").fillna("").duplicated().sum())
    except Exception:
        return 0


def _category_series(research):
    if research.empty:
        return pd.Series(dtype="object")
    col = _find_column(
        research,
        ["product_category", "category", "product_name", "product"],
    )
    if col is None:
        return pd.Series(["Non classé"] * len(research), index=research.index)

    def classify(value):
        raw = "" if _missing(value) else str(value).casefold()
        if any(x in raw for x in ("dairy", "lait", "milk", "fromage", "yaourt")):
            return "Produits laitiers"
        if any(x in raw for x in ("vegetal", "végétal", "plant", "vegetable")):
            return "Produits végétaux"
        if any(x in raw for x in ("cereal", "céréale", "grain", "farine")):
            return "Céréales"
        if any(x in raw for x in ("meat", "viande", "beef", "poultry", "poulet")):
            return "Viandes"
        if any(x in raw for x in ("seafood", "fish", "poisson", "crustacé")):
            return "Produits de la mer"
        if any(x in raw for x in ("beverage", "boisson", "drink", "jus")):
            return "Boissons"
        return str(value).strip() if not _missing(value) else "Non renseigné"

    return research[col].map(classify)


def _prepare_history(history):
    result = history.copy()
    risk_col = _find_column(
        result,
        ["risk_level", "expert_risk_label", "risk_category", "predicted_risk"],
    )
    if risk_col is not None:
        result["_FOODNEXA_Risk"] = result[risk_col].map(_risk_label)
    else:
        score_col = _find_column(result, ["risk_score", "final_risk_score", "risk"])
        if score_col is not None:
            values = pd.to_numeric(result[score_col], errors="coerce")
            result["_FOODNEXA_Risk"] = values.map(
                lambda x: "Non renseigné" if pd.isna(x)
                else "Faible" if x < 34
                else "Modéré" if x < 67
                else "Élevé"
            )
        else:
            result["_FOODNEXA_Risk"] = "Non renseigné"
    return result


def _display_table(frame, columns, height=300):
    if frame.empty:
        st.info("Aucun enregistrement disponible pour le moment.")
        return
    available = [c for c in columns if c in frame.columns]
    if not available:
        available = list(frame.columns[:8])
    st.dataframe(
        frame[available],
        use_container_width=True,
        hide_index=True,
        height=height,
    )


def render_dashboard(
    history_data=None,
    research_data=None,
    quality_report=None,
    pipeline_status=None,
):
    """Render an interactive dashboard using native Streamlit components."""
    history = _prepare_history(_frame(history_data))
    research = _frame(research_data)

    st.title("📊 FOODNEXA Dashboard")
    st.caption(
        "Food Safety / Risk Intelligence — suivi des analyses, données de recherche "
        "et qualité du dataset."
    )

    # KPI calculations are based only on the supplied datasets.
    total_analyses = len(history)
    total_research = len(research)
    risk_counts = history["_FOODNEXA_Risk"].value_counts() if not history.empty else {}
    low = int(risk_counts.get("Faible", 0)) if hasattr(risk_counts, "get") else 0
    moderate = int(risk_counts.get("Modéré", 0)) if hasattr(risk_counts, "get") else 0
    high = int(risk_counts.get("Élevé", 0)) if hasattr(risk_counts, "get") else 0
    score = _quality_score(quality_report)
    duplicates = _duplicates(research)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total analyses", f"{total_analyses:,}")
    k2.metric("Research observations", f"{total_research:,}")
    k3.metric("Risques élevés", f"{high:,}")
    k4.metric("Data quality", f"{score:.1f}%" if score is not None else "N/D")

    st.divider()

    # Filters are real Streamlit controls and update the tables/charts below.
    st.subheader("🔎 Exploration interactive")
    f1, f2, f3 = st.columns([1, 1, 1.4])
    product_col = _find_column(
        history, ["product_name", "product", "product_category"]
    )
    product_options = []
    if product_col is not None and not history.empty:
        product_options = sorted(
            {str(v) for v in history[product_col].dropna().tolist() if str(v).strip()}
        )
    selected_product = f1.selectbox(
        "Produit (historique)",
        ["Tous"] + product_options,
        key="foodnexa_dashboard_product_filter",
    )
    risk_options = ["Tous", "Faible", "Modéré", "Élevé", "Non renseigné"]
    selected_risk = f2.selectbox(
        "Niveau de risque",
        risk_options,
        key="foodnexa_dashboard_risk_filter",
    )
    search_text = f3.text_input(
        "Recherche (lot, produit, analyste...)",
        key="foodnexa_dashboard_search",
        placeholder="Ex. LOT-001",
    )

    filtered_history = history.copy()
    if selected_product != "Tous" and product_col is not None:
        filtered_history = filtered_history[
            filtered_history[product_col].astype(str) == selected_product
        ]
    if selected_risk != "Tous":
        filtered_history = filtered_history[
            filtered_history["_FOODNEXA_Risk"] == selected_risk
        ]
    if search_text.strip():
        searchable = [
            c for c in filtered_history.columns
            if not str(c).startswith("_FOODNEXA_")
        ]
        mask = filtered_history[searchable].astype(str).apply(
            lambda col: col.str.contains(search_text.strip(), case=False, na=False)
        ).any(axis=1)
        filtered_history = filtered_history[mask]

    tab_overview, tab_history, tab_research, tab_system = st.tabs(
        ["Vue d’ensemble", "Historique des risques", "Research Dataset", "Qualité & système"]
    )

    with tab_overview:
        left, right = st.columns([1, 1.3])
        with left:
            st.markdown("#### Distribution des risques")
            if total_analyses:
                risk_chart = pd.DataFrame(
                    {"Nombre de lots": [low, moderate, high]},
                    index=["Faible", "Modéré", "Élevé"],
                )
                st.bar_chart(risk_chart, use_container_width=True)
                st.caption(
                    "Répartition calculée à partir du niveau de risque enregistré "
                    "dans l’historique."
                )
            else:
                st.info("Aucune analyse de risque enregistrée.")
        with right:
            st.markdown("#### Observations par catégorie")
            if not research.empty:
                categories = _category_series(research).value_counts()
                st.bar_chart(
                    categories.rename("Observations"),
                    use_container_width=True,
                )
            else:
                st.info("Aucune observation de recherche disponible.")

        st.markdown("#### Activité récente")
        date_col = _find_column(history, ["analysis_date", "created_at", "date"])
        batch_col = _find_column(history, ["batch_id", "sample_id", "sample_ref"])
        analyst_col = _find_column(history, ["analyst", "analyst_name", "operator"])
        display_cols = [
            c for c in [date_col, batch_col, product_col, analyst_col]
            if c is not None
        ]
        if not history.empty:
            recent = filtered_history.copy()
            if date_col is not None:
                recent["_sort_date"] = pd.to_datetime(
                    recent[date_col], errors="coerce", utc=True
                )
                recent = recent.sort_values(
                    "_sort_date", ascending=False, na_position="last"
                ).drop(columns=["_sort_date"])
            recent = recent.head(8).copy()
            recent["Niveau de risque"] = recent["_FOODNEXA_Risk"]
            _display_table(
                recent,
                display_cols + ["Niveau de risque"],
                height=290,
            )
        else:
            st.info("L’historique est vide.")

    with tab_history:
        st.markdown("#### Historique des évaluations")
        st.caption(
            f"{len(filtered_history)} résultat(s) après application des filtres."
        )
        if not filtered_history.empty:
            table = filtered_history.copy()
            table["Niveau de risque"] = table["_FOODNEXA_Risk"]
            preferred = [
                _find_column(table, ["analysis_date", "created_at", "date"]),
                _find_column(table, ["batch_id", "sample_id", "sample_ref"]),
                _find_column(table, ["product_name", "product"]),
                "Niveau de risque",
                _find_column(table, ["risk_score", "final_risk_score"]),
            ]
            _display_table(table, [c for c in preferred if c is not None], height=420)
            csv_data = filtered_history.drop(
                columns=["_FOODNEXA_Risk"], errors="ignore"
            ).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Exporter l’historique filtré (CSV)",
                data=csv_data,
                file_name="foodnexa_history_filtered.csv",
                mime="text/csv",
                key="foodnexa_dashboard_export_history",
            )
        else:
            st.info("Aucun résultat ne correspond aux filtres.")

    with tab_research:
        st.markdown("#### Research Dataset")
        st.caption(
            "Les champs non renseignés restent distincts des résultats mesurés à zéro."
        )
        if not research.empty:
            r1, r2, r3 = st.columns(3)
            r1.metric("Observations", len(research))
            r2.metric("Colonnes", len(research.columns))
            r3.metric("Doublons exacts", duplicates)

            research_product_col = _find_column(
                research, ["product_name", "product", "product_category", "category"]
            )
            research_search = st.text_input(
                "Rechercher dans le Research Dataset",
                key="foodnexa_dashboard_research_search",
                placeholder="Lot, produit, fournisseur...",
            )
            filtered_research = research.copy()
            if research_search.strip():
                mask = filtered_research.astype(str).apply(
                    lambda col: col.str.contains(
                        research_search.strip(), case=False, na=False
                    )
                ).any(axis=1)
                filtered_research = filtered_research[mask]
            _display_table(
                filtered_research,
                [
                    _find_column(filtered_research, ["batch_id", "sample_id", "sample_ref"]),
                    research_product_col,
                    _find_column(filtered_research, ["product_category", "category"]),
                    _find_column(filtered_research, ["analysis_date", "created_at"]),
                    _find_column(filtered_research, ["ph"]),
                    _find_column(filtered_research, ["temperature_celsius", "temperature"]),
                    _find_column(filtered_research, ["tvc", "total_viable_count"]),
                ],
                height=420,
            )
            research_csv = filtered_research.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Exporter le Research Dataset filtré (CSV)",
                data=research_csv,
                file_name="foodnexa_research_filtered.csv",
                mime="text/csv",
                key="foodnexa_dashboard_export_research",
            )
        else:
            st.info("Le Research Dataset ne contient aucune observation.")

    with tab_system:
        st.markdown("#### Data Quality & System Status")
        if score is not None:
            st.metric("Quality score", f"{score:.1f}%")
        else:
            st.info(
                "Le rapport actuel ne fournit pas de score global reconnu "
                "(quality_score / overall_score / score)."
            )

        issues = _quality_issues(quality_report)
        st.markdown("**Quality review**")
        if issues:
            for issue in issues:
                st.warning(issue)
        else:
            st.success("Aucun problème de qualité n’a été retourné par le rapport actuel.")

        st.write(f"Doublons exacts dans le Research Dataset : **{duplicates}**")

        st.markdown("**System pipeline**")
        if isinstance(pipeline_status, dict) and pipeline_status:
            status_cols = st.columns(min(3, len(pipeline_status)))
            for index, (name, available) in enumerate(pipeline_status.items()):
                with status_cols[index % len(status_cols)]:
                    if available is True:
                        st.success(f"{name} : Available")
                    elif available is False:
                        st.error(f"{name} : Unavailable")
                    else:
                        st.warning(f"{name} : Not confirmed")
        else:
            st.info("État du système non fourni par app.py.")

        st.caption(
            "FOODNEXA est un prototype expérimental d’aide à l’évaluation des risques. "
            "Le dashboard ne remplace ni les analyses de laboratoire ni la validation scientifique."
        )
