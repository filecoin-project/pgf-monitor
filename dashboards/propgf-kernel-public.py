import marimo

__generated_with = "unknown"
app = marimo.App(width="full")


# =============================================================================
# HEADER
# =============================================================================


@app.cell(hide_code=True)
def _(SERIES_LAST, mo, n_functions, n_metrics):
    _badge = "background-color:#f0eeeb; padding:2px 6px; border-radius:3px;"
    _h = (
        "# Filecoin Kernel — what is being watched\n\n"
        "<small>"
        f'Owner: <span style="{_badge}">Open Source Observer</span> · '
        f'Readings through: <span style="{_badge}">{SERIES_LAST}</span> · '
        f'Source: <span style="{_badge}">2 public tables</span>'
        "</small>\n\n"
        f"{n_metrics} metrics are fetched every night from the teams' own infrastructure and "
        "judged by nobody: **no threshold in this dashboard is currently in force**, because the "
        "agreements carrying those numbers are not executed. What follows is measurement — which "
        f"of the {n_functions} catalogued kernel functions anyone is watching, and what those "
        "watchers read.\n\n"
        "Every figure comes from "
        "`filecoin.filpgf_public.kernel_timeseries_metrics_by_project` and "
        "`filecoin.filpgf_public.kernel_functions`, both public. Any OSO API key reproduces it."
    )
    mo.md(_h)
    return


# =============================================================================
# KPI SUMMARY CARDS
# =============================================================================


@app.cell(hide_code=True)
def _(df_functions, df_series, mo, n_functions, n_metrics):
    _covered = int((df_functions["adopted_metrics"] > 0).sum())
    _in_scope = df_functions[df_functions["is_in_scope"]]
    _in_scope_covered = int((_in_scope["adopted_metrics"] > 0).sum())
    _scored = int(df_series["threshold_op"].notna().sum())
    _indeterminate = int(df_series["amount"].isna().sum())

    mo.hstack(
        [
            mo.stat(
                value=f"{n_metrics}",
                label="Metrics measured",
                caption=f"across {df_series['team'].nunique()} teams, "
                f"{df_series['grant_ref'].nunique()} grants",
            ),
            mo.stat(
                value=f"{_covered}/{n_functions}",
                label="Kernel functions watched",
                caption=f"{_in_scope_covered}/{len(_in_scope)} of the in-scope tiers",
            ),
            mo.stat(
                value=f"{len(df_series):,}",
                label="Readings on record",
                caption=f"{_indeterminate} with no defensible value",
            ),
            mo.stat(
                value=f"{_scored}",
                label="Readings scored",
                caption="no bar is in force until a contract is executed",
            ),
        ],
        widths="equal",
        gap=1,
    )
    return


# =============================================================================
# GLOBAL FILTERS
# =============================================================================


@app.cell(hide_code=True)
def _(df_series, mo):
    tier_filter = mo.ui.dropdown(
        options=["All"] + sorted(df_series["tier"].dropna().unique().tolist()),
        value="All",
        label="Kernel tier",
    )
    team_filter = mo.ui.dropdown(
        options=["All"] + sorted(df_series["team"].dropna().unique().tolist()),
        value="All",
        label="Team",
        searchable=True,
    )
    mo.hstack([tier_filter, team_filter], justify="start", gap=2)
    return team_filter, tier_filter


@app.cell(hide_code=True)
def _(df_series, team_filter, tier_filter):
    df_filtered = df_series.copy()
    if tier_filter.value != "All":
        df_filtered = df_filtered[df_filtered["tier"] == tier_filter.value]
    if team_filter.value != "All":
        df_filtered = df_filtered[df_filtered["team"] == team_filter.value]
    return (df_filtered,)


# =============================================================================
# COVERAGE — which kernel functions anyone is watching
# =============================================================================


@app.cell(hide_code=True)
def _(mo):
    _head = (
        "## Half the kernel is unwatched, and that is the point of this chart\n\n"
        "Bars are catalogued kernel functions; length is how many adopted metrics evidence each "
        "one. The functions sitting at zero are the honest part — a coverage figure computed only "
        "over what we already measure would always read 100%."
    )
    mo.md(_head)
    return


