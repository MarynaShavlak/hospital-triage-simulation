"""Bucket-черга: priority за O(1) для кількох дискретних рівнів тяжкості.

Одне FIFO-відро на рівень; кількість рівнів фіксована, тож перебір відер — стала
операція. Реалізує ТУ САМУ дисципліну priority, що й купа (звірено біт-у-біт),
але без log n.
"""
from __future__ import annotations

from collections import deque

from ..engines import run_single_server
from ..model import N_LEVELS, Patient


class BucketPolicy:
    """Priority через bucket-чергу: одне FIFO-відро на рівень. push/pop = O(1).

    Реалізує ТУ САМУ дисципліну priority, що й купа (звірено біт-у-біт), але без
    log n: кількість рівнів фіксована, тож перебір відер — стала операція.
    """

    def __init__(self, levels: int = N_LEVELS) -> None:
        self._buckets: list[deque[Patient]] = [deque() for _ in range(levels + 1)]   # індекс = severity (1..levels)
        self._n = 0

    def push(self, patient: Patient) -> None:
        self._buckets[patient.severity].append(patient)                    # push O(1)
        self._n += 1

    def pop(self, now: float) -> Patient:
        for sev in range(1, len(self._buckets)):               # pop O(1): рівнів стала кількість
            if self._buckets[sev]:
                self._n -= 1
                return self._buckets[sev].popleft()
        raise AssertionError("pop на порожній bucket-черзі — не трапляється (захищено __len__)")

    def __len__(self) -> int:
        return self._n


def simulate_bucket(patients: list[Patient], levels: int = N_LEVELS) -> list[Patient]:
    """Priority через bucket-чергу (той самий результат, що купа, але без log n)."""
    return run_single_server(patients, BucketPolicy(levels))
