# DEMO - QuasarAI in 6 minutes

**Audience:** anyone who pays LLM bills or builds AI features on Azure.
**One-line takeaway:** *"The first answer costs 349 ms. Every answer after
that costs 6 ms - and 20 people asking at once still costs one generation."*

Everything runs 100% local on the Azure Cosmos DB emulator. No cloud, no API
keys, no cost.

---

## Before the audience arrives (~4 minutes)

1. Start the **Azure Cosmos DB Emulator** (Windows Start menu), wait ~20 s.
2. Terminal 1:

   ```powershell
   cd quasar-ai
   uv sync
   uv run quasar-ai check        # must say: emulator : REACHABLE
   uv run python demo/demo_quasar.py   # WARM-UP RUN - absorbs first-touch
                                     # slowness; leave it finishing Act 4 work
   uv run quasar-ai serve        # http://127.0.0.1:8001
   ```

3. Open **http://127.0.0.1:8001/docs** (Swagger) in the browser.
4. Terminal 2, in the same folder - keep it free for `stampede_hit.py`.

---

## Act 1 - The 55x moment (2 min)

In Swagger: **GET `/cache/demo:quantum`** → *Try it out* → *Execute* (twice).

**First call (miss):** `status: "miss"`, `latency_ms ≈ 349`, source
`generated`. The mock LLM "thought", the answer got stored in Cosmos DB.

> **Say:** "That 349 milliseconds is your LLM bill - tokens you pay for
> every single time someone asks this."

**Second call (hit):** `status: "hit"`, `latency_ms ≈ 6`, **byte-identical
payload** (point at the same `content` hash).

> **Say:** "Same answer, 55 times faster. The bill was paid once."

**Wow-moment math (say it):** at 10k identical questions/day, that is
~58 minutes of LLM latency replaced by ~1 minute of point reads.

## Act 2 - The stampede (90 seconds)

The killer scenario: a cold key goes viral. 20 users hit it *at the same
instant*. Naive caches fire 20 LLM calls (and often crash 19 concurrent
writes). Terminal 2:

```powershell
uv run python demo/stampede_hit.py
```

Expected:

```
20 concurrent requests in ~400 ms
statuses: 1 miss + 19 hit
generations: 1 (must be 1)
```

> **Say:** "One per-key lock. Twenty users. One generation. This is the
> thundering-herd bug most demos don't even know they have - and the v1 of
> this project had it."

## Act 3 - Live benchmark (60 seconds)

In Swagger: **GET `/benchmark?ops=15`** → Execute. JSON shows
`miss_avg_ms ≈ 354`, `hit_avg_ms ≈ 10`, `speedup ≈ 35`, plus p95s.

> **Say:** "Percentiles, not vibes. p95 matters because your slowest users
> don't care about the average."

## Act 4 - The receipts (60 seconds)

Open `docs/DECISIONS.md`. Ten ADRs; each one names what v1 did wrong.

> **Say:** "This file is why you should trust the 55x - every design
> decision here exists because the previous version measured or broke
> something real: sync SDK blocking the event loop, md5 keys, naive
> datetimes, SQL built by string interpolation. The fix list *is* the
> architecture."

---

## Contingency plans

| Problem | Fallback |
|---|---|
| Emulator won't start | `uv run pytest` - the stampede unit test passes on an in-memory fake; narrate from README's measured table |
| Server port busy | `uv run quasar-ai serve --port 8090` |
| Act 2 shows >1 miss | Another process hit the same key between runs - the key is time-stamped, just rerun |

## Reset between runs

```powershell
# Swagger: DELETE /cache/invalidate   (or)
Invoke-RestMethod -Method Delete "http://127.0.0.1:8001/cache/invalidate"
```
