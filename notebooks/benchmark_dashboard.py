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
    import json, math, statistics
    from pathlib import Path
    import altair as alt
    return (alt, json, math, mo, statistics, Path)


@app.cell
def __(Path, json):
    d = Path(__file__).parent.parent / "tests" / "benchmarks" / "snapshots"
    _snaps = []
    for _p in sorted(d.glob("*.json")):
        _it = json.loads(_p.read_text())
        _it["_filename"] = _p.name
        _snaps.append(_it)
    _cur = Path(__file__).parent.parent / "tests" / "benchmarks" / "baseline.json"
    if _cur.exists():
        _it = json.loads(_cur.read_text())
        _it["_filename"] = "current (baseline.json)"
        _snaps.append(_it)
    snapshots = _snaps
    return (snapshots,)


@app.cell
def __(mo, snapshots):
    mo.md("# DuckBrain Search Benchmark Dashboard")
    mo.md(f"**{len(snapshots)} snapshots** from `tests/benchmarks/snapshots/`")
    return


@app.cell
def __(snapshots):
    """Pre-compute all chart + table data in one go. One cell, no name conflicts."""
    # Summary table
    summary_rows = []
    # Snippet chart
    snippet_data = []
    # P@5 chart
    p5_data = []
    # Per-query detail (latest)
    detail_rows = []

    for sn in snapshots:
        sn_avg = sn.get("averages", {}) if isinstance(sn.get("averages"), dict) else {}
        sn_label = sn.get("label") or sn.get("_filename", "—")

        # Summary
        sv = sn_avg.get("score_avg")
        summary_rows.append({
            "File": sn.get("_filename", "—"),
            "Label": sn.get("label", "—"),
            "Commit": str(sn.get("commit", "—"))[:8],
            "Snip%": f"{sn_avg.get('snippet_containment', 0):.0%}",
            "P@5": f"{sn_avg.get('precision_at_5', 0):.2f}",
            "Score": f"{sv:.2f}" if sv else "N/A",
        })

        # Snippet chart
        v1 = sn_avg.get("snippet_containment")
        if v1 is not None:
            snippet_data.append({"version": sn_label, "value": v1})

        # P@5 chart
        v2 = sn_avg.get("precision_at_5")
        if v2 is not None:
            p5_data.append({"version": sn_label, "value": v2})

    # Detail from latest
    if snapshots:
        for q in snapshots[-1].get("per_query", []):
            if q.get("relevant_count", 0) == 0:
                continue
            detail_rows.append({
                "Query": q["query"],
                "P@5": f"{q['precision_at_5']:.2f}",
                "R@5": f"{q['recall_at_5']:.2f}",
                "Snippet": f"{q['snippet_containment']:.0%}",
                "Score (avg)": f"{q['score_avg']:.3f}" if q.get("score_avg") else "—",
                "Results": q["retrieved_count"],
            })

    return (detail_rows, p5_data, snippet_data, summary_rows)


@app.cell
def __(mo, summary_rows):
    mo.md("## Snapshots")
    mo.ui.table(summary_rows)
    return


@app.cell
def __(alt, mo, snippet_data):
    mo.md("### Snippet Containment Over Time")
    if snippet_data:
        ch1 = (
            alt.Chart(alt.Data(values=snippet_data))
            .mark_bar()
            .encode(
                x=alt.X("value:Q", scale=alt.Scale(domain=[0, 1]),
                        axis=alt.Axis(format="%"), title=None),
                y=alt.Y("version:N", sort=None, title=None),
                color=alt.Color("version:N", legend=None),
            )
            .properties(height=max(60, 30 * len(snippet_data)))
        )
        mo.ui.altair_chart(ch1)
    return


@app.cell
def __(alt, mo, p5_data):
    mo.md("### Precision@5 Over Time")
    if p5_data:
        ch2 = (
            alt.Chart(alt.Data(values=p5_data))
            .mark_bar()
            .encode(
                x=alt.X("value:Q", scale=alt.Scale(domain=[0, 1]), title=None),
                y=alt.Y("version:N", sort=None, title=None),
                color=alt.Color("version:N", legend=None),
            )
            .properties(height=max(60, 30 * len(p5_data)))
        )
        mo.ui.altair_chart(ch2)
    return


@app.cell
def __(detail_rows, mo, snapshots):
    mo.md("## Latest Snapshot — Per-Query Detail")
    if snapshots:
        mo.md(f"**{snapshots[-1].get('label', snapshots[-1].get('_filename', ''))}**")
    mo.ui.table(detail_rows)
    return


# ── NDCG ──

@app.cell
def __(math):
    def ndcg(retrieved, graded):
        if not graded:
            return 1.0
        k = 5
        rels = [graded.get(t, 0) for t in retrieved[:k]]
        rels = (rels + [0] * k)[:k]
        ideal = sorted(graded.values(), reverse=True)[:k]
        ideal = (ideal + [0] * k)[:k]
        def _d(ss):
            return sum(s / math.log2(i + 2) for i, s in enumerate(ss))
        t = _d(ideal)
        return _d(rels) / t if t > 0 else 1.0

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
    return (GRADED, ndcg)


@app.cell
def __(GRADED, ndcg, snapshots, statistics):
    nd_rows = []
    if snapshots:
        for _q in snapshots[-1].get("per_query", []):
            if _q.get("relevant_count", 0) == 0:
                continue
            _grades = GRADED.get(_q["query"], {})
            if _grades:
                _n = ndcg(_q.get("retrieved_titles", []), _grades)
                nd_rows.append({"Query": _q["query"], "NDCG@5": _n})
    nd_avg = statistics.mean(r["NDCG@5"] for r in nd_rows) if nd_rows else 0
    return (nd_avg, nd_rows)


@app.cell
def __(mo, nd_avg, nd_rows):
    mo.md("---")
    mo.md("## Aspirational: NDCG@5")
    mo.ui.table(
        [{"Query": r["Query"], "NDCG@5": f"{r['NDCG@5']:.2f}"} for r in nd_rows]
        + [{"Query": "AVERAGE", "NDCG@5": f"{nd_avg:.2f}"}]
    )
    mo.callout(
        f"Average NDCG@5: **{nd_avg:.2f}**. Improves with better ranking. Target: ≥0.90.",
        kind="info",
    )
    return


@app.cell
def __(mo):
    mo.md(
        "## Aspirational\n\n"
        "**Title-aware snippets** — 81% currently. Extending `_extract_snippet()` "
        "to check page titles would close the gap to 100%.\n\n"
        "**Wikilink navigability** — 0% currently. `[[wikilinks]]` not yet "
        "extracted. Implement the wikilink graph spec to unlock backlink "
        "navigation and ranking."
    )
    return


if __name__ == "__main__":
    app.run()
