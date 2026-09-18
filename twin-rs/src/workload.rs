//! Scenario shapes and op streams - 1:1 twins of OrbitBench's workloads,
//! but driven by the shared xorshift so both languages replay identical ops.

use crate::rng::Xorshift64Star;

#[derive(Clone)]
pub struct Scenario {
    pub name: &'static str,
    pub ops: u64,
    pub read_ratio: f64,
    pub key_space: u64,
    pub concurrency: u64,
    pub value_bytes: usize,
}

pub fn scenarios(ops: u64, concurrency: u64) -> Vec<Scenario> {
    vec![
        Scenario { name: "read_heavy", ops, read_ratio: 0.9, key_space: 500, concurrency, value_bytes: 512 },
        Scenario { name: "write_heavy", ops, read_ratio: 0.1, key_space: 500, concurrency, value_bytes: 512 },
        Scenario { name: "mixed", ops, read_ratio: 0.5, key_space: 500, concurrency, value_bytes: 512 },
        Scenario { name: "hot_key", ops: ops / 2, read_ratio: 1.0, key_space: 1, concurrency: concurrency * 2, value_bytes: 512 },
    ]
}

#[derive(Clone, Copy, PartialEq)]
pub enum Op {
    Get,
    Set,
}

pub struct OpStream {
    rng: Xorshift64Star,
    read_ratio: f64,
    key_space: u64,
}

impl OpStream {
    pub fn new(seed: u64, scenario: &Scenario) -> Self {
        Self {
            rng: Xorshift64Star::new(seed),
            read_ratio: scenario.read_ratio,
            key_space: scenario.key_space,
        }
    }

    /// Returns (op, key, nonce) - identical sequence to the Python twin
    /// for the same seed, call for call.
    pub fn next_op(&mut self) -> (Op, String, u64) {
        let decision = self.rng.next_f64();
        let key_index = self.rng.next_u64() % self.key_space;
        let nonce = self.rng.next_u64();
        let op = if decision < self.read_ratio { Op::Get } else { Op::Set };
        (op, format!("key-{key_index}"), nonce)
    }
}
