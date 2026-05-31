"""Лінійний aging: ефективний пріоритет зростає лінійно з часом очікування.

**Ключовий факт:** член «−зараз/T» однаковий для всіх і скорочується при
порівнянні, тож відносний порядок не залежить від часу — лінійний aging лягає на
купу зі **статичним** ключем `severity + arrival/T` за O(log n). Наївний список
із пересортуванням лишаємо як прозорий еталон (звірено біт-у-біт із купою).
"""
from __future__ import annotations

from ..engines import HeapPolicy, run_single_server
from ..model import DEFAULT_AGING_THRESHOLD, Patient


class ListAgingPolicy:
    """Наївний еталон лінійного aging: звичайний список із пересортуванням щокроку.

    Пересортування на ПОТОЧНИЙ момент часу коштує O(n log n)/крок — повільно,
    але прозоро. Дає той самий результат, що й купна версія (звірено біт-у-біт).
    """

    def __init__(self, aging_threshold: int = DEFAULT_AGING_THRESHOLD) -> None:
        self._T = aging_threshold
        self._w: list[Patient] = []

    def push(self, patient: Patient) -> None:
        self._w.append(patient)

    def pop(self, now: float) -> Patient:
        # Ефективний пріоритет на ПОТОЧНИЙ момент часу (пряма форма aging).
        self._w.sort(
            key=lambda patient: (patient.severity - (now - patient.arrival_time) / self._T, patient.arrival_time))
        return self._w.pop(0)

    def __len__(self) -> int:
        return len(self._w)


def simulate_aging_list(patients: list[Patient], aging_threshold: int = DEFAULT_AGING_THRESHOLD) -> list[Patient]:
    """Priority з 'дорослішанням' через СПИСОК із пересортуванням (наївний еталон)."""
    return run_single_server(patients, ListAgingPolicy(aging_threshold))


def simulate_aging_heap(patients: list[Patient], aging_threshold: int = DEFAULT_AGING_THRESHOLD) -> list[Patient]:
    """Лінійний aging на КУПІ за O(log n).

    Статичний ключ `severity + arrival/T`: член «−зараз/T» однаковий для всіх
    і скорочується при порівнянні, тож відносний порядок не залежить від часу —
    купа підходить.
    """
    return run_single_server(patients, HeapPolicy(
        lambda patient: (patient.severity + patient.arrival_time / aging_threshold, patient.arrival_time)))


# Публічний рушій aging — купна версія (O(log n)); наївний список лишаємо як еталон.
# (Відповідає рішенню з ноутбука зробити купну версію основною.)
simulate_aging = simulate_aging_heap
