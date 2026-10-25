use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};

pub struct RtkMetrics {
    pub total_queries_processed: AtomicUsize,
    pub total_tokens_saved: AtomicUsize,
    pub local_commands_handled: AtomicUsize,
    pub total_filter_duration_us: AtomicU64,
}

impl RtkMetrics {
    pub const fn new() -> Self {
        Self {
            total_queries_processed: AtomicUsize::new(0),
            total_tokens_saved: AtomicUsize::new(0),
            local_commands_handled: AtomicUsize::new(0),
            total_filter_duration_us: AtomicU64::new(0),
        }
    }

    pub fn record_filter(&self, tokens_saved: usize, duration_us: u64) {
        self.total_queries_processed.fetch_add(1, Ordering::Relaxed);
        self.total_tokens_saved.fetch_add(tokens_saved, Ordering::Relaxed);
        self.total_filter_duration_us.fetch_add(duration_us, Ordering::Relaxed);
    }

    pub fn record_local_command(&self, tokens_saved: usize) {
        self.total_queries_processed.fetch_add(1, Ordering::Relaxed);
        self.local_commands_handled.fetch_add(1, Ordering::Relaxed);
        self.total_tokens_saved.fetch_add(tokens_saved, Ordering::Relaxed);
    }

    pub fn to_json(&self) -> String {
        let processed = self.total_queries_processed.load(Ordering::Relaxed);
        let tokens = self.total_tokens_saved.load(Ordering::Relaxed);
        let local_cmds = self.local_commands_handled.load(Ordering::Relaxed);
        let duration = self.total_filter_duration_us.load(Ordering::Relaxed);
        let avg_us = if processed > 0 { duration / (processed as u64) } else { 0 };

        format!(
            r#"{{"total_queries_processed":{},"total_tokens_saved":{},"local_commands_handled":{},"avg_filter_duration_us":{}}}"#,
            processed, tokens, local_cmds, avg_us
        )
    }

    pub fn reset(&self) {
        self.total_queries_processed.store(0, Ordering::Relaxed);
        self.total_tokens_saved.store(0, Ordering::Relaxed);
        self.local_commands_handled.store(0, Ordering::Relaxed);
        self.total_filter_duration_us.store(0, Ordering::Relaxed);
    }
}

pub static METRICS: RtkMetrics = RtkMetrics::new();
