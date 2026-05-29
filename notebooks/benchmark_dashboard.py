"""DuckBrain Search Benchmark Dashboard.

Developer-only tool — not shipped with DuckBrain.
Run with: uv run marimo edit notebooks/benchmark_dashboard.py

Loads all labeled snapshots from tests/benchmarks/snapshots/ and renders
actual vs. aspirational metrics with version annotations. Save a new
snapshot with:

    uv run python tests/benchmarks/search_quality.py --label "my-change"
"""

import json
import math
import statistics
from pathlib import Path

import altair as alt
import marimo

__generated_with = "0.23.8"
app = marimo.App(title="DuckBrain Search Benchmark")


@app.cell
def __():
    import marimo as mo
    return (mo,)


@app.cell
def __(mo):
    mo.md(
        """
        # DuckBrain Search Benchmark Dashboard

        Developer dashboard for search quality metrics. Not shipped with DuckBrain.

        Run: `uv run marimo edit notebooks/benchmark_dashboard.py`

        Save snapshots: `uv run python tests/benchmarks/search_quality.py --label "description"`
        """
    )
    return


@app.cell
def __():
    def load_baselines() -> list[dict]:
        """Load all labeled snapshots from snapshots/ directory, sorted by sequence."""
        snapshots_dir = (
            Path(__file__).parent.parent / "tests" / "benchmarks" / "snapshots"
        )
        snapshots: list[dict] = []

        for path in sorted(snapshots_dir.glob("*.json")):
            data = json.loads(path.read_text())
            data["_filename"] = path.name
            snapshots.append(data)

        # Also load the current baseline.json if it exists
        current_path = (
            Path(__file__).parent.parent / "tests" / "benchmarks" / "baseline.json"
        )
        if current_path.exists():
            current = json.loads(current_path.read_text())
            current["_filename"] = "current (baseline.json)"
            snapshots.append(current)

        return snapshots

    snapshots = load_baselines()
    return load_baselines, snapshots


@app.cell
def __(mo, snapshots):
    mo.md(f"**{len(snapshots)} snapshot(s)** loaded from `tests/benchmarks/snapshots/`")
    return


@app.cell
def __():
    # ── NDCG computation (aspirational metric) ──

    def dcg(scores: list[int]) -> float:
        return sum(s / math.log2(i + 2) for i, s in enumerate(scores))

    def ndcg(retrieved_titles: list[str], graded_rels: dict[str, int]) -> float:
        if not graded_rels:
            return 1.0
        k = 5
        rels = [graded_rels.get(t, 0) for t in retrieved_titles[:k]]
        rels = (rels + [0] * k)[:k]
        ideal = sorted(graded_rels.values(), reverse=True)[:k]
        ideal = (ideal + [0] * k)[:k]
        return dcg(rels) / dcg(ideal) if dcg(ideal) > 0 else 1.0

    GRADED_RELS = {
        "memory": {
            "Claude Mem": 3, "Agent Memory Systems": 3,
            "duckdb-memory-mcp-build-decision": 2, "The LLM Wiki Concept": 1,
        },
        "MCP": {
            "Claude Mem": 3, "duckdb-memory-mcp-build-decision": 3, "2026-05-28": 1,
        },
        "DuckDB": {
            "Agent Memory Systems": 2, "duckdb-memory-mcp-build-decision": 3,
            "Knowledge Graph Architecture": 2,
        },
        "graph": {"Knowledge Graph Architecture": 3, "The LLM Wiki Concept": 1},
        "knowledge graph": {"Knowledge Graph Architecture": 3},
        "Jagged Frontier": {"Jagged Frontier": 3},
        "metrics layer": {"The missing piece of the modern data stack": 3},
    }
    return GRADED_RELS, dcg, ndcg


@app.cell
def __(mo, snapshots):
    # ── Snapshot summary table ──
    mo.md("## Snapshots")

    label_rows = []
    for s in snapshots:
        label_rows.append({
            "File": s.get("_filename", "—"),
            "Label": s.get("label", "—"),
            "Commit": s.get("commit", "—")[:8],
            "Snip%": f"{s.get('averages', {}).get('snippet_containment', 0):.0%}",
            "P@5": f"{s.get('averages', {}).get('precision_at_5', 0):.2f}",
            "Score": f"{s.get('averages', {}).get('score_avg', 0):.2f}" if s.get("averages", {}).get("score_avg") else "N/A",
        })

    mo.ui.table(label_rows)
    return label_rows,


