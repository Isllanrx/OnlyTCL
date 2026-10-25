use std::time::Instant;
use crate::metrics::METRICS;

/// Result of context filtering
#[derive(Debug, serde::Serialize)]
pub struct FilterResult {
    pub original_chars: usize,
    pub filtered_chars: usize,
    pub estimated_tokens_before: usize,
    pub estimated_tokens_after: usize,
    pub tokens_saved: usize,
    pub reduction_percentage: f32,
    pub elapsed_micros: u64,
    pub filtered_text: String,
}

/// Estimate tokens from character count (average ~3.2 chars/token for multilingual/Portuguese)
#[inline]
pub fn estimate_tokens(text: &str) -> usize {
    if text.is_empty() {
        return 0;
    }
    // Simple heuristic: count words + punctuation approximation
    let words = text.split_whitespace().count();
    let chars = text.chars().count();
    // Weighted blend: words * 1.33 or chars / 3.5
    let by_words = (words as f64 * 1.33) as usize;
    let by_chars = chars / 3;
    by_words.max(by_chars).max(1)
}

/// Compress and filter context to minimize token usage on TV
pub fn filter_context(input: &str) -> FilterResult {
    let start = Instant::now();
    let original_chars = input.chars().count();
    let tokens_before = estimate_tokens(input);

    let mut filtered = String::with_capacity(input.len());
    let mut consecutive_empty_lines = 0;

    for line in input.lines() {
        let trimmed_end = line.trim_end();
        let trimmed = trimmed_end.trim();

        if trimmed.is_empty() {
            consecutive_empty_lines += 1;
            if consecutive_empty_lines <= 1 {
                filtered.push('\n');
            }
            continue;
        }
        consecutive_empty_lines = 0;

        // Truncate raw base64 data blobs in conversation logs
        if trimmed.starts_with("data:image/") || (trimmed.len() > 100 && !trimmed.contains(' ') && is_likely_base64(trimmed)) {
            filtered.push_str("[media: base64 omitted for TV context reduction]\n");
            continue;
        }

        // Strip verbose stack traces in user prompt if present
        if trimmed.starts_with("\tat ") && filtered.ends_with("\tat ... [stack trace truncated]\n") {
            continue;
        } else if trimmed.starts_with("\tat ") && line_count_matching(&filtered, "\tat ") > 5 {
            filtered.push_str("\tat ... [stack trace truncated]\n");
            continue;
        }

        filtered.push_str(trimmed_end);
        filtered.push('\n');
    }

    let filtered_chars = filtered.chars().count();
    let tokens_after = estimate_tokens(&filtered);
    let tokens_saved = tokens_before.saturating_sub(tokens_after);
    let reduction_percentage = if tokens_before > 0 {
        ((tokens_saved as f32 / tokens_before as f32) * 100.0).clamp(0.0, 100.0)
    } else {
        0.0
    };

    let elapsed = start.elapsed().as_micros() as u64;

    // Record metrics
    METRICS.record_filter(tokens_saved, elapsed);

    FilterResult {
        original_chars,
        filtered_chars,
        estimated_tokens_before: tokens_before,
        estimated_tokens_after: tokens_after,
        tokens_saved,
        reduction_percentage,
        elapsed_micros: elapsed,
        filtered_text: filtered,
    }
}

fn is_likely_base64(s: &str) -> bool {
    let mut valid = 0;
    for c in s.chars() {
        if c.is_ascii_alphanumeric() || c == '+' || c == '/' || c == '=' {
            valid += 1;
        }
    }
    valid > 80 && (valid as f32 / s.len() as f32) > 0.95
}

fn line_count_matching(text: &str, pat: &str) -> usize {
    text.lines().filter(|l| l.trim_start().starts_with(pat)).count()
}
