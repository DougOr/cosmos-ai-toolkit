"""Latency statistics: percentiles over raw samples, means only as context."""

import math
from dataclasses import dataclass, field


def percentile(samples: list[float], q: float) -> float:
    """Linear-interpolated percentile on sorted samples. 0.0 when empty."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * q
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


@dataclass
class Stats:
    backend: str
    scenario: str
    ops: int = 0
    errors: int = 0
    reads: int = 0
    hits: int = 0
    total_s: float = 0.0
    latencies_ms: list[float] = field(default_factory=list, repr=False)

    @property
    def mean_ms(self) -> float:
        return round(sum(self.latencies_ms) / len(self.latencies_ms), 3) if self.latencies_ms else 0.0

    @property
    def p50_ms(self) -> float:
        return round(percentile(self.latencies_ms, 0.50), 3)

    @property
    def p95_ms(self) -> float:
        return round(percentile(self.latencies_ms, 0.95), 3)

    @property
    def p99_ms(self) -> float:
        return round(percentile(self.latencies_ms, 0.99), 3)

    @property
    def ops_per_sec(self) -> float:
        return round(self.ops / self.total_s, 1) if self.total_s > 0 else 0.0

    @property
    def hit_ratio(self) -> float:
        return round(self.hits / self.reads, 3) if self.reads > 0 else 0.0

    def as_dict(self) -> dict:
        return {
            "backend": self.backend,
            "scenario": self.scenario,
            "ops": self.ops,
            "errors": self.errors,
            "reads": self.reads,
            "hit_ratio": self.hit_ratio,
            "total_s": round(self.total_s, 3),
            "ops_per_sec": self.ops_per_sec,
            "mean_ms": self.mean_ms,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
        }


def console_table(stats_list: list[Stats]) -> str:
    """Aligned ASCII table - the deliverable of every run."""
    headers = ["backend", "scenario", "ops", "errors", "hit%", "ops/s",
               "mean", "p50", "p95", "p99"]
    rows = []
    for s in stats_list:
        rows.append([
            s.backend, s.scenario, str(s.ops), str(s.errors), f"{s.hit_ratio:.0%}",
            f"{s.ops_per_sec:.0f}", f"{s.mean_ms:.3f}", f"{s.p50_ms:.3f}",
            f"{s.p95_ms:.3f}", f"{s.p99_ms:.3f}",
        ])

    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    separator = "-" * len(line)
    body = "\n".join("  ".join(cell.ljust(w) for cell, w in zip(row, widths)) for row in rows)
    units = "(latency columns in ms; in-memory backends legitimately show sub-ms values)"
    return f"{line}\n{separator}\n{body}\n{separator}\n{units}"
