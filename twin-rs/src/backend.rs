//! The in-memory cache backend - the twin of OrbitBench's `MemoryBackend`
//! and of `python_twin/twin_bench.py`'s `MemoryBackend`.
//!
//! Deliberate semantic difference from the Python twin (documented in
//! docs/METHODOLOGY.md): Rust needs explicit synchronization because tokio
//! runs workers on multiple threads, while asyncio serializes on one event
//! loop. Making that difference *visible* is part of the experiment.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Instant;

pub struct Value {
    #[allow(dead_code)] // stored, not read: the allocation IS the measured cost
    pub nonce: u64,
    #[allow(dead_code)] // same: kept alive, never read back
    pub pad: String,
}

pub fn build_value(value_bytes: usize, nonce: u64) -> Value {
    Value {
        nonce,
        pad: "x".repeat(value_bytes),
    }
}

struct Entry {
    expires_at: Option<Instant>,
    #[allow(dead_code)] // same as Value.pad: kept alive, never read back
    value: Value,
}

pub struct MemoryBackend {
    data: Mutex<HashMap<String, Entry>>,
    locks: Mutex<HashMap<String, Arc<tokio::sync::Mutex<()>>>>,
}

impl MemoryBackend {
    pub fn new() -> Self {
        Self {
            data: Mutex::new(HashMap::new()),
            locks: Mutex::new(HashMap::new()),
        }
    }

    /// Returns true on hit (and lazily evicts an expired entry).
    pub fn get(&self, key: &str) -> bool {
        let mut data = self.data.lock().unwrap();
        match data.get(key) {
            None => false,
            Some(entry) => match entry.expires_at {
                Some(t) if Instant::now() > t => {
                    data.remove(key);
                    false
                }
                _ => true,
            },
        }
    }

    pub fn set(&self, key: &str, value: Value, ttl: Option<std::time::Duration>) {
        let expires_at = ttl.map(|d| Instant::now() + d);
        self.data
            .lock()
            .unwrap()
            .insert(key.to_string(), Entry { expires_at, value });
    }

    #[allow(dead_code)] // diagnostics
    pub fn len(&self) -> usize {
        self.data.lock().unwrap().len()
    }

    /// Per-key async lock for get-or-generate (stampede protection).
    /// The registry lock is a std Mutex held only across a map insert -
    /// never across an await - so it cannot block the runtime.
    pub fn lock_for(self: &Arc<Self>, key: &str) -> Arc<tokio::sync::Mutex<()>> {
        self.locks
            .lock()
            .unwrap()
            .entry(key.to_string())
            .or_insert_with(|| Arc::new(tokio::sync::Mutex::new(())))
            .clone()
    }
}
