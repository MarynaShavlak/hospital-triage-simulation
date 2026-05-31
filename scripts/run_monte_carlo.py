#!/usr/bin/env python3
"""Монте-Карло: N незалежних прогонів з різними seed (Фаза 9).

Показує, що один прогін (seed=42) міг обманути: чесна оцінка прискорення ближча
до ~5×, а не 11×. Кількість прогонів задається аргументом (типово 300).

Сам експеримент рахує `triage_sim.monte_carlo` — те саме джерело чисел, що й
графіки 17/18 (figbuild); тут лише друк зведення.
"""
import sys

import _bootstrap  # noqa: F401
import numpy as np

from triage_sim import monte_carlo


def main(n_runs=300):
    data = monte_carlo(runs=n_runs)
    res, skipped = data["res"], data["skipped"]

    print(f"Виконано {n_runs} прогонів (пропущено {skipped})\n")

    def summary(name, arr):
        arr = np.array(arr)
        pct_low, pct_high = np.percentile(arr, [2.5, 97.5])
        print(f"{name:<14} {arr.mean():>7.1f} ± {arr.std():>5.1f} хв   (95%: {pct_low:.0f}–{pct_high:.0f})")

    print("КРИТИЧНІ (L1), середнє очікування:")
    summary("  FIFO", res["f_L1"])
    summary("  Priority", res["p_L1"])
    summary("  Aging", res["a_L1"])
    print("\nЛЕГКІ (L5), максимальне очікування:")
    summary("  FIFO", res["f_L5"])
    summary("  Priority", res["p_L5"])
    summary("  Aging", res["a_L5"])

    speedups = np.array(res["speedup"])
    print("\nПРИСКОРЕННЯ критичних (FIFO/Priority):")
    print(f"  середнє {speedups.mean():.1f}× | медіана {np.median(speedups):.1f}× | "
          f"95%: {np.percentile(speedups, 2.5):.1f}–{np.percentile(speedups, 97.5):.1f}×")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(n)
