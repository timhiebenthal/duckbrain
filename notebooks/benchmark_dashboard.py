"""DuckBrain Search Benchmark Dashboard.

Developer-only tool — not shipped with DuckBrain.
Run with: uv run marimo edit notebooks/benchmark_dashboard.py

Shows current benchmark metrics, before/after deltas from baseline.before.json,
and aspirational metrics that are out of scope today but trackable for future
iterations (title-aware snippets, wikilink navigability, NDCG ranking quality).
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

        - **Actual metrics** — green = implemented, amber = needs work
        - **Aspirational metrics** — gray = not yet implemented, shows headroom for future iterations
        - **Before/After delta** — comparison against the saved baseline snapshot
        """
    )
    return


@app.cell
def __():
    def load_baseline(name: str) -> dict:
        path = Path(__file__).parent.parent / "tests" / "benchmarks" / f"{name}.json"
        return json.loads(path.read_text())

    current = load_baseline("baseline")
    previous = load_baseline("baseline.before")

    before_by_query = {q["query"]: q for q in previous["per_query"]}

    rows = []
    for q in current["per_query"]:
        b = before_by_query.get(q["query"], {})
        rows.append({
            "query": q["query"],
            "relevant_count": q["relevant_count"],
            "P5_before": b.get("precision_at_5"),
            "P5_after": q["precision_at_5"],
            "R5_before": b.get("recall_at_5"),
            "R5_after": q["recall_at_5"],
            "MRR_before": b.get("mrr"),
            "MRR_after": q["mrr"],
            "Snip_before": b.get("snippet_containment"),
            "Snip_after": q["snippet_containment"],
            "Score_avg": q["score_avg"],
            "retrieved": q["retrieved_count"],
            "retrieved_titles": q.get("retrieved_titles", []),
        })

    has_before = any(r["Snip_before"] is not None for r in rows)
    return current, previous, rows, has_before


@app.cell
def __(current, mo):
    mo.md(
        f"""
        **Dataset:** {current['dataset']['total_pages']} pages,
        {current['dataset']['total_queries']} queries
        ({current['dataset']['queries_with_relevant']} with ≥1 relevant doc)

        **Commit:** `{current['commit'][:8]}`
        """
    )
    return


@app.cell
def __(alt, mo, rows):
    mo.md("## Actual Metrics")

    # ── Snippet containment bar chart ──
    relevant_rows = [r for r in rows if r["relevant_count"] > 0]
    snip_data = [{"query": r["query"], "Snippet Containment": r["Snip_after"]} for r in relevant_rows]
    avg_snip = statistics.mean(d["Snippet Containment"] for d in snip_data)
    snip_data.append({"query": "AVERAGE", "Snippet Containment": avg_snip})

    chart = (
        alt.Chart(alt.Data(values=snip_data))
        .mark_bar()
        .encode(
            x=alt.X("Snippet Containment:Q", scale=alt.Scale(domain=[0, 1]),
                    axis=alt.Axis(format="%"), title=""),
            y=alt.Y("query:N", sort=None, title=""),
            color=alt.condition(
                alt.datum["Snippet Containment"] >= 0.90,
                alt.value("#22c55e"),
                alt.value("#f59e0b"),
            ),
            tooltip=["query", "Snippet Containment"],
        )
        .properties(title="Snippet Containment (body match in context)", height=200)
    )

    mo.ui.altair_chart(chart)

    # ── P@5 bar chart ──
    p5_data = [{"query": r["query"], "P@5": r["P5_after"]} for r in relevant_rows]
    avg_p5 = statistics.mean(d["P@5"] for d in p5_data)
    p5_data.append({"query": "AVERAGE", "P@5": avg_p5})

    chart = (
        alt.Chart(alt.Data(values=p5_data))
        .mark_bar()
        .encode(
            x=alt.X("P@5:Q", scale=alt.Scale(domain=[0, 1]), title=""),
            y=alt.Y("query:N", sort=None, title=""),
            color=alt.condition(
                alt.datum["P@5"] >= 0.80,
                alt.value("#22c55e"),
                alt.value("#f59e0b"),
            ),
            tooltip=["query", "P@5"],
        )
        .properties(title="Precision@5", height=200)
    )

    mo.ui.altair_chart(chart)
    return avg_p5, avg_snip, chart, p5_data, relevant_rows, snip_data


