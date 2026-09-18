"""Command line entry point: `quasar-ai serve` and `quasar-ai check`."""

import argparse
import sys

import httpx


def _check(settings) -> int:
    """Connectivity preflight: config guard, then a real request to the emulator."""
    print("QuasarAI preflight")
    print(f"  endpoint      : {settings.cosmos_endpoint}")
    print(f"  database      : {settings.database_name}")
    print(f"  local endpoint: {settings.is_local_endpoint}")

    try:
        settings.tls_guard()
        print("  tls guard     : OK (verification skipped only for localhost)")
    except ValueError as exc:
        print(f"  tls guard     : FAILED - {exc}")
        return 2

    verify = settings.verify_emulator_tls
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = httpx.get(settings.cosmos_endpoint, verify=verify, timeout=4.0)
        # Any HTTP response means the emulator listener is up (auth comes later).
        print(f"  emulator      : REACHABLE (HTTP {response.status_code})")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"  emulator      : NOT REACHABLE - {exc}")
        print("  hint          : start the Azure Cosmos DB Emulator (Windows MSI), then retry")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quasar-ai", description="QuasarAI cache engine CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the FastAPI server")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    sub.add_parser("check", help="preflight: config guard + emulator reachability")

    args = parser.parse_args(argv)

    from quasar_ai.config import get_settings

    settings = get_settings()

    if args.command == "check":
        return _check(settings)

    import uvicorn

    uvicorn.run(
        "quasar_ai.api:app",
        host=args.host or settings.api_host,
        port=args.port or settings.api_port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
