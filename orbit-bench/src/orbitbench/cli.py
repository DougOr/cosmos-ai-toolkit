"""Command line entry point: `orbitbench run`, `list`, and `check`."""

import argparse
import sys

import httpx

from orbitbench.backends import AVAILABLE_BACKENDS, backend_available
from orbitbench.workloads import SCENARIOS


def _check(settings) -> int:
    print("OrbitBench AI preflight")
    print(f"  endpoint      : {settings.cosmos_endpoint}")

    try:
        settings.tls_guard()
        print("  tls guard     : OK (verification skipped only for localhost)")
    except ValueError as exc:
        print(f"  tls guard     : FAILED - {exc}")
        return 2

    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = httpx.get(settings.cosmos_endpoint,
                                 verify=settings.verify_emulator_tls, timeout=4.0)
        print(f"  emulator      : REACHABLE (HTTP {response.status_code})")
        emulator_ok = True
    except Exception as exc:  # noqa: BLE001
        print(f"  emulator      : NOT REACHABLE - {exc}")
        emulator_ok = False

    for name in AVAILABLE_BACKENDS:
        status = "available" if backend_available(name) else "unavailable (extra not installed)"
        print(f"  backend {name:<7}: {status}")

    return 0 if emulator_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orbitbench", description="Pluggable cache backends + honest benchmarks"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a benchmark suite")
    run.add_argument("--backend", action="append", dest="backends",
                     choices=AVAILABLE_BACKENDS, default=None,
                     help="repeatable; default: memory and cosmos")
    run.add_argument("--scenario", action="append", dest="scenarios",
                     choices=list(SCENARIOS), default=None)
    run.add_argument("--ops", type=int, default=1000)
    run.add_argument("--concurrency", type=int, default=8)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--no-purge", action="store_true", help="keep existing entries")
    run.add_argument("--md", default=None, help="write RESULTS markdown to this path")
    run.add_argument("--json", default=None, help="write JSON results to this path")

    serve = sub.add_parser("serve", help="run the FastAPI server")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    sub.add_parser("list", help="list backends and scenarios")
    sub.add_parser("check", help="preflight: TLS guard + emulator + backend availability")

    args = parser.parse_args(argv)

    from orbitbench.config import get_settings

    settings = get_settings()

    if args.command == "check":
        return _check(settings)

    if args.command == "list":
        print("backends  :", ", ".join(
            f"{b}{'*' if backend_available(b) else ' (extra needed)'}" for b in AVAILABLE_BACKENDS
        ))
        print("scenarios :")
        for name, scenario in SCENARIOS.items():
            print(f"  {name:<11} ops={scenario.ops} read={scenario.read_ratio:.0%} "
                  f"key_space={scenario.key_space} concurrency={scenario.concurrency}")
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "orbitbench.api:app",
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
            log_level="info",
        )
        return 0

    # --- run ---
    import asyncio

    from orbitbench.backends import create_backend
    from orbitbench.metrics import console_table
    from orbitbench.report import save_json, save_markdown
    from orbitbench.runner import run_scenario
    from orbitbench.workloads import Scenario

    scenario_names = args.scenarios or list(SCENARIOS)
    backend_names = args.backends or ["memory", "cosmos"]

    async def execute():
        results = []
        unavailable = []
        for backend_name in backend_names:
            try:
                backend = await create_backend(backend_name, settings, purge=not args.no_purge)
            except Exception as exc:  # noqa: BLE001 - skip cleanly, keep other numbers
                print(f"backend {backend_name}: UNAVAILABLE - {exc}")
                unavailable.append({"backend": backend_name, "error": str(exc)})
                continue
            try:
                for scenario_name in scenario_names:
                    base = SCENARIOS[scenario_name]
                    scenario = Scenario(
                        name=base.name,
                        ops=min(args.ops, 50_000),
                        read_ratio=base.read_ratio,
                        key_space=base.key_space,
                        concurrency=min(max(args.concurrency, 1), 64),
                        value_bytes=base.value_bytes,
                        ttl_seconds=base.ttl_seconds,
                    )
                    print(f"running {backend.name}/{scenario.name} ...", flush=True)
                    results.append(await run_scenario(backend, scenario, args.seed))
            finally:
                await backend.close()
        return results, unavailable

    results, unavailable = asyncio.run(execute())

    if not results:
        print("no backend produced results - start the emulator for the cosmos backend")
        return 1

    meta = {"ops": args.ops, "concurrency": args.concurrency, "seed": args.seed,
            "endpoint": settings.cosmos_endpoint, "unavailable": unavailable}
    print()
    print(console_table(results))
    if args.md:
        path = save_markdown(results, args.md, meta)
        print(f"markdown  : {path}")
    if args.json:
        path = save_json(results, args.json, meta)
        print(f"json      : {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
