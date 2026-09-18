//! CosmoTwin - the rewrite-hypothesis benchmark (Rust side).
//!
//! Usage:
//!   cargo run --release -- bench [--ops 200000] [--concurrency 8]
//!                                [--seed 42] [--json out.json]
//!   cargo run --release -- selftest          (prints the PRNG vector the
//!                                             Python twin must match)

mod backend;
mod metrics;
mod report;
mod rng;
mod stampede;
mod workload;

use std::sync::Arc;
use std::time::Instant;

use backend::{build_value, MemoryBackend};
use metrics::Stats;
use workload::{OpStream, Scenario};

struct Config {
    ops: u64,
    concurrency: u64,
    seed: u64,
    json: Option<String>,
    stampede_waiters: u64,
    stampede_gen_us: u64,
}

fn parse_args() -> Config {
    let mut cfg = Config {
        ops: 200_000,
        concurrency: 8,
        seed: 42,
        json: None,
        stampede_waiters: 10_000,
        stampede_gen_us: 300,
    };
    // skip(2): argv[0] is the binary, argv[1] is the mode ("bench")
    let mut args = std::env::args().skip(2);
    while let Some(arg) = args.next() {
        let mut value = || {
            args.next()
                .unwrap_or_else(|| panic!("{arg} expects a value"))
        };
        match arg.as_str() {
            "--ops" => cfg.ops = value().parse().expect("ops must be a number"),
            "--concurrency" => cfg.concurrency = value().parse().expect("concurrency must be a number"),
            "--seed" => cfg.seed = value().parse().expect("seed must be a number"),
            "--json" => cfg.json = Some(value()),
            "--stampede-waiters" => cfg.stampede_waiters = value().parse().expect("number"),
            "--stampede-gen-us" => cfg.stampede_gen_us = value().parse().expect("number"),
            other => panic!("unknown argument: {other}"),
        }
    }
    cfg
}

async fn run_scenario(scenario: &Scenario, cfg: &Config) -> Stats {
    let backend = Arc::new(MemoryBackend::new());

    // untimed prefill: reads measure reads (OrbitBench methodology)
    for i in 0..scenario.key_space {
        backend.set(
            &format!("key-{i}"),
            build_value(scenario.value_bytes, cfg.seed.wrapping_mul(1000) + i),
            None,
        );
    }

    let per_worker = scenario.ops / scenario.concurrency;
    let remainder = scenario.ops % scenario.concurrency;
    let seed = cfg.seed;
    let started = Instant::now();

    let mut handles = Vec::with_capacity(scenario.concurrency as usize);
    for w in 0..scenario.concurrency {
        let count = per_worker + u64::from(w < remainder);
        let backend = backend.clone();
        let sc = scenario.clone();
        handles.push(tokio::spawn(async move {
            let mut stream = OpStream::new(seed + w, &sc);
            let mut latencies = Vec::with_capacity(count as usize);
            let mut reads = 0u64;
            let mut hits = 0u64;
            for i in 0..count {
                let (op, key, nonce) = stream.next_op();
                let t0 = Instant::now();
                match op {
                    workload::Op::Get => {
                        reads += 1;
                        if backend.get(&key) {
                            hits += 1;
                        }
                    }
                    workload::Op::Set => {
                        backend.set(&key, build_value(sc.value_bytes, nonce.wrapping_add(i)), None);
                    }
                }
                latencies.push(t0.elapsed().as_secs_f64() * 1000.0);
            }
            (latencies, reads, hits)
        }));
    }

    let mut latencies = Vec::with_capacity(scenario.ops as usize);
    let mut reads = 0u64;
    let mut hits = 0u64;
    for handle in handles {
        let (l, r, h) = handle.await.unwrap();
        latencies.extend(l);
        reads += r;
        hits += h;
    }
    let total_s = started.elapsed().as_secs_f64();

    Stats::new(
        "rust-memory",
        scenario.name,
        scenario.ops,
        0,
        reads,
        hits,
        total_s,
        latencies,
    )
}

async fn bench(cfg: Config) {
    println!(
        "CosmoTwin (Rust) - ops={} concurrency={} seed={} value=512B",
        cfg.ops, cfg.concurrency, cfg.seed
    );
    println!();

    let scenarios = workload::scenarios(cfg.ops, cfg.concurrency);
    let mut results = Vec::with_capacity(scenarios.len());
    for scenario in &scenarios {
        results.push(run_scenario(scenario, &cfg).await);
    }
    report::print_table(&results);

    let stampede_result = stampede::run(cfg.stampede_waiters, cfg.stampede_gen_us, 512, cfg.seed).await;
    report::print_stampede(&stampede_result);

    if let Some(path) = cfg.json {
        report::write_json(&results, &stampede_result, &path);
    }
}

fn selftest() {
    // The Python twin must print the exact same three values for seed 1.
    let mut rng = rng::Xorshift64Star::new(1);
    println!("prng-vector seed=1:");
    for _ in 0..3 {
        println!("  {:016x}", rng.next_u64());
    }
}

#[tokio::main]
async fn main() {
    let mode = std::env::args().nth(1).unwrap_or_else(|| "bench".to_string());
    if mode == "selftest" {
        selftest();
    } else {
        bench(parse_args()).await;
    }
}
