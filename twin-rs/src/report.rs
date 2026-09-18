//! Console table in the OrbitBench column format + JSON export.

use crate::metrics::Stats;
use crate::stampede::StampedeResult;

pub fn print_table(stats: &[Stats]) {
    let headers = ["backend", "scenario", "ops", "errors", "hit%", "ops/s", "mean", "p50", "p95", "p99"];
    let rows: Vec<Vec<String>> = stats
        .iter()
        .map(|s| {
            vec![
                s.backend.clone(),
                s.scenario.clone(),
                s.ops.to_string(),
                s.errors.to_string(),
                format!("{:.0}%", s.hit_ratio() * 100.0),
                format!("{:.0}", s.ops_per_sec()),
                format!("{:.4}", s.mean_ms),
                format!("{:.4}", s.p50_ms),
                format!("{:.4}", s.p95_ms),
                format!("{:.4}", s.p99_ms),
            ]
        })
        .collect();

    let widths: Vec<usize> = headers
        .iter()
        .enumerate()
        .map(|(i, h)| rows.iter().map(|r| r[i].len()).chain([h.len()]).max().unwrap())
        .collect();

    let line: Vec<String> = headers
        .iter()
        .zip(&widths)
        .map(|(h, w)| format!("{h:<w$}"))
        .collect();
    println!("{}", line.join("  "));
    println!("{}", "-".repeat(line.join("  ").len()));
    for row in &rows {
        let cells: Vec<String> = row
            .iter()
            .zip(&widths)
            .map(|(c, w)| format!("{c:<w$}"))
            .collect();
        println!("{}", cells.join("  "));
    }
    println!("{}", "-".repeat(line.join("  ").len()));
    println!("(latency columns in ms; this benchmark isolates in-process cache logic - no network)");
}

pub fn print_stampede(result: &StampedeResult) {
    println!();
    println!(
        "stampede: {} concurrent get-or-generate on one cold key (generation = {} micros simulated)",
        result.waiters, result.gen_cost_us
    );
    println!(
        "  wall {:.2} ms | generations: {} (must be 1) | {}",
        result.wall_ms,
        result.generations,
        if result.generations == 1 { "OK" } else { "FAILED" }
    );
}

pub fn write_json(stats: &[Stats], stampede: &StampedeResult, path: &str) {
    let body: Vec<String> = stats.iter().map(|s| s.to_json()).collect();
    let json = format!(
        "{{\"generated_by\":\"cosmotwin rust\",\"results\":[{}],\"stampede\":{{\"waiters\":{},\"generations\":{},\"wall_ms\":{:.2}}}}}",
        body.join(","),
        stampede.waiters,
        stampede.generations,
        stampede.wall_ms
    );
    std::fs::write(path, json).expect("write json");
    println!("json: {path}");
}
