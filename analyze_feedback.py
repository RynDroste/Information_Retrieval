#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple analysis script for user feedback logs.

Combines:
- Current retrieval scores (keyword / semantic / combined)
- User positive feedback (👍) from logs/feedback.jsonl

Outputs:
- Overall stats (number of feedbacks, rank distribution)
- Per-(query, filters) stats: count, avg rank, Pos@3 / Pos@5
- Average scores for positively judged documents
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean


LOG_PATH = Path(__file__).parent / "logs" / "feedback.jsonl"


def load_feedback():
    if not LOG_PATH.exists():
        print(f"Feedback log not found: {LOG_PATH}")
        return []
    records = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append(rec)
            except json.JSONDecodeError:
                continue
    return records


def canonical_filter_key(filters: dict) -> str:
    """Create a stable string key from filters dict for grouping."""
    if not isinstance(filters, dict):
        return ""
    items = sorted(filters.items())
    return ";".join(f"{k}={v}" for k, v in items)


def analyze(records):
    if not records:
        print("No feedback records to analyze.")
        return

    # Only keep positive feedback (we已经只保留“相关按钮”，但老日志里可能还有 negative)
    positives = [r for r in records if r.get("positive") is True]
    if not positives:
        print("No positive feedback records found.")
        return

    print("========== Overall Stats ==========")
    print(f"Total feedback records: {len(records)}")
    print(f"Positive feedback records: {len(positives)}")

    # Rank distribution for positives
    rank_counts = Counter(int(r.get("rank", 0) or 0) for r in positives)
    print("\nTop ranks for positive feedback (rank => count):")
    for rank in sorted(rank_counts.keys())[:20]:
        print(f"  Rank {rank}: {rank_counts[rank]}")

    # Global score stats
    keyword_scores = [r["keyword_score"] for r in positives if isinstance(r.get("keyword_score"), (int, float))]
    semantic_scores = [r["semantic_score"] for r in positives if isinstance(r.get("semantic_score"), (int, float))]
    combined_scores = [r["combined_score"] for r in positives if isinstance(r.get("combined_score"), (int, float))]

    print("\nAverage scores for positively judged documents:")
    if keyword_scores:
        print(f"  Avg keyword_score : {mean(keyword_scores):.3f}")
    else:
        print("  Avg keyword_score : N/A")
    if semantic_scores:
        print(f"  Avg semantic_score: {mean(semantic_scores):.3f}")
    else:
        print("  Avg semantic_score: N/A")
    if combined_scores:
        print(f"  Avg combined_score: {mean(combined_scores):.3f}")
    else:
        print("  Avg combined_score: N/A")

    # Group by (query + filters) for per-query stats
    groups = defaultdict(list)
    for r in positives:
        query = (r.get("query") or "").strip()
        filt_key = canonical_filter_key(r.get("filters") or {})
        key = (query, filt_key)
        groups[key].append(r)

    print("\n========== Per-query Stats (Top 20 groups by feedback count) ==========")
    # Sort groups by size
    sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)[:20]

    for (query, filt_key), recs in sorted_groups:
        ranks = sorted(int(r.get("rank", 0) or 0) for r in recs)
        cnt = len(recs)
        pos_at_3 = sum(1 for r in ranks if r <= 3) / cnt
        pos_at_5 = sum(1 for r in ranks if r <= 5) / cnt
        avg_rank = mean(ranks)
        print("\n----------------------------------------")
        print(f"Query        : '{query or '<EMPTY>'}'")
        print(f"Filters      : {filt_key or '<NONE>'}")
        print(f"Feedback cnt : {cnt}")
        print(f"Avg rank     : {avg_rank:.2f}")
        print(f"Pos@3        : {pos_at_3:.2%}  (fraction of positives in rank ≤ 3)")
        print(f"Pos@5        : {pos_at_5:.2%}  (fraction of positives in rank ≤ 5)")


def main():
    records = load_feedback()
    analyze(records)


if __name__ == "__main__":
    main()




