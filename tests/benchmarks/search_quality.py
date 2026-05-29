"""Search quality benchmark for DuckBrain.

Measures BM25 search precision, recall, MRR, and snippet quality
against a known set of queries and ground-truth relevant pages.

Usage:
    uv run python tests/benchmarks/search_quality.py                    # save as baseline.json only
    uv run python tests/benchmarks/search_quality.py --label "v0.2"    # also save labeled snapshot

Labeled snapshots go to tests/benchmarks/baselines/<NNN>-<label>.json
and persist for comparison across versions.
"""

import argparse
import json
import re
import statistics
from pathlib import Path
from typing import Any

from duckbrain import PageMetadata
from duckbrain.indexer import build_fts_index, search

# ── Sample dataset ────────────────────────────────────────────────────────────

SAMPLE_PAGES: list[PageMetadata] = [
    # 0: Short body — query terms early
    PageMetadata(
        filepath="wiki/entities/claude-mem.md",
        title="Claude Mem",
        kind="entity",
        tags=["open-source", "ai", "memory", "mcp"],
        body=(
            "Claude Mem is an MCP-based memory plugin that provides persistent memory "
            "across sessions for OpenCode."
        ),
        created="2026-05-28",
        updated="2026-05-28",
    ),
    # 1: Medium body — query terms early
    PageMetadata(
        filepath="wiki/concepts/agent-memory-systems.md",
        title="Agent Memory Systems",
        kind="concept",
        tags=["agent-memory", "taxonomy", "ai"],
        body="A 6-level taxonomy of Claude Code memory approaches. Includes DuckDB Zero-ETL.",
        created="2026-05-28",
        updated="2026-05-28",
    ),
    # 2: Short body — unique term (title term not in body: "Jagged" not in body text)
    PageMetadata(
        filepath="wiki/concepts/jagged-frontier.md",
        title="Jagged Frontier",
        kind="concept",
        tags=["ai", "llm", "capability"],
        body=(
            "Uneven LLM capability across tasks — some things are easy "
            "for AI, others unexpectedly hard."
        ),
        created="2026-05-04",
        updated="2026-05-20",
    ),
    # 3: Medium body — mixed terms
    PageMetadata(
        filepath="wiki/synthesis/duckdb-memory-mcp-build-decision.md",
        title="duckdb-memory-mcp-build-decision",
        kind="synthesis",
        tags=["agent-memory", "duckdb", "mcp", "comparison"],
        body=(
            "Verdict: Build a minimal DuckDB MCP server. Existing tools fail "
            "on vault schema-aware write-back."
        ),
        created="2026-05-28",
        updated="2026-05-28",
    ),
    # 4: Short body — specific term
    PageMetadata(
        filepath="wiki/sources/the-missing-piece-of-the-modern-data-stack.md",
        title="The missing piece of the modern data stack",
        kind="source",
        tags=["metrics-layer", "mds"],
        body="Benn Stancil on the metrics layer as the missing MDS component.",
        created="2026-05-20",
        updated="2026-05-20",
    ),
    # 5: Short body — daily
    PageMetadata(
        filepath="daily/2026-05-28.md",
        title="2026-05-28",
        kind="daily",
        tags=[],
        body="Worked on DuckBrain MCP server.",
        created="2026-05-28",
        updated="2026-05-28",
    ),
    # 6: LONG body — query term buried past char 100
    PageMetadata(
        filepath="wiki/concepts/knowledge-graph-architecture.md",
        title="Knowledge Graph Architecture",
        kind="concept",
        tags=["knowledge-graph", "architecture", "graphrag"],
        body=(
            "This document explores the architectural choices behind modern "
            "data systems. We begin with a taxonomy of database paradigms, "
            "covering relational stores, document databases, and columnar "
            "engines. Each paradigm has trade-offs in query expressiveness, "
            "write throughput, and horizontal scalability. The second section "
            "examines index structures: B-trees, LSM trees, inverted indices, "
            "and bitmap indexes. We then compare query languages — SQL, MQL, "
            "and GQL — evaluating their ergonomics for analytical workloads. "
            "The third section introduces the concept of a knowledge graph: "
            "a structured representation of entities, their attributes, and "
            "the relationships between them. Knowledge graphs enable semantic "
            "querying that goes beyond keyword matching, supporting path "
            "traversal, subgraph matching, and inference. The final section "
            "builds a reference architecture that combines DuckDB for analytical "
            "queries with a graph overlay for relationship traversal."
        ),
        created="2026-05-29",
        updated="2026-05-29",
    ),
    # 7: LONG body — query term in middle
    PageMetadata(
        filepath="wiki/concepts/llm-wiki-concept.md",
        title="The LLM Wiki Concept",
        kind="concept",
        tags=["llm", "wiki", "ai-agent"],
        body=(
            "An LLM Wiki is a markdown knowledge base that an AI agent reads, "
            "writes, and maintains. Unlike traditional wikis edited by humans, "
            "an LLM Wiki is structured for machine consumption: consistent "
            "frontmatter, explicit wikilink graphs, and semantic tag taxonomies. "
            "The key innovation is treating the wiki as the agent's long-term "
            "memory substrate — every learning, every decision, every discovery "
            "becomes a persistent, searchable page. The search mechanism must "
            "support both keyword lookups for precise retrieval and semantic "
            "browsing for serendipitous discovery. This page describes the "
            "design principles behind the LLM Wiki pattern."
        ),
        created="2026-05-28",
        updated="2026-05-28",
    ),
]

