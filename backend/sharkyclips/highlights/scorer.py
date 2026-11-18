"""Combine signals with mode weights into one hype curve (one value per second).

Signals that can't run are skipped and the remaining weights re-normalized, so
the scorer never needs to know which signals exist.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import gaussian_filter1d

from ..errors import SharkyClipsError
from ..ui import console
from .context import AnalysisContext
from .signals import REGISTRY, SignalResult, SignalUnavailable

MIN_SHARE_FOR_AGREEMENT = 0.08  # tiny-weight signals don't count as "agreeing"
# 1.2.53 moment quality (issue #1b): a loudness spike that nothing else backs up (no words, no
# laughter, no game event, no chat) is usually a door slam, a sound effect or a cough: it keeps
# only part of its weight. Long stretches without speech and with flat audio (menus, loading
# screens, AFK) are pushed down so picks have context (setup -> payoff).
LONELY_LOUDNESS_KEEP = 0.45
IDLE_PENALTY = 0.55  # hype x this in an idle stretch
IDLE_MIN_S = 20  # at least this long without a word ...
IDLE_FLAT_DB = 2.5  # ... and the audio level barely moves (std in dB over 10 s)


@dataclass
class HypeCurve:
    smoothed: np.ndarray
    combined: np.ndarray
    results: dict[str, SignalResult]
    shares: dict[str, float]  # normalized weights of the signals that ran
    status: dict[str, dict] = field(default_factory=dict)


def compute_hype(ctx: AnalysisContext) -> HypeCurve:
    weights = {k: float(v) for k, v in ctx.mode.weights.items() if v and v > 0}
    results: dict[str, SignalResult] = {}
    status: dict[str, dict] = {}
    for name, w in weights.items():
        cls = REGISTRY.get(name)
        if cls is None:
            status[name] = {"status": "skipped", "weight": w, "reason": "not available yet"}
            continue
        t0 = time.perf_counter()
        try:
            res = cls().run(ctx)
        except SignalUnavailable as exc:
            status[name] = {"status": "skipped", "weight": w, "reason": str(exc)}
            console.print(f"[yellow]Signal '{name}' skipped:[/] {exc}")
            continue
        except Exception as exc:  # noqa: BLE001  - one broken signal must not kill the run
            status[name] = {"status": "error", "weight": w, "reason": f"{type(exc).__name__}: {exc}"}
            console.print(f"[red]Signal '{name}' failed:[/] {exc}")
            continue
        res.scores = np.clip(np.asarray(res.scores, dtype=np.float64)[: ctx.n], 0, 1)
        if len(res.scores) < ctx.n:
            res.scores = np.pad(res.scores, (0, ctx.n - len(res.scores)))
        results[name] = res
        status[name] = {"status": "ok", "weight": w, "seconds": round(time.perf_counter() - t0, 2),
                        "events": len(res.events), **({"meta": res.meta} if res.meta else {})}

    total = sum(weights[n] for n in results)
    if total <= 0:
        reasons = "; ".join(f"{k}: {v.get('reason')}" for k, v in status.items())
        raise SharkyClipsError(f"No highlight signal could run ({reasons}).",
                               "Run `python cli.py transcribe <id>` first, and `python cli.py doctor`.")
    shares = {n: weights[n] / total for n in results}
    for n, s in shares.items():
        status[n]["share"] = round(s, 3)

    combined = np.zeros(ctx.n)
    agreeing = np.zeros(ctx.n)
    for n, res in results.items():
        combined += shares[n] * res.scores
        if shares[n] >= MIN_SHARE_FOR_AGREEMENT:
            agreeing += res.scores >= 0.5
    if "loudness" in results and len(results) > 1:
        loud = results["loudness"].scores
        others = agreeing - (loud >= 0.5)
        near = np.convolve((others > 0).astype(float), np.ones(7), mode="same") > 0  # +-3 s
        lonely = (loud >= 0.3) & ~near
        combined -= shares["loudness"] * loud * (1 - LONELY_LOUDNESS_KEEP) * lonely
    combined *= 1.0 + ctx.mode.agreement_bonus * np.maximum(0, agreeing - 1)
    idle = idle_seconds(ctx)
    if idle is not None and idle.any():
        game = results.get("game")
        if game is not None:  # a game event on screen is never "idle" (a quiet clutch)
            idle &= game.scores < 0.3
        combined = np.where(idle, combined * IDLE_PENALTY, combined)
        console.print(f"[dim]Context: {int(idle.sum())} s of menus / loading / AFK pushed down.[/]")
    combined = np.clip(combined, 0, 1)
    smoothed = gaussian_filter1d(combined, ctx.mode.smooth_sigma) if ctx.n > 3 else combined
    return HypeCurve(smoothed, combined, results, shares, status)


def idle_seconds(ctx: AnalysisContext) -> np.ndarray | None:
    """True for seconds inside a long stretch with no speech and a flat audio level: menus,
    loading screens, queue timers, AFK. None when there is no transcript to tell."""
    if not ctx.transcript:
        return None
    n = ctx.n
    spoken = np.zeros(n, dtype=bool)
    for w in ctx.words:
        a, b = int(max(0, w.start)), int(min(n - 1, w.end))
        spoken[a:b + 1] = True
    # distance to the nearest word, both ways: a gap of >= IDLE_MIN_S seconds
    quiet = ~spoken
    run = np.zeros(n, dtype=int)
    i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            run[i:j] = j - i
            i = j
        else:
            i += 1
    long_quiet = run >= IDLE_MIN_S
    if not long_quiet.any():
        return long_quiet
    try:
        db = ctx.rms_db.astype(np.float64)
    except Exception:  # noqa: BLE001 - no audio level: the silence alone decides
        return long_quiet
    fps = max(1, int(round(len(db) / max(1.0, ctx.duration))))
    per_s = np.array([db[k * fps:(k + 1) * fps].mean() if k * fps < len(db) else db[-1] for k in range(n)])
    win = 10
    pad = np.pad(per_s, (win // 2, win // 2), mode="edge")
    std = np.array([pad[k:k + win].std() for k in range(n)])
    return long_quiet & (std < IDLE_FLAT_DB)

