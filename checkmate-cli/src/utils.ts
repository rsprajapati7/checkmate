import { useState, useEffect } from 'react';

// ── Spinner ────────────────────────────────────────────────────────────────
export const SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'] as const;

/**
 * Animated spinner hook. Returns the current spinner character.
 * Only animates when `active` is true — clears interval when idle.
 */
export function useSpinner(active: boolean, intervalMs = 80): string {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => {
      setIdx((prev) => (prev + 1) % SPINNER_FRAMES.length);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [active, intervalMs]);

  return SPINNER_FRAMES[idx];
}

// ── Clean ASCII symbols (no emojis) ────────────────────────────────────────
export const SYM = {
  CHECK:   '[ OK ]',
  CROSS:   '[FAIL]',
  WARN:    '[WARN]',
  BULLET:  '  >>',
  ARROW:   '-->',
  PIPE:    '|',
  DASH:    '---',
  SECTION: '===',
} as const;

// ── Helpers ────────────────────────────────────────────────────────────────

/** Clamp a value between min and max. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Build a filled/empty ASCII progress bar. */
export function buildBar(score: number, totalBlocks = 10): { filled: number; empty: number } {
  const filled = Math.min(totalBlocks, Math.max(0, Math.round((score / 100) * totalBlocks)));
  return { filled, empty: totalBlocks - filled };
}
