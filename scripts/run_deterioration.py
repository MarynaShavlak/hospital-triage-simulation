#!/usr/bin/env python3
"""Динамічна тяжкість: погіршення під час очікування + смерть (Фаза 13).

Найреалістичніша модель проєкту. Порівнює два світи:

* **Наївна модель** (без виходу пацієнтів) — усі дисципліни вбивають ~39–45 %
  критичних: спіраль смерті, де навіть Priority безсилий.
* **Реалістична модель** (погіршення + вихід легких) — «клапан» виходу легких
  рятує критичних під Priority (смертність L1 падає до ~6 %).

Наприкінці — аналіз чутливості до темпу погіршення. Кількість прогонів задається аргументом (типово 300).

Самі прогони рахують `triage_sim.deterioration_stats` / `deterioration_sensitivity`
— те саме джерело чисел, що й графік 23 (figbuild); тут лише друк.
"""
import sys

import _bootstrap  # noqa: F401

from triage_sim import DISCIPLINES as DISCS
from triage_sim import deterioration_sensitivity, deterioration_stats


def print_naive(stats):
    """Наївна модель (без виходу пацієнтів)."""
    naive, arrived_l1_died, arrived_l1 = stats["naive"], stats["arrived_l1_died"], stats["arrived_l1"]
    print("НАЇВНА МОДЕЛЬ (без виходу пацієнтів):\n")
    print(f"{'Дисципліна':<12}{'погіршились':>13}{'померли':>10}")
    for disc in DISCS:
        disc_stats = naive[disc]
        print(f"{disc:<12}{100 * disc_stats['deteriorated'] / disc_stats['total']:>11.1f}%"
              f"{100 * disc_stats['died'] / disc_stats['total']:>9.1f}%")
    print("\nПрибули критичними (L1) і померли:")
    for disc in DISCS:
        print(f"  {disc:<10}: {100 * arrived_l1_died[disc] / arrived_l1:.0f}% прибулих L1")


def print_realistic(stats):
    """Реалістична модель (погіршення + вихід легких)."""
    results, arrived_l1 = stats["R"], stats["arrived_l1"]
    print("РЕАЛІСТИЧНА МОДЕЛЬ (погіршення + вихід легких):\n")
    print(f"{'Дисципліна':<12}{'померли':>9}{'пішли':>9}{'прибулих L1 померло':>22}")
    for disc in DISCS:
        disc_results = results[disc]
        print(f"{disc:<12}{100 * disc_results['died'] / disc_results['total']:>8.1f}%"
              f"{100 * disc_results['left'] / disc_results['total']:>8.1f}%"
              f"{100 * disc_results['l1_died'] / arrived_l1:>20.0f}%")


def print_sensitivity(sens):
    """Чутливість смертності критичних до темпу погіршення."""
    arrived_l1 = sens["arrived_l1"]
    print("% прибулих критичних (L1), що померли, за різних темпів погіршення:\n")
    print(f"{'темп/хв':>9}{'FIFO':>8}{'Priority':>10}{'Aging':>8}")
    for rate, l1_deaths in zip(sens["rates"], sens["l1_deaths"], strict=True):
        print(f"{rate * 100:>7.1f}%{100 * l1_deaths['fifo'] / arrived_l1:>7.0f}%"
              f"{100 * l1_deaths['priority'] / arrived_l1:>9.0f}%{100 * l1_deaths['aging'] / arrived_l1:>7.0f}%")


def main(n_runs=300):
    stats = deterioration_stats(runs=n_runs)
    print("=" * 60)
    print_naive(stats)
    print("\n" + "=" * 60)
    print_realistic(stats)
    print("\n" + "=" * 60)
    print("ЧУТЛИВІСТЬ ДО ТЕМПУ ПОГІРШЕННЯ\n")
    print_sensitivity(deterioration_sensitivity(runs=min(n_runs, 200)))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(n)
