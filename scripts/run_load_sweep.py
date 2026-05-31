#!/usr/bin/env python3
"""Чутливість до навантаження: sweep по ρ (Фаза 10).

Головний інсайт: перевага Priority для критичних РОСТЕ із завантаженням лікаря.

Сам sweep рахує `triage_sim.load_sweep` — те саме джерело чисел, що й графік 19
(figbuild); тут лише друк таблиці.
"""
import _bootstrap  # noqa: F401

from triage_sim import load_sweep


def main(seeds_per_rho=40):
    data = load_sweep(seeds_per_rho=seeds_per_rho)
    print(f"{'ρ':>5}{'FIFO крит':>11}{'Prio крит':>11}{'прискор.':>10}{'Prio L5 max':>13}")
    print("-" * 50)
    for i in range(len(data["rho"])):
        print(f"{data['rho'][i]:>5.2f}{data['fifo_L1'][i]:>11.1f}{data['prio_L1'][i]:>11.1f}"
              f"{data['speedup'][i]:>9.1f}×{data['prio_L5max'][i]:>13.0f}")


if __name__ == "__main__":
    main()
