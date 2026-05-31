"""Шар підготовки даних для графіків — лінива, з кешуванням.

`Data` рахує кожен набір (seed=42, Монте-Карло, sweep по навантаженню, harm,
reneging, deterioration) лише за першим запитом і кешує результат. Жодних
звернень до matplotlib — чиста обчислювальна логіка через публічний API
`triage_sim`, тож важкі прогони виконуються лише для тих графіків, що їх обрали.
"""
from __future__ import annotations

import copy

from triage_sim import (
    count_in_danger,
    deterioration_stats,
    generate_patients,
    load_sweep,
    metrics_by_severity,
    monte_carlo,
    reneging_stats,
    simulate,
    simulate_aging,
)

from .constants import AGING_THR, DISCS


class Data:
    """Лінива підготовка даних для графіків: кожен набір рахується раз і кешується."""

    def __init__(self, runs: int) -> None:
        self.runs = runs
        self._cache: dict = {}

    def _memo(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def seed42(self):
        def build():
            pts = generate_patients(seed=42)
            served = {
                "fifo": simulate(copy.deepcopy(pts), "fifo"),
                "priority": simulate(copy.deepcopy(pts), "priority"),
                "aging": simulate_aging(copy.deepcopy(pts), AGING_THR),
            }
            metrics = {disc: metrics_by_severity(s) for disc, s in served.items()}
            return {"pts": pts, "served": served, "metrics": metrics}
        return self._memo("seed42", build)

    def throughput(self):
        def build():
            served_n = {d: 0 for d in DISCS}
            util: dict[str, list[float]] = {d: [] for d in DISCS}
            sumwait = {d: {s: 0.0 for s in range(1, 6)} for d in DISCS}
            for seed in range(self.runs):
                base = generate_patients(seed=seed)
                first_arr = min(p.arrival_time for p in base)
                runs = {
                    "fifo": simulate(copy.deepcopy(base), "fifo"),
                    "priority": simulate(copy.deepcopy(base), "priority"),
                    "aging": simulate_aging(copy.deepcopy(base), AGING_THR),
                }
                for disc, served in runs.items():
                    served_n[disc] += len(served)
                    last = max(p.start_time + p.service_duration for p in served if p.start_time is not None)
                    busy = sum(p.service_duration for p in served)
                    util[disc].append(busy / (last - first_arr))
                    for p in served:
                        sumwait[disc][p.severity] += p.wait_time
            return {"served_n": served_n, "util": util, "sumwait": sumwait}
        return self._memo("throughput", build)

    def monte(self):
        # Спільне джерело з run_monte_carlo.py — графік і звіт про ті самі числа.
        return self._memo("monte", lambda: monte_carlo(runs=self.runs))

    def sweep(self):
        # Спільне джерело з run_load_sweep.py.
        return self._memo("sweep", lambda: load_sweep(seeds_per_rho=min(self.runs, 40)))

    def harm(self):
        def build():
            sims = {"fifo": lambda p: simulate(p, "fifo"),
                    "priority": lambda p: simulate(p, "priority"),
                    "aging": lambda p: simulate_aging(p, AGING_THR)}
            cache = {d: [sims[d](copy.deepcopy(generate_patients(seed=s))) for s in range(self.runs)]
                     for d in DISCS}
            acc: dict[str, dict] = {d: {s: {"danger": [], "total": []} for s in range(1, 6)} for d in DISCS}
            for d in DISCS:
                for served in cache[d]:
                    danger, total = count_in_danger(served)
                    for s in range(1, 6):
                        acc[d][s]["danger"].append(danger[s])
                        acc[d][s]["total"].append(total[s])
            thresholds = [5, 10, 15, 20, 30]
            sens: dict[str, list[float]] = {d: [] for d in DISCS}
            for thr in thresholds:
                for d in DISCS:
                    dt = ct = 0
                    for served in cache[d]:
                        for p in served:
                            if p.severity == 1:
                                ct += 1
                                dt += p.wait_time > thr
                    sens[d].append(100 * dt / ct)
            return {"acc": acc, "sens": sens, "thresholds": thresholds}
        return self._memo("harm", build)

    def reneging(self):
        # Спільне джерело з run_reneging.py.
        return self._memo("reneging", lambda: reneging_stats(runs=self.runs))

    def deter(self):
        # Спільне джерело з run_deterioration.py.
        return self._memo("deter", lambda: deterioration_stats(runs=self.runs))