# ── Query definitions with ground truth ───────────────────────────────────────
# "relevant" lists the titles of pages that SHOULD appear in results.
# Snippet containment is measured for ALL relevant results — the current
# body[:100] approach is expected to miss terms buried deep in long bodies.

QUERIES: list[dict[str, Any]] = [
    {
        "query": "memory",
        "relevant": [
            "Claude Mem",
            "Agent Memory Systems",
            "duckdb-memory-mcp-build-decision",
        ],
    },
    {
        "query": "MCP",
        "relevant": [
            "Claude Mem",
            "duckdb-memory-mcp-build-decision",
            "2026-05-28",
        ],
    },
    {
        "query": "DuckDB",
        "relevant": [
            "Agent Memory Systems",
            "duckdb-memory-mcp-build-decision",
            "Knowledge Graph Architecture",
        ],
    },
    {
        "query": "graph",
        "relevant": [
            "Knowledge Graph Architecture",
        ],
    },
    {
        "query": "knowledge graph",
        "relevant": [
            "Knowledge Graph Architecture",
        ],
    },
    {
        "query": "Jagged Frontier",
        "relevant": [
            "Jagged Frontier",
        ],
    },
    {
        "query": "metrics layer",
        "relevant": [
            "The missing piece of the modern data stack",
        ],
    },
    {
        "query": "nonexistent_term_xyz",
        "relevant": [],
    },
]


# ── Metrics computation ───────────────────────────────────────────────────────


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of top-k results that are relevant."""
    if k == 0:
        return 1.0
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    rel_set = set(relevant)
    return len([t for t in top_k if t in rel_set]) / len(top_k)


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of all relevant docs captured in top-k results."""
    if not relevant:
        return 1.0
    top_k = retrieved[:k]
    rel_set = set(relevant)
    return len([t for t in top_k if t in rel_set]) / len(relevant)


def mean_reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
    """1 / rank of first relevant result, or 0 if none found."""
    if not relevant:
        return 1.0
    rel_set = set(relevant)
    for i, title in enumerate(retrieved, start=1):
        if title in rel_set:
            return 1.0 / i
    return 0.0


def snippet_containment(
    results: list[dict[str, Any]], query: str, relevant_titles: list[str]
) -> float:
    """Fraction of relevant results whose snippet contains any query term.

    Measures how well the current snippet extraction (body[:100])
    captures the search context. A low score means matched terms are
    buried deep in body text — the main motivation for context-aware snippets.
    """
    if not relevant_titles:
        return 1.0
    rel_set = set(relevant_titles)
    query_terms = query.lower().split()
    hit_count = 0
    for r in results:
        if r["title"] in rel_set:
            snippet_lower = r["snippet"].lower()
            if any(term in snippet_lower for term in query_terms):
                hit_count += 1
    return hit_count / len(relevant_titles)


# ── Report formatting ─────────────────────────────────────────────────────────


def print_report(metrics: dict[str, Any], commit_hash: str) -> None:
    """Print a formatted benchmark report."""
    print()
    print("═" * 66)
    print("  DuckBrain Search Quality Benchmark")
    print(f"  Baseline: {commit_hash[:8]}")
    print("═" * 66)
    print()
    print(
        f"Dataset: {metrics['dataset']['total_pages']} pages, "
        f"{metrics['dataset']['total_queries']} queries"
    )
    print()

    # Per-query table
    header = (
        f"{'Query':<22} {'P@5':>5}  {'R@5':>5}  {'MRR':>5}  "
        f"{'Snip%':>6}  {'Score(avg)':>9}"
    )
    print("─" * 66)
    print(header)
    print("─" * 66)

    for qm in metrics["per_query"]:
        p5 = qm["precision_at_5"]
        r5 = qm["recall_at_5"]
        mrr = qm["mrr"]
        sc = qm["snippet_containment"]
        sa = qm["score_avg"]
        score_str = f"{sa:>9.3f}" if sa is not None else "      N/A"
        print(
            f"{qm['query']:<22} "
            f"{p5:>4.2f}  "
            f"{r5:>4.2f}  "
            f"{mrr:>4.2f}  "
            f"{sc:>5.1%}  "
            f"{score_str}"
        )

    print("─" * 66)

    # Averages (only queries with at least one relevant doc)
    avg = metrics["averages"]
    score_str = f"{avg['score_avg']:>9.3f}" if avg["score_avg"] is not None else "      N/A"
    print(
        f"{'AVERAGE':<22} "
        f"{avg['precision_at_5']:>4.2f}  "
        f"{avg['recall_at_5']:>4.2f}  "
        f"{avg['mrr']:>4.2f}  "
        f"{avg['snippet_containment']:>5.1%}  "
        f"{score_str}"
    )
    print("─" * 66)
    print()

    # Key observations
    print("Notes:")
    sc = avg["snippet_containment"]
    if sc >= 0.90:
        print(f"  • Snippet containment: {sc:.0%} (target ≥90% achieved)")
    else:
        print(f"  • Snippet containment: {sc:.0%} — terms buried deep in "
              "long bodies still missed")
    print(
        "  • Score exposure: "
        f"{'working' if avg['score_avg'] is not None else 'NOT exposed'}"
    )
    print(f"  • {metrics['dataset']['queries_with_relevant']} queries with "
          f"≥1 relevant doc (excluded 'nonexistent' from averages)")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────


