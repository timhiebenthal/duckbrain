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
    return (mo,)


@app.cell
def __():
    import json
    import math
    import statistics
    from pathlib import Path
    import altair as alt
    return (alt, json, math, statistics, Path)


@app.cell
def __(Path, json):
    d = Path(__file__).parent.parent / "tests" / "benchmarks" / "snapshots"
    snaps = []
    for sp in sorted(d.glob("*.json")):
        item = json.loads(sp.read_text())
        item["_filename"] = sp.name
        snaps.append(item)
    curp = Path(__file__).parent.parent / "tests" / "benchmarks" / "baseline.json"
    if curp.exists():
        cur = json.loads(curp.read_text())
        cur["_filename"] = "current (baseline.json)"
        snaps.append(cur)
    snapshots = snaps
    return (snapshots,)


@app.cell
def __(mo, snapshots):
    mo.md("""# DuckBrain Search Benchmark Dashboard""")
    mo.md(f"**{len(snapshots)} snapshot(s)** from `tests/benchmarks/snapshots/`")
    mo.md("Save: `uv run python tests/benchmarks/search_quality.py --label \"change\"`")
    return


@app.cell
def __(math):
    def dcg(scores):
        return sum(s / math.log2(i + 2) for i, s in enumerate(scores))

    def ndcg(retrieved, graded):
        if not graded:
            return 1.0
        k = 5
        rels = [graded.get(t, 0) for t in retrieved[:k]]
        rels = (rels + [0] * k)[:k]
        ideal = sorted(graded.values(), reverse=True)[:k]
        ideal = (ideal + [0] * k)[:k]
        t = dcg(ideal)
        return dcg(rels) / t if t > 0 else 1.0

    GRADED_RELS = {
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
    return (GRADED_RELS, dcg, ndcg)


@app.cell
def __(mo, snapshots):
    mo.md("## Snapshots")
    trows = []
    for st in snapshots:
        st_avg = st.get("averages", {}) if isinstance(st.get("averages"), dict) else {}
        st_score = st_avg.get("score_avg")
        trows.append({
            "File": st.get("_filename", "—"),
            "Label": st.get("label", "—"),
            "Commit": str(st.get("commit", "—"))[:8],
            "Snip%": f"{st_avg.get('snippet_containment', 0):.0%}",
            "P@5": f"{st_avg.get('precision_at_5', 0):.2f}",
            "Score": f"{st_score:.2f}" if st_score else "N/A",
        })
    mo.ui.table(trows)
    return (trows,)


@app.cell
def __(alt, mo, snapshots):
    mo.md("### Snippet Containment Over Time")
    sc_data = []
    for sc_snap in snapshots:
        sc_lbl = sc_snap.get("label") or sc_snap.get("_filename", "—")
        sc_avg = sc_snap.get("averages", {}) if isinstance(sc_snap.get("averages"), dict) else {}
        sc_v = sc_avg.get("snippet_containment")
        if sc_v is not None:
            sc_data.append({"label": sc_lbl, "value": sc_v})
    if sc_data:
        sc_chart = (
            alt.Chart(alt.Data(values=sc_data))
            .mark_bar()
            .encode(
                x=alt.X("value:Q", scale=alt.Scale(domain=[0, 1]),
                        axis=alt.Axis(format="%"), title="Snippet Containment"),
                y=alt.Y("label:N", sort=None, title=None),
                color=alt.Color("label:N", legend=None),
            )
            .properties(height=max(60, 30 * len(sc_data)))
        )
        mo.ui.altair_chart(sc_chart)
    return


@app.cell
def __(alt, mo, snapshots):
    mo.md("### Precision@5 Over Time")
    p5data = []
    for p5snap in snapshots:
        p5lbl = p5snap.get("label") or p5snap.get("_filename", "—")
        p5avg = p5snap.get("averages", {}) if isinstance(p5snap.get("averages"), dict) else {}
        p5v = p5avg.get("precision_at_5")
        if p5v is not None:
            p5data.append({"label": p5lbl, "value": p5v})
    if p5data:
        p5chart = (
            alt.Chart(alt.Data(values=p5data))
            .mark_bar()
            .encode(
                x=alt.X("value:Q", scale=alt.Scale(domain=[0, 1]), title="P@5"),
                y=alt.Y("label:N", sort=None, title=None),
                color=alt.Color("label:N", legend=None),
            )
            .properties(height=max(60, 30 * len(p5data)))
        )
        mo.ui.altair_chart(p5chart)
    return


@app.cell
def __(mo, snapshots):
    mo.md("## Latest Snapshot — Per-Query Detail")
    det_rows = []
    if snapshots:
        latest_snap = snapshots[-1]
        mo.md(f"**{latest_snap.get('label', latest_snap.get('_filename', ''))}**")
        for rq in latest_snap.get("per_query", []):
            if rq.get("relevant_count", 0) == 0:
                continue
            det_rows.append({
                "Query": rq["query"],
                "P@5": f"{rq['precision_at_5']:.2f}",
                "R@5": f"{rq['recall_at_5']:.2f}",
                "Snippet": f"{rq['snippet_containment']:.0%}",
                "Score (avg)": f"{rq['score_avg']:.3f}" if rq.get("score_avg") else "N/A",
                "Results": rq["retrieved_count"],
            })
        mo.ui.table(det_rows)
    return


@app.cell
def __(GRADED_RELS, mo, ndcg, snapshots, statistics):
    mo.md("---")
    mo.md("## Aspirational: NDCG@5")
    if snapshots:
        nd_latest = snapshots[-1]
        ndrows = []
        for nrq in nd_latest.get("per_query", []):
            if nrq.get("relevant_count", 0) == 0:
                continue
            grades = GRADED_RELS.get(nrq["query"], {})
            if grades:
                n = ndcg(nrq.get("retrieved_titles", []), grades)
                ndrows.append({"Query": nrq["query"], "NDCG@5": n})
        if ndrows:
            ndavg = statistics.mean(r["NDCG@5"] for r in ndrows)
            mo.ui.table(
                [{"Query": r["Query"], "NDCG@5": f"{r['NDCG@5']:.2f}"} for r in ndrows]
                + [{"Query": "AVERAGE", "NDCG@5": f"{ndavg:.2f}"}]
            )
            mo.callout(
                f"Average NDCG@5: **{ndavg:.2f}**. "
                "Improves with better ranking (wikilink boost, snippets). "
                "Target: ≥0.90.",
                kind="info",
            )
    return


@app.cell
def __(mo):
    mo.md("## Aspirational: Title-Aware Snippets")
    mo.md("Currently 81%. Extending snippet extraction to page titles would close the gap to 100%.")
    return


@app.cell
def __(mo):
    mo.md("""## Aspirational: Wikilink Navigability
Not measurable yet — [[wikilinks]] not extracted. Currently 0%.""")
    return


if __name__ == "__main__":
    app.run()