@app.cell
def __(mo, rows):
    # ── Scores table ──
    score_data = []
    for r in rows:
        if r["relevant_count"] > 0:
            score_data.append({
                "Query": r["query"],
                "Score (avg)": f"{r['Score_avg']:.3f}" if r["Score_avg"] else "N/A",
                "Results": r["retrieved"],
            })

    mo.md("### BM25 Scores")
    mo.ui.table(score_data)
    return score_data,


@app.cell
def __(mo):
    mo.md(
        """
        ---
        ## Aspirational Metrics

        These measure capabilities **not yet implemented**. Currently at or near
        zero — will only improve with future feature work. This ensures the
        benchmark has headroom; maxing out at 100% too early hides progress.
        """
    )
    return


@app.cell
def __():
    # ── NDCG computation ──

    def dcg(scores: list[int]) -> float:
        """Discounted Cumulative Gain."""
        return sum(s / math.log2(i + 2) for i, s in enumerate(scores))

    def ndcg(retrieved_titles: list[str], graded_rels: dict[str, int]) -> float:
        """NDCG for top-5 results.

        graded_rels maps title → relevance grade (3=high, 2=relevant, 1=marginal, 0=none).
        """
        if not graded_rels:
            return 1.0
        k = 5
        rels = [graded_rels.get(t, 0) for t in retrieved_titles[:k]]
        # Pad or truncate to k
        rels = (rels + [0] * k)[:k]
        ideal = sorted(graded_rels.values(), reverse=True)[:k]
        ideal = (ideal + [0] * k)[:k]
        return dcg(rels) / dcg(ideal) if dcg(ideal) > 0 else 1.0

    # Graded relevance for each query (3=best answer, 2=good, 1=ok, 0=irrelevant)
    GRADED_RELS = {
        "memory": {
            "Claude Mem": 3,
            "Agent Memory Systems": 3,
            "duckdb-memory-mcp-build-decision": 2,
            "The LLM Wiki Concept": 1,
        },
        "MCP": {
            "Claude Mem": 3,
            "duckdb-memory-mcp-build-decision": 3,
            "2026-05-28": 1,
        },
        "DuckDB": {
            "Agent Memory Systems": 2,
            "duckdb-memory-mcp-build-decision": 3,
            "Knowledge Graph Architecture": 2,
        },
        "graph": {
            "Knowledge Graph Architecture": 3,
            "The LLM Wiki Concept": 1,
        },
        "knowledge graph": {
            "Knowledge Graph Architecture": 3,
        },
        "Jagged Frontier": {
            "Jagged Frontier": 3,
        },
        "metrics layer": {
            "The missing piece of the modern data stack": 3,
        },
    }
    return GRADED_RELS, dcg, ndcg


@app.cell
def __(GRADED_RELS, alt, mo, ndcg, rows):
    # ── NDCG aspirational chart ──
    ndcg_data = []
    for r in rows:
        if r["relevant_count"] == 0:
            continue
        grades = GRADED_RELS.get(r["query"], {})
        if grades:
            n = ndcg(r["retrieved_titles"], grades)
            ndcg_data.append({"query": r["query"], "NDCG@5": n})
    avg_ndcg = statistics.mean(d["NDCG@5"] for d in ndcg_data)
    ndcg_data.append({"query": "AVERAGE", "NDCG@5": avg_ndcg})

    chart = (
        alt.Chart(alt.Data(values=ndcg_data))
        .mark_bar()
        .encode(
            x=alt.X("NDCG@5:Q", scale=alt.Scale(domain=[0, 1]), title=""),
            y=alt.Y("query:N", sort=None, title=""),
            color=alt.condition(
                alt.datum["NDCG@5"] >= 0.90,
                alt.value("#22c55e"),
                alt.value("#d1d5db"),  # gray = aspirational target area
            ),
            tooltip=["query", "NDCG@5"],
        )
        .properties(title="NDCG@5 (aspirational — needs graded relevance benchmark)", height=180)
    )

    mo.md("### NDCG — Normalized Discounted Cumulative Gain")
    mo.md(
        "Measures ranking quality: highly relevant results at the top score better. "
        "A proper benchmark needs graded relevance judgments (not just binary). "
        "Currently uses hand-labeled grades from the dashboard — not automated."
    )
    mo.ui.altair_chart(chart)
    mo.callout(
        f"Average NDCG@5: **{avg_ndcg:.2f}**. Scores improve with better ranking "
        "(wikilink boost, hybrid search). Target: ≥0.90.",
        kind="info",
    )
    return avg_ndcg, chart, grades, n, ndcg_data


