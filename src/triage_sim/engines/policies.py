"""Політики черги та фабрики ключів сортування.

Кожна політика реалізує інтерфейс `QueuePolicy` (push / pop / __len__) і
інкапсулює дисципліну обслуговування — драйвери з `drivers.py` лишаються
незмінними. Ключова теза: **FIFO — це теж черга з пріоритетами**, лише з ключем
за часом прибуття; тому одна `HeapPolicy` обслуговує і priority, і fifo —
різниця тільки у функції ключа (`heap_key`).

* `HeapPolicy`          — черга з пріоритетами на `heapq` (статичний ключ);
* `FifoDequePolicy`     — FIFO на `deque`, push/pop за O(1);
* `heap_key`            — статичний ключ купи за назвою дисципліни;
* `discipline_sort_key` — динамічний ключ списку для моделей із вибуттям (з aging).
"""
from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Callable

from ..model import DEFAULT_AGING_THRESHOLD, Patient

# Ключ сортування купи: patient → кортеж (severity/час, …) для порівняння в heapq.
KeyFn = Callable[[Patient], tuple]


def heap_key(discipline: str) -> KeyFn:
    """Функція статичного ключа купи за назвою дисципліни (`priority` або `fifo`).

    FIFO — це теж черга з пріоритетами, лише з ключем за часом прибуття: на цьому
    тримається теза «одна структура, різний ключ». Невідому дисципліну відхиляємо
    одразу (fail-fast), а не трактуємо мовчки.
    """
    if discipline == "priority":
        return lambda patient: (patient.severity, patient.arrival_time)
    if discipline == "fifo":
        return lambda patient: (patient.arrival_time,)
    raise ValueError(f"невідома дисципліна: {discipline!r} (очікується 'priority' або 'fifo')")


class HeapPolicy:
    """Черга з пріоритетами на `heapq`. Порядок задається функцією `key_fn(p)`."""

    def __init__(self, key_fn: KeyFn) -> None:
        self._key = key_fn
        self._h: list[tuple] = []
        self._seq = 0          # тай-брейкер для стабільності (FIFO серед рівних)

    def push(self, patient: Patient) -> None:
        heapq.heappush(self._h, (self._key(patient), self._seq, patient))
        self._seq += 1

    def pop(self, now: float) -> Patient:
        return heapq.heappop(self._h)[2]

    def __len__(self) -> int:
        return len(self._h)


class FifoDequePolicy:
    """FIFO через `deque` — push/pop за O(1), без купи."""

    def __init__(self) -> None:
        self._q: deque[Patient] = deque()

    def push(self, patient: Patient) -> None:
        self._q.append(patient)                      # у КІНЕЦЬ черги, O(1)

    def pop(self, now: float) -> Patient:
        return self._q.popleft()               # з ПОЧАТКУ — найраніший, O(1)

    def __len__(self) -> int:
        return len(self._q)


def discipline_sort_key(
    discipline: str, aging_threshold: int = DEFAULT_AGING_THRESHOLD,
) -> Callable[[Patient, float], tuple]:
    """Динамічний ключ сортування списку для моделей із вибуттям.

    Черга все одно повністю перебирається на кожному кроці (відсів вибулих),
    тож aging тут задається у ПРЯМІЙ формі `severity − очікування/T`.
    Невідому дисципліну відхиляємо одразу (fail-fast).
    """
    if discipline == "priority":
        return lambda patient, now: (patient.severity, patient.arrival_time)
    if discipline == "fifo":
        return lambda patient, now: (patient.arrival_time,)
    if discipline == "aging":
        return lambda patient, now: (
            patient.severity - (now - patient.arrival_time) / aging_threshold, patient.arrival_time)
    raise ValueError(f"невідома дисципліна: {discipline!r} (очікується 'priority', 'fifo' або 'aging')")
