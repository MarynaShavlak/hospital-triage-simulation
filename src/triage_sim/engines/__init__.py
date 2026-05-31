"""Рушії симуляції: узагальнені драйвери + політики черги + публічні обгортки.

Архітектура «один рушій + політика черги»: уся механіка часу — у драйверах
(`drivers.py`), а дисципліна обслуговування — у політиці (`policies.py`).
Публічні тонкі обгортки (`simulate`, `simulate_fifo_deque`, `simulate_md`)
складають драйвер із потрібною політикою — вони тут, на межі пакета:

* `priority` → ключ `(severity, arrival_time)` — найтяжчий першим;
* `fifo`     → ключ `(arrival_time,)`          — перший прийшов, перший пішов.

Моделі з ВИБУТТЯМ пацієнтів (reneging, deterioration) користуються драйвером
`run_with_departures` із динамічним `discipline_sort_key`.
"""
from __future__ import annotations

import heapq

from ..model import Patient
from .drivers import QueuePolicy, run_single_server, run_with_departures
from .policies import (
    FifoDequePolicy,
    HeapPolicy,
    KeyFn,
    discipline_sort_key,
    heap_key,
)

# Публічні рушії — тонкі обгортки над драйвером + політикою

def simulate(patients: list[Patient], discipline: str = "priority") -> list[Patient]:
    """Симулює один лікар + чергу. discipline: 'fifo' або 'priority'."""
    return run_single_server(patients, HeapPolicy(heap_key(discipline)))


def simulate_fifo_deque(patients: list[Patient]) -> list[Patient]:
    """FIFO через deque — O(1) на операцію, без купи.

    Дає той самий результат, що `simulate(..., 'fifo')` (звірено біт-у-біт),
    але без накладних витрат купи. Купу для FIFO ми взяли лише щоб **уніфікувати
    код** і показати, що FIFO та Priority — одна структура з різним ключем.
    """
    return run_single_server(patients, FifoDequePolicy())


def simulate_md(patients: list[Patient], discipline: str = "priority", n_doctors: int = 1) -> list[Patient]:
    """Як `simulate`, але `c` лікарів. Стан лікарів — купа часів звільнення.

    При `n_doctors=1` збігається зі `simulate` біт-у-біт. Багатосерверну
    логіку валідовано формулою Erlang-C (M/M/c) — див. `validation.py`.
    Черга — та сама `HeapPolicy`, що й в одно-серверному рушії.
    """
    arrivals = sorted(patients, key=lambda patient: patient.arrival_time)
    i = 0
    policy = HeapPolicy(heap_key(discipline))
    served = []
    servers = [0.0] * n_doctors
    heapq.heapify(servers)
    while i < len(arrivals) or policy:
        earliest_free = servers[0]                                  # найраніше вільний лікар
        while i < len(arrivals) and arrivals[i].arrival_time <= earliest_free:
            policy.push(arrivals[i])
            i += 1
        if policy:
            free = heapq.heappop(servers)
            patient = policy.pop(earliest_free)
            patient.start_time = free
            served.append(patient)
            heapq.heappush(servers, free + patient.service_duration)
        elif i < len(arrivals):
            free = heapq.heappop(servers)
            heapq.heappush(servers, max(free, arrivals[i].arrival_time))
        else:
            break
    return served


__all__ = [
    # драйвери (drivers.py)
    "QueuePolicy", "run_single_server", "run_with_departures",
    # політики черги + фабрики ключів (policies.py)
    "KeyFn", "heap_key", "HeapPolicy", "FifoDequePolicy", "discipline_sort_key",
    # публічні обгортки
    "simulate", "simulate_fifo_deque", "simulate_md",
]
