//! The stampede scenario - the twin of QuasarAI's per-key-lock proof:
//! N concurrent get-or-generate calls on one cold key with a simulated
//! generation cost. Correctness gate: generations must equal 1.

use std::sync::Arc;
use std::time::{Duration, Instant};

use crate::backend::{build_value, MemoryBackend};

pub struct StampedeResult {
    pub waiters: u64,
    pub generations: u64,
    pub wall_ms: f64,
    pub gen_cost_us: u64,
}

pub async fn run(waiters: u64, gen_cost_us: u64, value_bytes: usize, seed: u64) -> StampedeResult {
    let backend = Arc::new(MemoryBackend::new());
    let key = format!("cold-{seed}");

    let mut handles = Vec::with_capacity(waiters as usize);
    let started = Instant::now();

    for w in 0..waiters {
        let backend = backend.clone();
        let key = key.clone();
        handles.push(tokio::spawn(async move {
            let lock = backend.lock_for(&key);
            let _guard = lock.lock().await;
            if backend.get(&key) {
                return 0u64; // hit
            }
            tokio::time::sleep(Duration::from_micros(gen_cost_us)).await; // the "LLM"
            backend.set(&key, build_value(value_bytes, w), None);
            1u64 // generation
        }));
    }

    let mut generations = 0u64;
    for handle in handles {
        generations += handle.await.unwrap();
    }

    StampedeResult {
        waiters,
        generations,
        wall_ms: started.elapsed().as_secs_f64() * 1000.0,
        gen_cost_us,
    }
}
