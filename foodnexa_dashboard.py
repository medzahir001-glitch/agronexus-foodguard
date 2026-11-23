
import html
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

GREEN = "#176B3A"
AMBER = "#D99121"
RED = "#C83E3E"
GREY = "#AAB5AC"


def to_df(data):
    if data is None:
        return pd.DataFrame()
    if isinstance(data, pd.DataFrame):
        return data.copy()
    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def find_col(df, *names):
    columns = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        if name.lower() in columns:
            return columns[name.lower()]
    return None


def risk_label(value):
    value = str(value).strip().lower()
    if value in ("faible", "low"):
        return "Faible"
    if value in ("modéré", "modere", "moderate", "medium"):
        return "Modéré"
    if value in ("élevé", "eleve", "high"):
        return "Élevé"
    if "incomplet" in value:
        return "Données incomplètes"
    return "Non classé"


def prepare_history(data):
    df = to_df(data)

    if df.empty:
        return df

    batch = find_col(df, "batch_id", "batch_code")
    product = find_col(df, "product_name", "product")
    risk = find_col(df, "risk_level", "risk_status")
    score = find_col(df, "risk_score", "risk_index", "score")
    date = find_col(df, "analysis_date", "created_at", "date")

    df["_batch"] = (
        df[batch].fillna("").astype(str) if batch else ""
    )

    df["_product"] = (
        df[product].fillna("Non renseigné").astype(str)
        if product else "Non renseigné"
    )

    df["_risk"] = (
        df[risk].map(risk_label) if risk else "Non classé"
    )

    df["_score"] = (
        pd.to_numeric(df[score], errors="coerce")
        if score else float("nan")
    )

    df["_date"] = (
        pd.to_datetime(df[date], errors="coerce", utc=True)
        if date else pd.NaT
    )

    return df


