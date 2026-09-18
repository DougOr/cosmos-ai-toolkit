"""Command line entry point: `nebula-mind serve` and `nebula-mind check`."""

import argparse
import sys

import httpx


def _reachable(url: str, verify: bool = True) -> tuple[bool, str]:
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = httpx.get(url, verify=verify, timeout=3.0)
        return True, f"HTTP {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _check(settings) -> int:
    print("NebulaMind preflight")
    print(f"  endpoint      : {settings.cosmos_endpoint}")
    print(f"  llm provider  : {settings.llm_provider}")
    print(f"  embeddings    : {settings.embedding_provider}")

    try:
        settings.tls_guard()
        print("  tls guard     : OK (verification skipped only for localhost)")
    except ValueError as exc:
        print(f"  tls guard     : FAILED - {exc}")
        return 2

    verify = settings.verify_emulator_tls
    ok, detail = _reachable(settings.cosmos_endpoint, verify=verify)
    print(f"  emulator      : {'REACHABLE' if ok else 'NOT REACHABLE'} ({detail})")

    if settings.llm_provider == "mock":
        print("  llm           : mock - always available (fully offline)")
    elif settings.llm_provider == "ollama":
        ok, detail = _reachable(f"{settings.ollama_base_url}/api/tags")
        print(f"  ollama        : {'REACHABLE' if ok else 'NOT REACHABLE'} ({detail})")
    elif settings.llm_provider == "openai_compatible":
        if settings.openai_compat_api_key:
            print("  openai_compat : key configured (live call happens on first request)")
        else:
            print("  openai_compat : NO API KEY configured - requests will fail")
            return 1

    if settings.embedding_provider == "hash":
        print("  embeddings    : hash-lexical - always available (offline, lexical)")
    elif settings.embedding_provider == "ollama":
        print(f"  embeddings    : ollama model '{settings.embedding_model}' (same host as llm)")

    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nebula-mind", description="NebulaMind semantic cache CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="run the FastAPI server")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    sub.add_parser("check", help="preflight: TLS guard + emulator + provider reachability")

    args = parser.parse_args(argv)

    from nebula_mind.config import get_settings

    settings = get_settings()

    if args.command == "check":
        return _check(settings)

    import uvicorn

    uvicorn.run(
        "nebula_mind.api:app",
        host=args.host or settings.api_host,
        port=args.port or settings.api_port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
