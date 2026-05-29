"""DuckBrain Search Benchmark Dashboard.

Developer-only tool — not shipped with DuckBrain.
Run with: uv run marimo edit notebooks/benchmark_dashboard.py
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App()


@app.cell
def __():
    import marimo as mo
    import json, statistics
    from pathlib import Path
    import pandas as pd
    import altair as alt
    return (alt, json, mo, pd, statistics, Path)


@app.cell
def __(Path, json, pd):
    # Load all snapshots into DataFrames
    snap_dir = Path(__file__).parent.parent / "tests" / "benchmarks" / "snapshots"

    snapshot_rows = []
    query_rows = []

    for p in sorted(snap_dir.glob("*.json")):
        snap = json.loads(p.read_text())
        label = snap.get("label") or p.stem
        avg = snap.get("averages", {}) if isinstance(snap.get("averages"), dict) else {}
        snapshot_rows.append({
            "label": label,
            "filename": p.name,
            "commit": str(snap.get("commit", ""))[:8],
            "snip_containment": avg.get("snippet_containment"),
            "precision_at_5": avg.get("precision_at_5"),
            "recall_at_5": avg.get("recall_at_5"),
            "mrr": avg.get("mrr"),
            "score_avg": avg.get("score_avg"),
        })
        for q in snap.get("per_query", []):
            if q.get("relevant_count", 0) > 0:
                query_rows.append({
                    "label": label,
                    "filename": p.name,
                    "query": q["query"],
                    "precision_at_5": q["precision_at_5"],
                    "recall_at_5": q["recall_at_5"],
                    "mrr": q["mrr"],
                    "snip_containment": q["snippet_containment"],
                    "score_avg": q["score_avg"],
                    "retrieved_count": q["retrieved_count"],
                    "relevant_count": q["relevant_count"],
                    "retrieved_titles": q.get("retrieved_titles", []),
                })

    snapshot_df = pd.DataFrame(snapshot_rows)
    query_df = pd.DataFrame(query_rows)

    # Latest snapshot label
    latest_label = snapshot_df.iloc[-1]["label"] if len(snapshot_df) > 0 else "—"

    return (latest_label, query_df, snapshot_df)


@app.cell
def __(mo, snapshot_df):
    mo.md("# DuckBrain Search Benchmark Dashboard")
    mo.md(f"**{len(snapshot_df)} snapshots** from `tests/benchmarks/snapshots/`")
    return


# ── Summary table ──

@app.cell
def __(mo, snapshot_df):
    mo.md("## Snapshots")
    display_cols = snapshot_df[["label", "commit", "snip_containment", "precision_at_5", "score_avg"]].copy()
    display_cols["snip_containment"] = display_cols["snip_containment"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    display_cols["precision_at_5"] = display_cols["precision_at_5"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "—"
    )
    display_cols["score_avg"] = display_cols["score_avg"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    display_cols.columns = ["Label", "Commit", "Snip%", "P@5", "Score"]
    mo.ui.table(display_cols)
    return (display_cols,)


# ── Snippet containment chart ──

@app.cell
def __(alt, mo, snapshot_df):
    mo.md("### Snippet Containment Over Time")
    sc_chart = (
        alt.Chart(snapshot_df)
        .mark_bar()
        .encode(
            x=alt.X("snip_containment:Q", scale=alt.Scale(domain=[0, 1]),
                    axis=alt.Axis(format="%"), title=None),
            y=alt.Y("label:N", sort=None, title=None),
            color=alt.Color("label:N", legend=None),
            tooltip=["label", "snip_containment"],
        )
        .properties(height=max(60, 30 * len(snapshot_df)))
    )
    mo.ui.altair_chart(sc_chart)
    return (sc_chart,)


# ── P@5 chart ──

@app.cell
def __(alt, mo, snapshot_df):
    mo.md("### Precision@5 Over Time")
    p5_chart = (
        alt.Chart(snapshot_df)
        .mark_bar()
        .encode(
            x=alt.X("precision_at_5:Q", scale=alt.Scale(domain=[0, 1]), title=None),
            y=alt.Y("label:N", sort=None, title=None),
            color=alt.Color("label:N", legend=None),
            tooltip=["label", "precision_at_5"],
        )
        .properties(height=max(60, 30 * len(snapshot_df)))
    )
    mo.ui.altair_chart(p5_chart)
    return (p5_chart,)


# ── Latest per-query detail ──

@app.cell
def __(latest_label, mo, query_df):
    mo.md("## Latest Snapshot — Per-Query Detail")
    mo.md(f"**{latest_label}**")

    latest = query_df[query_df["filename"] == query_df["filename"].iloc[-1]]
    detail = latest[["query", "precision_at_5", "recall_at_5",
                      "snip_containment", "score_avg", "retrieved_count"]].copy()
    detail["precision_at_5"] = detail["precision_at_5"].apply(lambda x: f"{x:.2f}")
    detail["recall_at_5"] = detail["recall_at_5"].apply(lambda x: f"{x:.2f}")
    detail["snip_containment"] = detail["snip_containment"].apply(lambda x: f"{x:.0%}")
    detail["score_avg"] = detail["score_avg"].apply(
        lambda x: f"{x:.3f}" if pd.notna(x) else "—"
    )
    detail.columns = ["Query", "P@5", "R@5", "Snippet", "Score (avg)", "Results"]
    mo.ui.table(detail)
    return (detail, latest)


# ── NDCG (aspirational) ──

@app.cell
def __():
    import math
    return (math,)


@app.cell
def __(math):
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
    return (GRADED, ndcg_score)


@app.cell
def __(GRADED, mo, ndcg_score, query_df, statistics):
    mo.md("---")
    mo.md("## Aspirational: NDCG@5")

    ndcg_rows = []
    latest_queries = query_df[query_df["filename"] == query_df["filename"].iloc[-1]]
    for _, row in latest_queries.iterrows():
        qname = row["query"]
        grades = GRADED.get(qname, {})
        if grades:
            n = ndcg_score(row["retrieved_titles"], grades)
            ndcg_rows.append({"Query": qname, "NDCG@5": n})

    if ndcg_rows:
        ndcg_avg = statistics.mean(r["NDCG@5"] for r in ndcg_rows)
        mo.ui.table(
            [{"Query": r["Query"], "NDCG@5": f"{r['NDCG@5']:.2f}"} for r in ndcg_rows]
            + [{"Query": "AVERAGE", "NDCG@5": f"{ndcg_avg:.2f}"}]
        )
        mo.callout(
            f"Average NDCG@5: **{ndcg_avg:.2f}**. Improves with better ranking. Target: ≥0.90.",
            kind="info",
        )
    else:
        mo.md("No NDCG data available yet.")
    return


@app.cell
def __(mo):
    mo.md(
        "## Aspirational\n\n"
        "**Title-aware snippets** — 81% currently. Extending `_extract_snippet()` "
        "to check page titles would close the gap to 100%.\n\n"
        "**Wikilink navigability** — 0% currently. `[[wikilinks]]` not yet "
        "extracted. Implement the wikilink graph spec."
    )
    return


if __name__ == "__main__":
    app.run()
