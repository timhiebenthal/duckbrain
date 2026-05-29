"""DuckBrain Search Benchmark Dashboard.

Developer-only tool — not shipped with DuckBrain.
Run with: uv run marimo edit notebooks/benchmark_dashboard.py
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import json, statistics
    from pathlib import Path
    import pandas as pd
    import altair as alt

    return Path, alt, json, mo, pd, statistics


@app.cell
def _(Path, json, pd):
    snap_dir = Path(__file__).parent.parent / "tests" / "benchmarks" / "snapshots"

    # Read all snapshot files into a list
    records = []
    for p in sorted(snap_dir.glob("*.json")):
        r = json.loads(p.read_text())
        r["_label"] = r.get("label") or p.stem
        r["_filename"] = p.name
        records.append(r)

    # Snapshot-level DataFrame
    snapshot_df = pd.DataFrame(
        {
            "label": [r["_label"] for r in records],
            "filename": [r["_filename"] for r in records],
            "commit": [str(r.get("commit", ""))[:8] for r in records],
            "snip_containment": [
                (r.get("averages") or {}).get("snippet_containment") for r in records
            ],
            "precision_at_5": [
                (r.get("averages") or {}).get("precision_at_5") for r in records
            ],
            "recall_at_5": [
                (r.get("averages") or {}).get("recall_at_5") for r in records
            ],
            "mrr": [(r.get("averages") or {}).get("mrr") for r in records],
            "score_avg": [(r.get("averages") or {}).get("score_avg") for r in records],
        }
    )

    # Query-level DataFrame (one row per test query per snapshot)
    q_rows = []
    for r in records:
        for q in r.get("per_query", []):
            if q.get("relevant_count", 0) > 0:
                # Build a human-readable query description
                n_rel = q["relevant_count"]
                q_rows.append(
                    {
                        "label": r["_label"],
                        "filename": r["_filename"],
                        "query_name": q["query"],
                        "query_desc": f"{q['query']}  ({n_rel} relevant page{'s' if n_rel > 1 else ''})",
                        "precision_at_5": q["precision_at_5"],
                        "recall_at_5": q["recall_at_5"],
                        "mrr": q["mrr"],
                        "snip_containment": q["snippet_containment"],
                        "score_avg": q["score_avg"],
                        "retrieved_count": q["retrieved_count"],
                        "relevant_count": n_rel,
                        "retrieved_titles": q.get("retrieved_titles", []),
                    }
                )
    query_df = pd.DataFrame(q_rows)

    latest_label = snapshot_df.iloc[-1]["label"] if len(snapshot_df) > 0 else "—"
    n_snapshots = len(snapshot_df)
    return latest_label, n_snapshots, query_df, snapshot_df


@app.cell
def _(mo, n_snapshots):
    mo.md("# DuckBrain Search Benchmark Dashboard")
    mo.md(f"**{n_snapshots} snapshots** loaded from `tests/benchmarks/snapshots/`")
    return


@app.cell
def _(mo):
    mo.md("""
    ### What each metric measures

    | Metric | Measures | Good value |
    |---|---|---|
    | **Snip%** (snippet containment) | Does the result snippet actually show the search term? Low = term is buried deep or only in the title, snippet shows unrelated text. | ≥90% |
    | **P@5** (precision at 5) | Of the top 5 results, how many are actually relevant? Low = many irrelevant results in top ranks. | ≥0.80 |
    | **R@5** (recall at 5) | Of all relevant pages, how many appear in the top 5? Low = relevant pages are being missed. | ≥0.90 |
    | **MRR** (mean reciprocal rank) | How high is the first relevant result? 1.0 = first result always relevant. | ≥0.80 |
    | **Score** (BM25) | DuckDB's FTS relevance score. Higher = stronger keyword match. Scores are log-scaled. | Typically 0.3–3.0 |
    | **NDCG** | Ranks by graded relevance (not just binary). Rewards perfect ordering. Currently aspirational. | ≥0.90 |
    """)
    return


@app.cell
def _(mo, pd, snapshot_df):
    mo.md("## Snapshots")
    t = snapshot_df[
        ["label", "commit", "snip_containment", "precision_at_5", "score_avg"]
    ].copy()
    t["snip_containment"] = t["snip_containment"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    t["precision_at_5"] = t["precision_at_5"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "—"
    )
    t["score_avg"] = t["score_avg"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    t.columns = ["Label", "Commit", "Snip%", "P@5", "Score"]
    mo.ui.table(t)
    return


@app.cell
def _(alt, mo, snapshot_df):
    mo.md("### Snippet Containment — do result snippets show the matched term?")
    sc = (
        alt.Chart(snapshot_df)
        .mark_bar()
        .encode(
            x=alt.X("snip_containment:Q", scale=alt.Scale(domain=[0, 1]),
                    axis=alt.Axis(format="%"), title="% of relevant results with term in snippet"),
            y=alt.Y("label:N", sort=None, title=None),
            color=alt.Color("label:N", legend=None),
            tooltip=["label", "snip_containment"],
        )
        .properties(height=max(60, 30 * len(snapshot_df)))
    )
    mo.ui.altair_chart(sc)
    return


@app.cell
def _(alt, mo, snapshot_df):
    mo.md("### Precision@5 — fraction of top-5 results that are relevant")
    p5 = (
        alt.Chart(snapshot_df)
        .mark_bar()
        .encode(
            x=alt.X("precision_at_5:Q", scale=alt.Scale(domain=[0, 1]),
                    title="Fraction of top-5 results that are relevant"),
            y=alt.Y("label:N", sort=None, title=None),
            color=alt.Color("label:N", legend=None),
            tooltip=["label", "precision_at_5"],
        )
        .properties(height=max(60, 30 * len(snapshot_df)))
    )
    mo.ui.altair_chart(p5)
    return


@app.cell
def _(latest_label, mo, pd, query_df):
    mo.md("## Latest Snapshot — Per-Query Detail")
    mo.md(f"**{latest_label}**  —  each row is one test query with its expected relevant pages")

    latest = query_df[query_df["filename"] == query_df["filename"].iloc[-1]]
    d = latest[
        [
            "query_desc", "precision_at_5", "recall_at_5",
            "snip_containment", "score_avg", "retrieved_count"
        ]
    ].copy()
    d["precision_at_5"] = d["precision_at_5"].apply(lambda x: f"{x:.2f}")
    d["recall_at_5"] = d["recall_at_5"].apply(lambda x: f"{x:.2f}")
    d["snip_containment"] = d["snip_containment"].apply(lambda x: f"{x:.0%}")
    d["score_avg"] = d["score_avg"].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
    d.columns = [
        "Query (N relevant pages)", "P@5", "R@5",
        "Snip%", "Score (avg)", "Found"
    ]
    mo.ui.table(d)
    return


@app.cell
def _():
    import math

    return (math,)


@app.cell
def _(math):
    def ndcg_score(retrieved, graded):
        if not graded:
            return 1.0
        k = 5
        rels = [graded.get(t, 0) for t in retrieved[:k]]
        rels = (rels + [0] * k)[:k]
        ideal = sorted(graded.values(), reverse=True)[:k]
        ideal = (ideal + [0] * k)[:k]

        def dcg(vals):
            return sum(s / math.log2(i + 2) for i, s in enumerate(vals))

        t = dcg(ideal)
        return dcg(rels) / t if t > 0 else 1.0

    GRADED = {
        "memory": {"Claude Mem": 3, "Agent Memory Systems": 3,
                   "duckdb-memory-mcp-build-decision": 2, "The LLM Wiki Concept": 1},
        "MCP": {"Claude Mem": 3, "duckdb-memory-mcp-build-decision": 3, "2026-05-28": 1},
        "DuckDB": {"Agent Memory Systems": 2, "duckdb-memory-mcp-build-decision": 3,
                   "Knowledge Graph Architecture": 2},
        "graph": {"Knowledge Graph Architecture": 3, "The LLM Wiki Concept": 1},
        "knowledge graph": {"Knowledge Graph Architecture": 3},
        "Jagged Frontier": {"Jagged Frontier": 3},
        "metrics layer": {"The missing piece of the modern data stack": 3},
    }
    return GRADED, ndcg_score


@app.cell
def _(GRADED, mo, ndcg_score, query_df, statistics):
    mo.md("---")
    mo.md("## Aspirational: NDCG@5")
    mo.md(
        "Normalized Discounted Cumulative Gain — rewards perfect ranking order. "
        "Pages graded 3 (best), 2 (good), 1 (marginal). Higher = better ordering."
    )

    latest_q = query_df[query_df["filename"] == query_df["filename"].iloc[-1]]
    nd_rows = []
    for _, row in latest_q.iterrows():
        qname = row["query_name"]
        grades = GRADED.get(qname, {})
        if grades:
            n = ndcg_score(row["retrieved_titles"], grades)
            nd_rows.append({"Query": qname, "NDCG@5": n})

    if nd_rows:
        nd_avg = statistics.mean(r["NDCG@5"] for r in nd_rows)
        mo.ui.table(
            [{"Query": r["Query"], "NDCG@5": f"{r['NDCG@5']:.2f}"} for r in nd_rows]
            + [{"Query": "AVERAGE", "NDCG@5": f"{nd_avg:.2f}"}]
        )
        mo.callout(
            f"Average NDCG@5: **{nd_avg:.2f}**. Improves with better ranking. Target: ≥0.90.",
            kind="info",
        )
    else:
        mo.md("No NDCG data available yet.")
    return


@app.cell
def _(mo):
    mo.md("""
    ## Aspirational — future metrics

    **Title-aware snippets** — 81% currently. Extending `_extract_snippet()`
    to also check page titles would close the gap to 100%.

    **Wikilink navigability** — 0% currently. `[[wikilinks]]` not yet
    extracted. Implement the wikilink graph spec to unlock backlink-based
    navigation and ranking.
    """)
    return


if __name__ == "__main__":
    app.run()