@app.cell
def __(alt, mo, snapshots):
    # ── Snippet containment across snapshots ──
    mo.md("### Snippet Containment Over Time")

    snip_versions = []
    for s in snapshots:
        label = s.get("label") or s.get("_filename", "—")
        avg = s.get("averages", {}).get("snippet_containment")
        if avg is not None:
            snip_versions.append({"Version": label, "Snippet Containment": avg})

    if snip_versions:
        chart = (
            alt.Chart(alt.Data(values=snip_versions))
            .mark_bar()
            .encode(
                x=alt.X("Snippet Containment:Q", scale=alt.Scale(domain=[0, 1]),
                        axis=alt.Axis(format="%"), title=""),
                y=alt.Y("Version:N", sort=None, title=""),
                color=alt.Color("Version:N", legend=None),
                tooltip=["Version", "Snippet Containment"],
            )
            .properties(height=40 + len(snip_versions) * 30)
        )
        mo.ui.altair_chart(chart)
    return chart, snip_versions


@app.cell
def __(alt, mo, snapshots):
    # ── P@5 across snapshots ──
    mo.md("### Precision@5 Over Time")

    p5_versions = []
    for s in snapshots:
        label = s.get("label") or s.get("_filename", "—")
        avg = s.get("averages", {}).get("precision_at_5")
        if avg is not None:
            p5_versions.append({"Version": label, "P@5": avg})

    if p5_versions:
        chart = (
            alt.Chart(alt.Data(values=p5_versions))
            .mark_bar()
            .encode(
                x=alt.X("P@5:Q", scale=alt.Scale(domain=[0, 1]), title=""),
                y=alt.Y("Version:N", sort=None, title=""),
                color=alt.Color("Version:N", legend=None),
                tooltip=["Version", "P@5"],
            )
            .properties(height=40 + len(p5_versions) * 30)
        )
        mo.ui.altair_chart(chart)
    return chart, p5_versions


@app.cell
def __(mo, snapshots):
    # ── Latest snapshot detail ──
    if not snapshots:
        return

    latest = snapshots[-1]
    mo.md("## Latest Snapshot — Per-Query Detail")
    mo.md(f"**{latest.get('label', latest.get('_filename', ''))}**")

    detail_rows = []
    for q in latest["per_query"]:
        if q["relevant_count"] == 0:
            continue
        detail_rows.append({
            "Query": q["query"],
            "P@5": f"{q['precision_at_5']:.2f}",
            "R@5": f"{q['recall_at_5']:.2f}",
            "Snippet": f"{q['snippet_containment']:.0%}",
            "Score (avg)": f"{q['score_avg']:.3f}" if q["score_avg"] else "N/A",
            "Results": q["retrieved_count"],
        })
    mo.ui.table(detail_rows)
    return detail_rows, latest


@app.cell
def __(GRADED_RELS, mo, ndcg, snapshots):
    # ── NDCG aspirational ──
    mo.md("---")
    mo.md("## Aspirational: NDCG@5")

    if not snapshots:
        return

    latest = snapshots[-1]
    ndcg_rows = []
    for q in latest["per_query"]:
        if q["relevant_count"] == 0:
            continue
        grades = GRADED_RELS.get(q["query"], {})
        if grades:
            n = ndcg(q["retrieved_titles"], grades)
            ndcg_rows.append({"Query": q["query"], "NDCG@5": n})
    avg_ndcg = statistics.mean(r["NDCG@5"] for r in ndcg_rows)

    if ndcg_rows:
        mo.ui.table(
            [{"Query": r["Query"], "NDCG@5": f"{r['NDCG@5']:.2f}"} for r in ndcg_rows]
            + [{"Query": "AVERAGE", "NDCG@5": f"{avg_ndcg:.2f}"}]
        )
        mo.callout(
            f"Average NDCG@5: **{avg_ndcg:.2f}**. "
            "Improves with better ranking (wikilink boost, title-aware snippets). "
            "Target: ≥0.90.",
            kind="info",
        )
    return avg_ndcg, grades, latest, n, ndcg_rows


@app.cell
def __(mo):
    mo.md("## Aspirational: Title-Aware Snippets")
    mo.md(
        "Currently 81% — queries like 'Jagged Frontier' match via title FTS "
        "but the snippet comes from body text where 'Jagged' doesn't appear. "
        "Extending `_extract_snippet()` to check the page title would close "
        "this gap to 100%."
    )
    return


@app.cell
def __(mo):
    mo.md(
        """
        ## Aspirational: Wikilink Navigability

        Not yet measurable — `[[wikilinks]]` are not extracted. Once the
        wikilink graph spec is implemented:

        - **% of relevant pages with ≥1 backlink** → navigability signal
        - **Average backlink count per result** → link density score
        - **Graph distance to best result** → hops from a known page

        Currently **0%** across all queries (no link data).
        """
    )
    return


if __name__ == "__main__":
    app.run()
