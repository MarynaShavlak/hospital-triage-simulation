"""Метрики аналізу: статистика очікування за тяжкістю та підрахунок «в небезпеці».

* `metrics_by_severity` — середнє/максимум/кількість очікування на кожен
  рівень тяжкості (основа всіх таблиць і графіків).
* `DANGER` + `count_in_danger` — клінічні пороги небезпеки (на основі
  CTAS) і скільки пацієнтів їх перевищили (метрика шкоди, Фаза 11).
"""
from __future__ import annotations

import statistics

from .model import SEVERITY_LEVELS, Patient


def metrics_by_severity(served: list[Patient]) -> dict[int, dict[str, float]]:
    """Повертає `{severity: {'avg', 'max', 'count'}}` за списком обслужених.

    Розкладає час очікування по «відрах» рівнів і рахує статистику для кожного.
    Рівні без пацієнтів у вихідний словник не потрапляють.
    """
    buckets: dict[int, list[float]] = {severity: [] for severity in SEVERITY_LEVELS}
    for patient in served:
        buckets[patient.severity].append(patient.wait_time)
    return {severity: {"avg": statistics.mean(waits), "max": max(waits), "count": len(waits)}
            for severity, waits in buckets.items() if waits}


# Пороги небезпеки на основі CTAS (L1 «негайно» → 10 хв як практичний проксі).
DANGER = {1: 10, 2: 15, 3: 30, 4: 60, 5: 120}


def count_in_danger(served: list[Patient], danger: dict[int, int] = DANGER) -> tuple[dict[int, int], dict[int, int]]:
    """Скільки пацієнтів кожного рівня перевищили свій поріг небезпеки.

    Повертає пару словників `(danger_counts, total_counts)` за рівнями.
    """
    in_danger = {severity: 0 for severity in SEVERITY_LEVELS}
    total = {severity: 0 for severity in SEVERITY_LEVELS}
    for patient in served:
        total[patient.severity] += 1
        if patient.wait_time > danger[patient.severity]:
            in_danger[patient.severity] += 1
    return in_danger, total