def run_benchmark(label: str | None = None) -> dict[str, Any]:
    """Run the benchmark and return full metrics dict."""

    import subprocess

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "unknown"

    conn = build_fts_index(SAMPLE_PAGES)

    per_query: list[dict[str, Any]] = []
    all_scores: list[float] = []

    for qdef in QUERIES:
        results = search(conn, qdef["query"])
        retrieved_titles = [r["title"] for r in results]

        p5 = precision_at_k(retrieved_titles, qdef["relevant"], 5)
        r5 = recall_at_k(retrieved_titles, qdef["relevant"], 5)
        mrr = mean_reciprocal_rank(retrieved_titles, qdef["relevant"])
        sc = snippet_containment(results, qdef["query"], qdef["relevant"])

        scores = [r.get("score") for r in results if r.get("score") is not None]
        score_avg = statistics.mean(scores) if scores else None
        if scores:
            all_scores.extend(scores)

        per_query.append(
            {
                "query": qdef["query"],
                "relevant_count": len(qdef["relevant"]),
                "retrieved_count": len(results),
                "precision_at_5": p5,
                "recall_at_5": r5,
                "mrr": mrr,
                "snippet_containment": sc,
                "score_avg": score_avg,
                "retrieved_titles": retrieved_titles,
            }
        )

    conn.close()

    # Averages across queries with at least one relevant doc
    queries_with_relevant = [q for q in per_query if q["relevant_count"] > 0]
    avg_p5 = statistics.mean(q["precision_at_5"] for q in queries_with_relevant)
    avg_r5 = statistics.mean(q["recall_at_5"] for q in queries_with_relevant)
    avg_mrr = statistics.mean(q["mrr"] for q in queries_with_relevant)
    avg_sc = statistics.mean(q["snippet_containment"] for q in queries_with_relevant)
    score_avgs = [
        q["score_avg"] for q in queries_with_relevant if q["score_avg"] is not None
    ]
    avg_score = statistics.mean(score_avgs) if score_avgs else None

    metrics: dict[str, Any] = {
        "commit": commit,
        "label": label,
        "dataset": {
            "total_pages": len(SAMPLE_PAGES),
            "total_queries": len(QUERIES),
            "queries_with_relevant": len(queries_with_relevant),
        },
        "per_query": per_query,
        "averages": {
            "precision_at_5": avg_p5,
            "recall_at_5": avg_r5,
            "mrr": avg_mrr,
            "snippet_containment": avg_sc,
            "score_avg": avg_score,
        },
    }

    if label:
        metrics["description"] = (
            f"Benchmark snapshot for change: {label}. "
            f"Commit: {commit[:8]}."
        )

    return metrics


def _next_sequence(baselines_dir: Path) -> int:
    """Find the next available sequence number from existing snapshots."""
    if not baselines_dir.exists():
        return 1
    max_n = 0
    for path in baselines_dir.glob("*.json"):
        m = re.match(r"^(\d+)", path.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def _slugify(label: str) -> str:
    """Convert a label to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(description="DuckBrain search quality benchmark")
    parser.add_argument(
        "--label", type=str, default=None,
        help="Human-readable label for this snapshot (e.g. 'add-wikilink-graph')",
    )
    args = parser.parse_args()

    label = args.label
    metrics = run_benchmark(label=label)
    print_report(metrics, metrics["commit"])

    # Always save current baseline
    baseline_path = Path(__file__).parent / "baseline.json"
    baseline_path.write_text(json.dumps(metrics, indent=2))
    print(f"Baseline saved to {baseline_path}")

    # If labeled, also save a snapshot for version comparison
    if label:
        baselines_dir = Path(__file__).parent / "baselines"
        baselines_dir.mkdir(exist_ok=True)
        seq = _next_sequence(baselines_dir)
        snap_path = baselines_dir / f"{seq:03d}-{_slugify(label)}.json"
        snap_path.write_text(json.dumps(metrics, indent=2))
        print(f"Snapshot saved to {snap_path}")
        print(f"  Label: {label}")
    print()


if __name__ == "__main__":
    main()
