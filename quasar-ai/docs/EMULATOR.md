# Running QuasarAI on the Azure Cosmos DB Emulator (Windows)

QuasarAI is engineered for the **local Windows emulator only**. No cloud
account, no network egress, no cost. This document gets you from zero to
`quasar-ai check` saying green.

## 1. Install and start the emulator

1. Download the **Azure Cosmos DB Emulator** (MSI) from
   <https://learn.microsoft.com/azure/cosmos-db/local-emulator> and install it.
2. Start it (Start menu → *Azure Cosmos DB Emulator*). It listens on
   `https://localhost:8081` and shows a data explorer in the browser.
3. Leave it running while using QuasarAI.

The emulator uses a **self-signed TLS certificate** and a **well-known public
key**. Both facts shape QuasarAI's design:

- `COSMOS_KEY` in `.env.example` is that public key. It is *not* a secret; it
  only ever opens your local emulator.
- TLS verification is skipped (`VERIFY_EMULATOR_TLS=false`), and
  **`Settings.tls_guard()` refuses to start if the endpoint is not localhost**
  while verification is skipped. You cannot accidentally run this
  configuration against a real cloud account.

## 2. Preflight

```bash
uv sync
uv run quasar-ai check
```

Expected:

```
QuasarAI preflight
  endpoint      : https://localhost:8081/
  database      : QuasarDB
  local endpoint: True
  tls guard     : OK (verification skipped only for localhost)
  emulator      : REACHABLE (HTTP 200)
```

`NOT REACHABLE` → the emulator process is not running, or the port is taken.

## 3. Trusting the certificate (only needed for browser data explorer)

If your browser warns when opening `https://localhost:8081/_explorer`:

```powershell
# export the emulator cert, then import to Trusted Root (admin PowerShell)
$cert = Export-Certificate -Type CERT -FilePath "$env:TEMP\cosmos.cer" `
  -Address localhost -Port 8081 2>$null
Import-Certificate -FilePath "$env:TEMP\cosmos.cer" -CertStoreLocation Cert:\CurrentUser\Root
```

QuasarAI itself does **not** need this step - it skips verification via the
guarded setting.

## 4. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `NOT REACHABLE` in `quasar-ai check` | Emulator not started | Start the emulator, wait ~20 s, re-run |
| `401 Unauthorized` from Cosmos | Key mismatch | Restore the well-known key in `.env` |
| `tls guard : FAILED` at startup | Endpoint pointed off-localhost with verification off | Intended behaviour - see `CLOUD_DELTAS.md` |
| Port 8081 busy | Another service owns it | Stop it, or change the emulator port and `COSMOS_ENDPOINT` |
| Emulator throws on startup after sleep | Known emulator quirk | Restart the emulator process |

## 5. Footnote: the Linux (vNext) emulator

Microsoft also ships a Dockerized Linux emulator. QuasarAI works with it
unchanged (same endpoint/key model, now truly cross-platform). The default
configs in this repo target the Windows MSI because that is what the v1
harness used, keeping v1-vs-v2 comparisons clean.
