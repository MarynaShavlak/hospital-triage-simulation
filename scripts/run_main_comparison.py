#!/usr/bin/env python3
"""Головне порівняння FIFO vs Priority vs Aging на одному наборі пацієнтів (seed=42).

Відтворює таблиці середнього/максимального очікування та «головну цифру» з
Фази 5. Наприкінці — звірка «дисципліна ≠ структура»: FIFO дає той самий
результат і на купі (`simulate`), і на справжній черзі (`simulate_fifo_deque`).
"""
import copy

import _bootstrap  # noqa: F401  (додає ../src у sys.path за потреби)
from _common import served_by_discipline

from triage_sim import (
    SEV_NAMES,
    generate_patients,
    metrics_by_severity,
    simulate_fifo_deque,
)


def main(seed=42, aging_threshold=45):
    patients = generate_patients(seed=seed)

    served = served_by_discipline(patients, aging_threshold)
    fifo, prio, aging = served["fifo"], served["priority"], served["aging"]

    metrics_fifo = metrics_by_severity(fifo)
    metrics_priority = metrics_by_severity(prio)
    metrics_aging = metrics_by_severity(aging)

    print(f"Набір пацієнтів: {len(patients)} (seed={seed}), поріг aging = {aging_threshold} хв\n")

    print("СЕРЕДНІЙ час очікування (хв) за тяжкістю:\n")
    print(f"{'Рівень':<18}{'FIFO':>8}{'Priority':>10}{'Aging':>8}")
    print("-" * 44)
    for severity in range(1, 6):
        print(f"{SEV_NAMES[severity]:<18}{metrics_fifo[severity]['avg']:>8.0f}{metrics_priority[severity]['avg']:>10.0f}{metrics_aging[severity]['avg']:>8.0f}")

    print("\nМАКСИМАЛЬНИЙ час очікування (хв) за тяжкістю:\n")
    print(f"{'Рівень':<18}{'FIFO':>8}{'Priority':>10}{'Aging':>8}")
    print("-" * 44)
    for severity in range(1, 6):
        print(f"{SEV_NAMES[severity]:<18}{metrics_fifo[severity]['max']:>8.0f}{metrics_priority[severity]['max']:>10.0f}{metrics_aging[severity]['max']:>8.0f}")

    print("\n" + "=" * 50)
    print("ГОЛОВНИЙ РЕЗУЛЬТАТ")
    print("=" * 50)
    print("Критичний пацієнт (L1) у середньому чекає:")
    print(f"   FIFO:     {metrics_fifo[1]['avg']:.0f} хвилин")
    print(f"   Priority: {metrics_priority[1]['avg']:.0f} хвилин")
    print(f"   → у {metrics_fifo[1]['avg'] / metrics_priority[1]['avg']:.0f} рази швидше з чергою з пріоритетами!\n")
    print("Найдовше очікування критичного пацієнта:")
    print(f"   FIFO:     {metrics_fifo[1]['max']:.0f} хвилин (це понад {metrics_fifo[1]['max'] / 60:.1f} години!)")
    print(f"   Priority: {metrics_priority[1]['max']:.0f} хвилин")
    print("\nЗворотний бік Priority — голодування легких (L5):")
    print(f"   максимум очікування L5: Priority={metrics_priority[5]['max']:.0f} хв, "
          f"Aging зрізає до {metrics_aging[5]['max']:.0f} хв")

    # FIFO — це купа з ключем за часом; але ту саму дисципліну тримає й справжня черга.
    fifo_deque = simulate_fifo_deque(copy.deepcopy(patients))
    same_order = [patient.id for patient in fifo] == [patient.id for patient in fifo_deque]
    print("\n" + "=" * 50)
    print("ДИСЦИПЛІНА ≠ СТРУКТУРА")
    print("=" * 50)
    print("FIFO та Priority — одна купа з різним ключем (тема проєкту).")
    print("Але саму дисципліну FIFO можна тримати на РІЗНИХ структурах:")
    print("   • купа (heapq), ключ = час прибуття       → O(log n)/операція")
    print("   • deque (справжня черга), append/popleft  → O(1)/операція")
    print(f"Однаковий порядок обслуговування (за id):    {same_order}")
    print("=> «який порядок» (дисципліна) не залежить від «як зберігати» (структура).")


if __name__ == "__main__":
    main()