@app.cell(hide_code=True)
def _(CHART_LAYOUT, colors, df_functions, go, mo):
    _cov = df_functions.sort_values(
        ["adopted_metrics", "kernel_function"], ascending=[True, False]
    )
    _bar_color = [
        colors["rule"] if _n == 0 else colors["accent"] for _n in _cov["adopted_metrics"]
    ]

    fig_coverage = go.Figure(
        go.Bar(
            x=_cov["adopted_metrics"],
            y=_cov["kernel_function"].str.slice(0, 58),
            orientation="h",
            marker=dict(color=_bar_color),
            customdata=_cov[["tier", "sub_category", "adopted_teams", "draft_metrics"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{customdata[0]} · %{customdata[1]}<br>"
                "%{x} adopted metric(s) from %{customdata[2]} team(s)<br>"
                "%{customdata[3]} drafted<extra></extra>"
            ),
        )
    )
    fig_coverage.update_layout(**CHART_LAYOUT)
    fig_coverage.update_layout(height=760, showlegend=False, bargap=0.35)
    fig_coverage.update_xaxes(title_text="adopted metrics", dtick=1)
    fig_coverage.update_yaxes(title_text=None, tickfont=dict(size=10))
    mo.ui.plotly(fig_coverage)
    return


# =============================================================================
# READINGS OVER TIME
# =============================================================================


@app.cell(hide_code=True)
def _(mo):
    _head_trend = (
        "## What the watchers read\n\n"
        "One line per metric, normalised to its own maximum so unlike units share an axis — a "
        "head-lag in epochs and an uptime percentage cannot otherwise be read together. Gaps are "
        "days the source produced no defensible number: not zeroes, and not failures."
    )
    mo.md(_head_trend)
    return


@app.cell(hide_code=True)
def _(CHART_LAYOUT, colors, df_filtered, go, mo, pd):
    _plot = df_filtered.dropna(subset=["amount"]).copy()
    fig_trend = go.Figure()

    if len(_plot):
        _plot["series"] = _plot["team"] + " · " + _plot["metric_name"]
        _peak = _plot.groupby("series")["amount"].transform("max").abs().replace(0, 1)
        _plot["scaled"] = _plot["amount"] / _peak
        for _name, _grp in _plot.sort_values("sample_date").groupby("series"):
            _g = _grp.sort_values("sample_date")
            fig_trend.add_trace(
                go.Scatter(
                    x=pd.to_datetime(_g["sample_date"]),
                    y=_g["scaled"],
                    mode="lines",
                    name=_name,
                    line=dict(color=colors["ink_3"], width=1),
                    customdata=_g[["amount", "kernel_function"]],
                    hovertemplate=(
                        "<b>%{fullData.name}</b><br>"
                        "%{x|%Y-%m-%d}: %{customdata[0]:.4g}<br>"
                        "%{customdata[1]}<extra></extra>"
                    ),
                )
            )

    fig_trend.update_layout(**CHART_LAYOUT)
    fig_trend.update_layout(height=420, showlegend=False, hovermode="closest")
    fig_trend.update_xaxes(title_text=None)
    fig_trend.update_yaxes(title_text="reading ÷ its own peak", rangemode="tozero")
    mo.ui.plotly(fig_trend)
    return


# =============================================================================
# DETAIL TABLE
# =============================================================================


@app.cell(hide_code=True)
def _(mo):
    _head_table = (
        "## Every commitment, and its latest reading\n\n"
        "One row per monitored commitment — identified by team and function, not by project, "
        "since two teams report the same metric name for their own infrastructure."
    )
    mo.md(_head_table)
    return


@app.cell(hide_code=True)
def _(df_filtered, mo):
    _latest = (
        df_filtered.sort_values("sample_date")
        .groupby(["team", "function_id", "metric_name"], as_index=False)
        .last()
    )
    _table = _latest[
        [
            "team",
            "metric_name",
            "kernel_function",
            "tier",
            "grant_ref",
            "sample_date",
            "amount",
            "cadence",
            "sla_statement",
        ]
    ].sort_values(["tier", "team", "metric_name"])

    mo.ui.table(
        _table,
        selection=None,
        show_download=True,
        pagination=True,
        page_size=15,
        format_mapping={"amount": lambda v: "—" if v is None else f"{v:,.4g}"},
    )
    return


# =============================================================================
# METHODOLOGY
# =============================================================================


@app.cell(hide_code=True)
def _(SERIES_FIRST, SERIES_LAST, mo):
    mo.accordion(
        {
            "Methodology, and what this dashboard deliberately cannot tell you": mo.md(
                rf"""
                **Sources.** Exactly two tables, both public:
                `filecoin.filpgf_public.kernel_timeseries_metrics_by_project` (one row per
                team × function × metric × day, {SERIES_FIRST} to {SERIES_LAST}) and
                `filecoin.filpgf_public.kernel_functions` (the catalogued inventory, including
                functions nothing measures). No private table is read, so anyone with an OSO API
                key can rebuild this page.

                **Nothing is scored.** Every threshold was withdrawn on 2026-08-20: the numbers
                exist in signed appendices, but the agreements carrying them are not executed, and
                a number nobody has countersigned is not a commitment. `threshold_op` is null on
                every row, so no reading here is a pass or a fail. When contracts are signed the
                bars return unchanged and history re-judges itself, because the bar is recorded
                per day rather than as a single current value.

                **Two different absences.** A missing `amount` means the source produced no
                defensible number that day. A missing threshold means no bar was agreed. Neither
                is a breach, and this dashboard renders neither as one.

                **What this page cannot show**, by construction, because it reads only public
                tables: adjudicated committee verdicts, draft metrics not yet adopted, the source
                host behind each reading, and anything about what a grant is worth. The first three
                live in the full internal dashboard; the last belongs in no public surface.

                **Readings are normalised per series** in the trend chart — each line is divided
                by its own peak so unlike units share an axis. Hover shows the real value.
                """
            )
        }
    )
    return


# =============================================================================
# DATA QUERIES
# =============================================================================


@app.cell(hide_code=True)
def _(pd):
    def to_frame(result):
        # mo.sql returns polars here. Going polars -> dicts -> pandas keeps this working
        # without pyarrow, which .to_pandas() requires and which is not installed (nor
        # cheap under Pyodide). Engine-agnostic on purpose.
        if hasattr(result, "to_dicts"):
            return pd.DataFrame(result.to_dicts())
        return pd.DataFrame(result)

    return (to_frame,)


@app.cell(hide_code=True)
def _(mo, pyoso_db_conn, to_frame):
    df_series = to_frame(mo.sql(
        """
        SELECT sample_date, team, function_id, metric_name, grant_ref, kernel_id,
               kernel_function, tier, category, sub_category, amount,
               threshold_op, threshold_value, threshold_source, method, cadence, sla_statement
        FROM filecoin.filpgf_public.kernel_timeseries_metrics_by_project
        ORDER BY sample_date
        """,
        output=False,
        engine=pyoso_db_conn,
    ))
    return (df_series,)


@app.cell(hide_code=True)
def _(mo, pyoso_db_conn, to_frame):
    df_functions = to_frame(mo.sql(
        """
        SELECT kernel_id, tier, category, sub_category, kernel_function, kernel_value,
               is_in_scope, adopted_metrics, draft_metrics, adopted_teams
        FROM filecoin.filpgf_public.kernel_functions
        ORDER BY tier, category, kernel_function
        """,
        output=False,
        engine=pyoso_db_conn,
    ))
    return (df_functions,)


@app.cell(hide_code=True)
def _(df_functions, df_series):
    # Header and KPI copy quote these, so derive them once from the data rather than hardcoding.
    n_metrics = int(
        df_series.groupby(["team", "function_id", "metric_name"]).ngroups
    )
    n_functions = int(len(df_functions))
    SERIES_FIRST = str(df_series["sample_date"].min())
    SERIES_LAST = str(df_series["sample_date"].max())
    return SERIES_FIRST, SERIES_LAST, n_functions, n_metrics


# =============================================================================
# CONFIGURATION
# =============================================================================


@app.cell(hide_code=True)
def _():
    colors = {
        "ink": "#1a1814",
        "ink_2": "#3a342b",
        "ink_3": "#5d5445",
        "paper": "#f5f1ea",
        "paper_2": "#f0eeeb",
        "rule": "#d5cfc5",
        "accent": "#2a3d8f",
        "signal": "#c8341d",
        "healthy": "#1e8a7a",
        "warm": "#d97c2a",
        "purple": "#7b5ea7",
    }

    fonts = {
        "headline": "Georgia, serif",
        "body": "Inter, system-ui, sans-serif",
        "mono": "'SF Mono', 'Cascadia Code', 'JetBrains Mono', monospace",
    }

    CHART_LAYOUT = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=fonts["body"], size=12, color=colors["ink"]),
        margin=dict(t=20, l=60, r=40, b=50),
        xaxis=dict(showgrid=False, linecolor=colors["ink"], linewidth=1),
        yaxis=dict(
            showgrid=True,
            gridcolor=colors["rule"],
            linecolor=colors["ink"],
            linewidth=1,
        ),
    )

    PRIMARY_COLOR = colors["accent"]
    ACCENT_COLOR = colors["signal"]
    COLORS = [
        colors["accent"],
        colors["warm"],
        colors["healthy"],
        colors["purple"],
        colors["signal"],
        colors["ink_3"],
    ]
    return ACCENT_COLOR, CHART_LAYOUT, COLORS, PRIMARY_COLOR, colors, fonts


# =============================================================================
# BOILERPLATE
# =============================================================================


@app.cell(hide_code=True)
def _():
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go

    return go, pd, px


@app.cell(hide_code=True)
def setup_pyoso():
    # This code sets up pyoso to be used as a database provider for this notebook
    # This code is autogenerated. Modification could lead to unexpected results :)
    import pyoso
    import marimo as mo

    pyoso_db_conn = pyoso.Client().dbapi_connection()
    return mo, pyoso_db_conn


if __name__ == "__main__":
    app.run()
