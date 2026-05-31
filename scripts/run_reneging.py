#!/usr/bin/env python3
"""Reneging / LWBS — пацієнти йдуть, не дочекавшись (Фаза 12).

Прогоняє симуляцію з порогом терпіння N разів і рахує частку LWBS
(Left Without Being Seen) — загалом і за рівнями тяжкості. Також демонструє
**ефект клапана**: під Priority довго застряглі легкі не дочікуються
катастрофічних 700+ хв, а просто йдуть, тож максимум очікування *обслужених*
легких різко падає. Кількість прогонів задається аргументом (типово 300).

Самі прогони рахують `triage_sim.reneging_stats` / `reneging_valve` — те саме
джерело чисел, що й графік 22 (figbuild); тут лише друк.
"""
import sys

import _bootstrap  # noqa: F401

from triage_sim import DISCIPLINES as DISCS
from triage_sim import reneging_stats, reneging_valve


def main(n_runs=300):
    stats = reneging_stats(runs=n_runs)
    overall, lwbs = stats["overall"], stats["lwbs"]

    print(f"Виконано {n_runs} прогонів\n")
    print("Загальний рівень LWBS:")
    for disc in DISCS:
        disc_overall = overall[disc]
        print(f"  {disc:<10}: {100 * disc_overall['left'] / disc_overall['total']:.1f}%")

    print("\nРівень LWBS за рівнями тяжкості (%):")
    print(f"{'Рівень':<7}{'FIFO':>8}{'Priority':>10}{'Aging':>8}")
    for severity in range(1, 6):
        rates = []
        for disc in DISCS:
            counts = lwbs[disc][severity]
            rates.append(100 * counts["left"] / counts["total"] if counts["total"] else 0)
        print(f"L{severity:<6}{rates[0]:>7.1f}%{rates[1]:>9.1f}%{rates[2]:>7.1f}%")

    valve = reneging_valve(runs=n_runs)
    l5_no, l5_yes = valve["l5_no"], valve["l5_yes"]
    print("\nЕФЕКТ КЛАПАНА (Priority, max очікування ОБСЛУЖЕНИХ L5):")
    print(f"  без reneging (ідеально терплячі): {sum(l5_no) / len(l5_no):.0f} хв "
          f"(макс {max(l5_no):.0f})")
    print(f"  з reneging (йдуть за ~2 год):     {sum(l5_yes) / len(l5_yes):.0f} хв "
          f"(макс {max(l5_yes):.0f})")
    print("  => катастрофічне голодування зникло: довгочекаючі ПІШЛИ, а не дочекалися")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(n)
