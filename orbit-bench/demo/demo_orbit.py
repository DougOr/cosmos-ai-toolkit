"""OrbitBench AI demo - memory vs Cosmos DB, honestly:

    uv run python demo/demo_orbit.py   (emulator running)

Runs read_heavy and mixed on both backends, prints the comparison table,
and writes demo/RESULTS.md + demo/results.json. Same seed -> same workload.
"""

import asyncio
import sys
from pathlib import Path

from orbitbench.backends import backend_available, create_backend
from orbitbench.config import get_settings
from orbitbench.metrics import console_table
from orbitbench.report import save_json, save_markdown
from orbitbench.runner import run_scenario
from orbitbench.workloads import SCENARIOS, Scenario

OPS = 400  # emulator-friendly; raise to 5000+ for real runs


async def main() -> None:
    settings = get_settings()
    backends = ["memory"] + (["cosmos"] if backend_available("cosmos") else [])
    scenario_names = ["read_heavy", "mixed"]

    results = []
    skipped = []
    for backend_name in backends:
        try:
            backend = await create_backend(backend_name, settings, purge=True)
        except Exception as exc:  # noqa: BLE001 - demo must degrade gracefully
            print(f"backend {backend_name}: UNAVAILABLE - {exc}")
            print("(start the Azure Cosmos DB Emulator to include it)")
            skipped.append(backend_name)
            continue
        try:
            for name in scenario_names:
                base = SCENARIOS[name]
                scenario = Scenario(
                    name=base.name, ops=OPS, read_ratio=base.read_ratio,
                    key_space=base.key_space, concurrency=base.concurrency,
                    value_bytes=base.value_bytes,
                )
                print(f"running {backend.name}/{name} ({OPS} ops) ...", flush=True)
                results.append(await run_scenario(backend, scenario, seed=42))
        finally:
            await backend.close()

    if not results:
        print("nothing benched - exiting")
        return 1

    print()
    print(console_table(results))

    out = Path(__file__).parent
    meta = {"ops": OPS, "seed": 42, "endpoint": settings.cosmos_endpoint,
            "skipped": skipped}
    md_path = save_markdown(results, out / "RESULTS.md", meta)
    json_path = save_json(results, out / "results.json", meta)
    print(f"\nwrote {md_path} and {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