@app.cell
def __(mo, rows):
    # ── Title-aware snippet gap ──
    gap_queries = []
    for r in rows:
        if r["relevant_count"] == 0:
            continue
        if r["Snip_after"] < 0.95:
            gap_queries.append(r)

    mo.md("### Title-Aware Snippet Containment")

    if gap_queries:
        gap_text = "\n".join(
            f"- **{g['query']}**: {g['Snip_after']:.0%} (match is in page title, not body)"
            for g in gap_queries
        )
        mo.md(
            f"**{len(gap_queries)} quer(ies)** with body-only snippet misses.\n\n{gap_text}"
        )
        mo.callout(
            "Fix: extend `_extract_snippet()` to also search the page title for "
            "query terms. When a title match is found but no body match exists, "
            "show body start with a `[title match]` prefix. This would close "
            "the remaining 19% gap to 100%.",
            kind="warn",
        )
    else:
        mo.md("No title-only misses — all queries hit ≥95% body-snippet containment.")
    return gap_queries, gap_text


@app.cell
def __(mo):
    mo.md(
        """
        ### Wikilink Navigability

        Not yet measurable — `[[wikilinks]]` are not extracted. Once the wikilink
        graph spec is implemented, this would show:

        - **% of relevant pages with ≥1 backlink**: navigability signal
        - **Average backlink count per result**: link density score
        - **Graph distance to best result**: how many hops from a known page

        Currently: **0% across all queries** (no link data).
        """
    )
    return


@app.cell
def __(mo):
    mo.md(
        """
        | Metric | Current | Target | Blocked by |
        |---|---|---|---|
        | Title-aware snippet | 81% | 100% | `_extract_snippet` only checks body |
        | NDCG@5 | ~0.85 | >0.90 | Graded relevance + ranking improvements |
        | Wikilink navigability | 0% | >50% | `[[wikilinks]]` not extracted |
        | Backlink-boosted ranking | 0% | P@5 ≥0.90 | Wikilink graph data |
        """
    )
    return


@app.cell
def __(has_before, mo, rows):
    mo.md("---")
    mo.md("## Before → After Delta")

    if has_before:
        delta_rows = []
        for r in rows:
            if r["relevant_count"] == 0:
                continue
            sb = f"{r['Snip_before']:.0%}" if r["Snip_before"] is not None else "—"
            sa = f"{r['Snip_after']:.0%}"
            pb = f"{r['P5_before']:.2f}" if r["P5_before"] is not None else "—"
            pa = f"{r['P5_after']:.2f}"
            delta_rows.append({
                "Query": r["query"],
                "Snip before": sb,
                "Snip after": sa,
                "P@5 before": pb,
                "P@5 after": pa,
                "Score": f"{r['Score_avg']:.3f}" if r["Score_avg"] else "—",
            })

        # Averages row
        avg_snip_before = statistics.mean(
            r["Snip_before"] for r in rows if r["relevant_count"] > 0 and r["Snip_before"] is not None
        )
        avg_snip_after = statistics.mean(
            r["Snip_after"] for r in rows if r["relevant_count"] > 0
        )
        delta_rows.append({
            "Query": "**AVERAGE**",
            "Snip before": f"{avg_snip_before:.0%}",
            "Snip after": f"{avg_snip_after:.0%}",
            "P@5 before": "—",
            "P@5 after": "—",
            "Score": "—",
        })

        mo.ui.table(delta_rows)
    else:
        mo.md("*No before/after comparison — save a baseline first.*")
    return avg_snip_after, avg_snip_before, delta_rows


if __name__ == "__main__":
    app.run()
