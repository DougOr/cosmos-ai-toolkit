"""Report export: console table (reuse), markdown, JSON."""

import json
import time
from pathlib import Path

from orbitbench.metrics import Stats, console_table


def markdown_report(stats_list: list[Stats], meta: dict | None = None) -> str:
    """RESULTS.md generator - same numbers as the console, plus provenance."""
    lines = [
        "# OrbitBench AI - Results",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if meta:
        lines.append("")
        lines.append("| meta | value |")
        lines.append("|---|---|")
        for key, value in meta.items():
            lines.append(f"| {key} | {value} |")

    lines.extend([
        "",
        "| backend | scenario | ops | errors | hit% | ops/s | mean ms | p50 ms | p95 ms | p99 ms |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for s in stats_list:
        lines.append(
            f"| {s.backend} | {s.scenario} | {s.ops} | {s.errors} | {s.hit_ratio:.0%} "
            f"| {s.ops_per_sec:.0f} | {s.mean_ms:.3f} | {s.p50_ms:.3f} "
            f"| {s.p95_ms:.3f} | {s.p99_ms:.3f} |"
        )

    lines.extend([
        "",
        "Methodology: prefilled key space (untimed), per-worker seeded RNG,",
        "per-op latency, errors counted not swallowed. Reproduce with",
        "`orbitbench run --md RESULTS.md`.",
        "",
    ])
    return "\n".join(lines)


def save_markdown(stats_list: list[Stats], path: str | Path, meta: dict | None = None) -> Path:
    path = Path(path)
    path.write_text(markdown_report(stats_list, meta), encoding="utf-8")
    return path


def save_json(stats_list: list[Stats], path: str | Path, meta: dict | None = None) -> Path:
    path = Path(path)
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "meta": meta or {},
        "results": [s.as_dict() for s in stats_list],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
