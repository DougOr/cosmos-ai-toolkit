//! Stats - same percentile interpolation and same JSON keys as OrbitBench,
//! so tables from both languages can sit in one document.

pub fn percentile(samples: &mut [f64], q: f64) -> f64 {
    if samples.is_empty() {
        return 0.0;
    }
    samples.sort_by(|a, b| a.partial_cmp(b).unwrap());
    if samples.len() == 1 {
        return samples[0];
    }
    let k = (samples.len() - 1) as f64 * q;
    let f = k.floor() as usize;
    let c = k.ceil() as usize;
    if f == c {
        return samples[f];
    }
    samples[f] + (samples[c] - samples[f]) * (k - f as f64)
}

#[derive(Clone)]
pub struct Stats {
    pub backend: String,
    pub scenario: String,
    pub ops: u64,
    pub errors: u64,
    pub reads: u64,
    pub hits: u64,
    pub total_s: f64,
    pub mean_ms: f64,
    pub p50_ms: f64,
    pub p95_ms: f64,
    pub p99_ms: f64,
}

#[allow(clippy::too_many_arguments)]
impl Stats {
    pub fn new(
        backend: &str,
        scenario: &str,
        ops: u64,
        errors: u64,
        reads: u64,
        hits: u64,
        total_s: f64,
        mut latencies_ms: Vec<f64>,
    ) -> Self {
        let mean = if latencies_ms.is_empty() {
            0.0
        } else {
            latencies_ms.iter().sum::<f64>() / latencies_ms.len() as f64
        };
        Self {
            backend: backend.to_string(),
            scenario: scenario.to_string(),
            ops,
            errors,
            reads,
            hits,
            total_s,
            mean_ms: mean,
            p50_ms: percentile(&mut latencies_ms, 0.50),
            p95_ms: percentile(&mut latencies_ms, 0.95),
            p99_ms: percentile(&mut latencies_ms, 0.99),
        }
    }

    pub fn ops_per_sec(&self) -> f64 {
        if self.total_s > 0.0 {
            self.ops as f64 / self.total_s
        } else {
            0.0
        }
    }

    pub fn hit_ratio(&self) -> f64 {
        if self.reads > 0 {
            self.hits as f64 / self.reads as f64
        } else {
            0.0
        }
    }

    pub fn to_json(&self) -> String {
        format!(
            r#"{{"backend":"{}","scenario":"{}","ops":{},"errors":{},"reads":{},"hit_ratio":{:.3},"total_s":{:.3},"ops_per_sec":{:.1},"mean_ms":{:.4},"p50_ms":{:.4},"p95_ms":{:.4},"p99_ms":{:.4}}}"#,
            self.backend,
            self.scenario,
            self.ops,
            self.errors,
            self.reads,
            self.hit_ratio(),
            self.total_s,
            self.ops_per_sec(),
            self.mean_ms,
            self.p50_ms,
            self.p95_ms,
            self.p99_ms
        )
    }
}