def kpi(label, value, color=GREEN, note=""):
    st.markdown(
        f"""
        <div style="
        background:white;
        border:1px solid #e1e9e2;
        border-top:3px solid {color};
        border-radius:9px;
        padding:9px;
        min-height:76px;">
        <div style="font-size:10px;color:#68766b;font-weight:700">
        {html.escape(str(label))}
        </div>
        <div style="font-size:21px;color:#14532d;font-weight:850">
        {html.escape(str(value))}
        </div>
        <div style="font-size:9px;color:#829087">
        {html.escape(str(note))}
        </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def chart_style(fig, height=260):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=25, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=10, color="#173B27"),
        legend=dict(
            orientation="h",
            y=-0.22,
            x=0
        )
    )
    return fig


def risk_distribution(df):
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    counts = df["_risk"].value_counts()

    colors = {
        "Faible": GREEN,
        "Modéré": AMBER,
        "Élevé": RED,
        "Données incomplètes": "#7B8794",
        "Non classé": GREY
    }

    fig = go.Figure(
        go.Pie(
            labels=counts.index,
            values=counts.values,
            hole=0.65,
            marker=dict(
                colors=[
                    colors.get(x, GREY)
                    for x in counts.index
                ],
                line=dict(color="white", width=2)
            ),
            textinfo="percent"
        )
    )

    fig.add_annotation(
        text=f"<b>{len(df)}</b><br><sup>Analyses</sup>",
        x=0.5,
        y=0.5,
        showarrow=False
    )

    st.plotly_chart(
        chart_style(fig, 250),
        use_container_width=True,
        key="fnx_risk_chart"
    )


def risk_evolution(df):
    dated = df.dropna(subset=["_date"]).copy()

    if dated.empty:
        st.info("Dates non disponibles.")
        return

    dated["_day"] = dated["_date"].dt.strftime("%Y-%m-%d")

    trend = (
        dated.groupby(["_day", "_risk"])
        .size()
        .reset_index(name="Analyses")
    )

    fig = px.line(
        trend,
        x="_day",
        y="Analyses",
        color="_risk",
        markers=True,
        color_discrete_map={
            "Faible": GREEN,
            "Modéré": AMBER,
            "Élevé": RED
        }
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Nombre d'analyses"
    )

    st.plotly_chart(
        chart_style(fig, 250),
        use_container_width=True,
        key="fnx_evolution_chart"
    )


def lot_intelligence(df):
    st.subheader("📦 Lot Intelligence")

    lots = sorted(
        x for x in df["_batch"].unique()
        if str(x).strip()
    )

    if not lots:
        st.info("Aucun Batch ID disponible.")
        return

    selected = st.selectbox(
        "Choisir un lot",
        lots,
        key="fnx_selected_lot"
    )

    lot = df[df["_batch"] == selected].copy()

    lot = lot.sort_values(
        "_date",
        ascending=False
    )

    latest = lot.iloc[0]

    score = latest["_score"]
    level = latest["_risk"]

    color = (
        RED if level == "Élevé"
        else AMBER if level == "Modéré"
        else GREEN
    )

    a, b, c, d = st.columns(4)

    with a:
        kpi("Batch ID", selected)

    with b:
        kpi(
            "Risk Score",
            f"{score:.1f}/100" if pd.notna(score) else "N/D",
            color
        )

    with c:
        kpi("Risk Level", level, color)

    with d:
        kpi("Nombre d'analyses", len(lot))

    st.markdown("**Paramètres enregistrés**")

    parameters = [
        ("Température °C", ("temperature_celsius", "temperature")),
        ("Stockage jours", ("storage_days",)),
        ("pH", ("ph",)),
        ("Rupture chaîne du froid", ("cold_chain_broken",)),
        ("Hygiène contrôlée", ("hygiene_controlled",)),
        ("Pasteurisation", ("pasteurized",))
    ]

    rows = []

    for label, aliases in parameters:
        col = find_col(lot, *aliases)

        if col:
            value = latest[col]

            rows.append({
                "Paramètre": label,
                "Valeur": (
                    "Non renseigné"
                    if pd.isna(value)
                    else str(value)
                )
            })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucun paramètre détaillé disponible.")

    factor_columns = [
        c for c in lot.columns
        if str(c).endswith("_score")
        and c not in ("risk_score", "_score")
    ]

    factors = []

    for col in factor_columns:
        value = pd.to_numeric(
            pd.Series([latest[col]]),
            errors="coerce"
        ).iloc[0]

        if pd.notna(value):
            factors.append({
                "Facteur": str(col).replace(
                    "_score", ""
                ).replace("_", " ").title(),
                "Score": value
            })

    if factors:
        st.markdown("**Facteurs de risque enregistrés**")

        factor_df = pd.DataFrame(factors)

        fig = px.bar(
            factor_df.sort_values("Score"),
            x="Score",
            y="Facteur",
            orientation="h",
            color_discrete_sequence=[GREEN]
        )

        st.plotly_chart(
            chart_style(fig, max(210, len(factors) * 35)),
            use_container_width=True
        )

    for label, candidates in [
        ("Raisons", ("reasons",)),
        ("Recommandations", ("recommendations",))
    ]:
        col = find_col(lot, *candidates)

        if col and pd.notna(latest[col]):
            st.markdown(f"**{label} enregistrées**")

            value = latest[col]

            items = (
                value if isinstance(value, (list, tuple))
                else str(value).split("|")
            )

            for item in items:
                if str(item).strip():
                    st.write("• " + str(item).strip())

    st.markdown("**Historique du lot**")

    st.dataframe(
        pd.DataFrame({
            "Date": lot["_date"].dt.strftime(
                "%Y-%m-%d %H:%M"
            ).fillna("—"),
            "Risk Score": lot["_score"].round(1),
            "Niveau": lot["_risk"]
        }),
        use_container_width=True,
        hide_index=True
    )


def compare_lots(df):
    st.subheader("📊 Comparaison des lots")

    lots = sorted(
        x for x in df["_batch"].unique()
        if str(x).strip()
    )

    if len(lots) < 2:
        st.info("Il faut au moins deux lots.")
        return

    selected = st.multiselect(
        "Sélectionner les lots",
        lots,
        default=lots[:min(3, len(lots))],
        max_selections=8,
        key="fnx_compare_selection"
    )

    if len(selected) < 2:
        return

    sub = df[df["_batch"].isin(selected)].sort_values("_date")

    summary = sub.groupby(
        "_batch",
        as_index=False
    ).agg(
        Produit=("_product", "last"),
        Analyses=("_batch", "size"),
        Score_moyen=("_score", "mean"),
        Dernier_score=("_score", "last"),
        Niveau=("_risk", "last")
    )

    summary["Score_moyen"] = summary["Score_moyen"].round(1)
    summary["Dernier_score"] = summary["Dernier_score"].round(1)

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )

    valid = summary.dropna(subset=["Dernier_score"])

    if not valid.empty:
        fig = px.bar(
            valid,
            x="_batch",
            y="Dernier_score",
            color="Niveau",
            color_discrete_map={
                "Faible": GREEN,
                "Modéré": AMBER,
                "Élevé": RED
            },
            text="Dernier_score",
            labels={
                "_batch": "Lot",
                "Dernier_score": "Risk Score"
            }
        )

        st.plotly_chart(
            chart_style(fig, 260),
            use_container_width=True
        )


def research_explorer(data):
    st.subheader("🧬 Research Explorer")

    research = to_df(data)

    if research.empty:
        st.info("Aucune observation scientifique disponible.")
        return

    batch = find_col(research, "batch_id", "batch_code")
    product = find_col(research, "product_name", "product")
    category = find_col(research, "product_category", "category")

    research["_batch_view"] = (
        research[batch].fillna("").astype(str)
        if batch else ""
    )

    research["_product_view"] = (
        research[product].fillna("Non renseigné").astype(str)
        if product else "Non renseigné"
    )

    research["_category_view"] = (
        research[category].fillna("Non renseigné").astype(str)
        if category else "Non renseigné"
    )

    a, b, c = st.columns(3)

    products = sorted(research["_product_view"].unique())
    categories = sorted(research["_category_view"].unique())

    with a:
        selected_products = st.multiselect(
            "Produit",
            products,
            default=products,
            key="fnx_research_products"
        )

    with b:
        selected_categories = st.multiselect(
            "Catégorie",
            categories,
            default=categories,
            key="fnx_research_categories"
        )

    with c:
        search = st.text_input(
            "Recherche Batch ID",
            key="fnx_research_batch"
        )

    view = research[
        research["_product_view"].isin(selected_products)
    ]

    view = view[
        view["_category_view"].isin(selected_categories)
    ]

    if search.strip():
        view = view[
            view["_batch_view"].str.contains(
                search.strip(),
                case=False,
                na=False
            )
        ]

    st.caption(
        f"{len(view)} observation(s). "
        "Les valeurs manquantes restent non renseignées."
    )

    visible = view.drop(
        columns=[
            "_batch_view",
            "_product_view",
            "_category_view"
        ],
        errors="ignore"
    )

    st.dataframe(
        visible,
        use_container_width=True,
        hide_index=True,
        height=300
    )

    st.download_button(
        "Exporter les observations CSV",
        visible.to_csv(index=False).encode("utf-8-sig"),
        "foodnexa_research.csv",
        "text/csv",
        key="fnx_research_download"
    )


def render_dashboard(
    history_data=None,
    research_data=None,
    quality_report=None,
    pipeline_status=None
):

    st.markdown("""
    <style>
    .block-container {
        max-width:1450px;
        padding-top:.7rem;
        padding-bottom:1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    df = prepare_history(history_data)

    st.title("FOODNEXA | Food Safety & Research Intelligence")

    st.caption(
        "Interactive Dashboard — Risk Monitoring, Lot Intelligence "
        "and Scientific Research"
    )

    with st.expander("🔎 Filtres du Dashboard", expanded=True):

        a, b, c = st.columns([1, 1, 1.2])

        products = (
            sorted(df["_product"].unique())
            if not df.empty else []
        )

        risk_options = [
            "Faible",
            "Modéré",
            "Élevé",
            "Données incomplètes",
            "Non classé"
        ]

        with a:
            selected_products = st.multiselect(
                "Produits",
                products,
                default=products,
                key="fnx_dashboard_products"
            )

        with b:
            selected_risks = st.multiselect(
                "Niveau de risque",
                risk_options,
                default=risk_options,
                key="fnx_dashboard_risks"
            )

        with c:
            batch_search = st.text_input(
                "Recherche Batch ID",
                key="fnx_dashboard_batch"
            )

    filtered = df.copy()

    if not filtered.empty:

        filtered = filtered[
            filtered["_product"].isin(selected_products)
        ]

        filtered = filtered[
            filtered["_risk"].isin(selected_risks)
        ]

        if batch_search.strip():
            filtered = filtered[
                filtered["_batch"].str.contains(
                    batch_search.strip(),
                    case=False,
                    na=False
                )
            ]

    total = len(filtered)

    high = int(
        (filtered["_risk"] == "Élevé").sum()
    ) if total else 0

    moderate = int(
        (filtered["_risk"] == "Modéré").sum()
    ) if total else 0

    unique_lots = (
        filtered["_batch"].replace("", pd.NA).nunique()
        if total else 0
    )

    avg = (
        filtered["_score"].mean()
        if total and filtered["_score"].notna().any()
        else None
    )

    k = st.columns(4)

    with k[0]:
        kpi("Analyses", total)

    with k[1]:
        kpi("Lots distincts", unique_lots)

    with k[2]:
        kpi("Risque élevé", high, RED)

    with k[3]:
        kpi(
            "Score moyen",
            f"{avg:.1f}/100" if avg is not None else "N/D"
        )

    st.divider()

    st.subheader("📈 Surveillance des risques")

    left, right = st.columns([1, 1.5])

    with left:
        risk_distribution(filtered)

    with right:
        risk_evolution(filtered)

    st.divider()

    st.subheader("📋 Historique des analyses")

    if filtered.empty:
        st.info("Aucune analyse ne correspond aux filtres.")
    else:
        table = pd.DataFrame({
            "Date": filtered["_date"].dt.strftime(
                "%Y-%m-%d %H:%M"
            ).fillna("—"),
            "Lot": filtered["_batch"],
            "Produit": filtered["_product"],
            "Risk Score": filtered["_score"].round(1),
            "Niveau": filtered["_risk"]
        })

        st.dataframe(
            table.sort_values("Date", ascending=False),
            use_container_width=True,
            hide_index=True,
            height=250
        )

        st.download_button(
            "Exporter les analyses CSV",
            table.to_csv(index=False).encode("utf-8-sig"),
            "foodnexa_analyses.csv",
            "text/csv",
            key="fnx_history_download"
        )

    st.divider()

    lot_intelligence(filtered)

    st.divider()

    compare_lots(filtered)

    st.divider()

    research_explorer(research_data)

    with st.expander("Data Quality & System Status"):

        st.metric(
            "Research observations",
            len(to_df(research_data))
        )

        if isinstance(quality_report, dict):
            st.json(quality_report)

        if isinstance(pipeline_status, dict):
            st.json(pipeline_status)

    st.caption(
        "FOODNEXA est un prototype expérimental d'aide à la décision. "
        "Les statistiques reflètent les données enregistrées. "
        "Une donnée manquante n'est pas considérée comme zéro ou conforme. "
        "Les résultats ne remplacent pas les analyses de laboratoire."
    )
